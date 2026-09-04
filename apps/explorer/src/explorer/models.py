"""Local models, through Ollama.

The second model provider in this app, and deliberately not a generalisation of
the first. `witz.py` and `ars.py` call the Anthropic API directly — they stream,
they use thinking blocks, and rewriting two working surfaces to share an
abstraction with this one would be refactoring beyond what this needs. The seam
is that a second provider now exists and is separate; a third should prompt the
generalisation this one skips.

Failures are returned rather than raised, the rule `witz.py` states: this sits
beside a verdict on a page, and a stopped daemon should not take the page down.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

#: Where the daemon listens. Overridable because a reader running Ollama on
#: another host should not have to edit this file to try the page.
HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")

#: Long enough for a 9.6 GB model to answer on CPU. A model turn here was
#: measured in seconds, but a cold load of the weights is the slow first one.
TIMEOUT = 300


@dataclass(frozen=True)
class LocalModel:
    """One installed model, and whether it can call tools.

    `reason` is Ollama's own words for a refusal, not a paraphrase. The three
    models that cannot call tools here are the German and European ones this
    project would most want, so the page names them and says why rather than
    quietly offering only the model that works.
    """

    name: str
    tools: bool
    reason: str


def _post(path: str, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    body = json.dumps(payload).encode()
    request = urllib.request.Request(f"{HOST}{path}", body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            parsed: dict[str, Any] = json.loads(response.read())
            return parsed, ""
    except urllib.error.HTTPError as exc:
        # Ollama puts its refusal in the body, and it is the useful half: the
        # status alone cannot tell "no such model" from "does not support tools".
        try:
            detail = str(json.loads(exc.read()).get("error", "")) or f"HTTP {exc.code}"
        except Exception:
            detail = f"HTTP {exc.code}"
        return None, detail
    except urllib.error.URLError as exc:
        return None, f"Could not reach Ollama at {HOST} ({exc.reason})."
    except (TimeoutError, OSError) as exc:
        return None, f"Could not reach Ollama at {HOST} ({exc})."


#: One probe per model per process. Installing a model mid-session is not a case
#: worth a cache invalidation path, and the probe costs a round trip each.
_TOOL_SUPPORT: dict[str, tuple[bool, str]] = {}

#: The smallest tool array Ollama will look at. Its template either accepts a
#: `tools` key or refuses the request outright, so nothing about this schema
#: needs to resemble denckring's own.
_PROBE_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "probe",
            "parameters": {"type": "object", "properties": {}},
        },
    }
]


def supports_tools(name: str) -> tuple[bool, str]:
    """Whether `name` can call tools, and Ollama's reason if it cannot.

    Asked by attempting a call, because `/api/tags` does not report it. There is
    no field for this anywhere in the API: the model's template either renders a
    tool array or the server refuses with `does not support tools`, and only the
    attempt distinguishes them.
    """
    if name not in _TOOL_SUPPORT:
        _, problem = _post(
            "/api/chat",
            {
                "model": name,
                "messages": [{"role": "user", "content": "hi"}],
                "tools": _PROBE_TOOL,
                "stream": False,
                "options": {"num_predict": 1},
            },
        )
        _TOOL_SUPPORT[name] = (not problem, problem)
    return _TOOL_SUPPORT[name]


def available() -> tuple[list[LocalModel], str]:
    """Every installed model, tool-capable first, and a problem if the daemon
    could not be reached at all."""
    try:
        with urllib.request.urlopen(f"{HOST}/api/tags", timeout=10) as response:
            payload = json.loads(response.read())
    except Exception as exc:
        return [], f"Could not reach Ollama at {HOST} ({exc})."
    found = []
    for row in payload.get("models", []):
        name = str(row.get("name", ""))
        if not name:
            continue
        tools, reason = supports_tools(name)
        found.append(LocalModel(name=name, tools=tools, reason=reason))
    found.sort(key=lambda model: (not model.tools, model.name))
    return found, ""


def chat(
    model: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
) -> tuple[dict[str, Any], str]:
    """One turn. Temperature zero, because the page is a demonstration of a
    protocol and a reader clicking the same preset twice should see the same
    thing happen."""
    payload, problem = _post(
        "/api/chat",
        {
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "options": {"temperature": 0},
        },
    )
    if payload is None:
        return {}, problem
    message: dict[str, Any] = payload.get("message", {})
    return message, ""
