"""A local model driving denckring's own MCP server.

The first consumer this repository has ever had for that server. It was written,
tested against its own tool functions and swept by hand, but nothing here had
spoken the protocol to it.

A real stdio client rather than importing the tool functions: the page's claim is
that the protocol works, and calling Python in-process while saying "via MCP"
would be the same class of untruth as a catalogue definition promising what its
checker cannot do.

The session is spawned per request and closed when the turn ends. Measured
2026-09-04: spawn plus initialize is 0.37s against a model turn measured in
seconds, so a persistent session would save an invisible fraction and buy a
lifecycle to get wrong — a subprocess to reap, a reconnect path, and a server
that keeps whatever it imported at start-up, which is exactly the staleness the
hand-driven server already has to be restarted for.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from typing import Any

from explorer import models

#: The console script `denckring[mcp]` installs. Looked up rather than assumed,
#: so the page can say it is missing instead of failing inside anyio's task
#: group, where the real cause arrives wrapped in an ExceptionGroup.
SERVER = "denckring-mcp"

#: Where the loop stops. Four is two more than any preset needs — one call and
#: one answer — and leaves room for a model that describes a procedure before
#: checking against it, without letting a confused one run all afternoon.
MAX_TURNS = 4


@dataclass(frozen=True)
class Step:
    """One tool call and what came back, as the page shows it."""

    name: str
    arguments: str
    result: str


@dataclass
class Transcript:
    """What happened, in order. The artefact of the page rather than a chat log.

    The interesting content is that a model running on this machine produced a
    well-formed call against a schema handed to it at runtime, and that denckring
    answered it — so the calls and their raw JSON are the body, and the closing
    sentence is the footnote.
    """

    question: str = ""
    model: str = ""
    steps: list[Step] = field(default_factory=list)
    answer: str = ""
    problem: str = ""


def _as_ollama_tool(tool: Any) -> dict[str, Any]:
    """One MCP tool in the shape Ollama's `tools` array wants.

    `input_schema`, not `inputSchema`. The wire format uses the camel-case name
    and the Python object does not, and the error that comes back —
    `'Tool' object has no attribute 'inputSchema'` — surfaces here, at the line
    building a tool list, nowhere near anything that looks like a protocol
    concern. Pinned by a test.
    """
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": (tool.description or "")[:900],
            "parameters": tool.input_schema,
        },
    }


def _text_of(result: Any) -> str:
    """The tool result as the model will see it."""
    blocks = getattr(result, "content", None) or []
    return "\n".join(getattr(block, "text", "") for block in blocks).strip()


async def run(question: str, model: str, max_turns: int = MAX_TURNS) -> Transcript:
    """Ask `model` to answer `question` using denckring's MCP tools."""
    transcript = Transcript(question=question.strip(), model=model)
    if not transcript.question:
        transcript.problem = "Ask something first."
        return transcript
    if shutil.which(SERVER) is None:
        transcript.problem = (
            f"{SERVER} is not on PATH. Install it with `uv tool install "
            f"denckring[mcp]` — the page drives the real server, not a stub."
        )
        return transcript

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    try:
        async with (
            stdio_client(StdioServerParameters(command=SERVER, args=[])) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            tools = [_as_ollama_tool(tool) for tool in (await session.list_tools()).tools]
            await _loop(session, tools, transcript, max_turns)
    except Exception as exc:
        # anyio wraps a failure inside the session in an ExceptionGroup, so the
        # useful line is rarely the outermost one. Reported rather than raised,
        # for the reason `witz.py` gives: this sits beside a verdict.
        transcript.problem = transcript.problem or f"The MCP session failed: {exc}"
    return transcript


async def _loop(
    session: Any, tools: list[dict[str, Any]], transcript: Transcript, max_turns: int
) -> None:
    messages: list[dict[str, Any]] = [{"role": "user", "content": transcript.question}]
    for _ in range(max_turns):
        message, problem = models.chat(transcript.model, messages, tools)
        if problem:
            transcript.problem = problem
            return
        calls = message.get("tool_calls") or []
        if not calls:
            transcript.answer = str(message.get("content", "")).strip()
            return
        messages.append(message)
        for call in calls:
            function = call.get("function", {})
            name = str(function.get("name", ""))
            arguments = function.get("arguments", {})
            result = await session.call_tool(name, arguments)
            text = _text_of(result)
            transcript.steps.append(
                Step(name=name, arguments=json.dumps(arguments, ensure_ascii=False), result=text)
            )
            messages.append({"role": "tool", "content": text})
    transcript.problem = (
        f"The model was still calling tools after {max_turns} turns and was stopped."
    )


#: Two presets, so the page can be driven without typing — and specifically so a
#: recording shows both halves of the surface: one asks the model to *check* a
#: text, the other to *generate* one. Both name a procedure and a language, since
#: a small model left to choose either tends to pick neither.
PRESETS = [
    (
        "Check a calculator word",
        "Use the check_text tool to check whether the German word 'Esel' satisfies the "
        "calculator_word procedure with digits 7353, lang de. Then say the verdict in "
        "one sentence.",
    ),
    (
        "Generate an anagram",
        "Use the apply_procedure tool to run the anagram procedure on the English text "
        "'dormitory'. Then tell me what it produced, in one sentence.",
    ),
]
