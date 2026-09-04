"""The local model, the MCP client, and the loop between them.

Everything here runs against fakes. The live path needs a 9.6 GB model and a
running daemon, and CI has neither — so what is tested is the wiring, and the
live path is exercised by hand and by the recorded scene.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, ClassVar

import pytest
from explorer import agent, models
from explorer.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


# ── the tool-shape conversion ───────────────────────────────────────────────


@dataclass
class _FakeTool:
    name: str
    description: str
    input_schema: dict[str, Any]


def test_a_tool_is_converted_by_its_snake_case_schema_attribute() -> None:
    """`input_schema`, not `inputSchema`.

    The wire format uses the camel-case name and the Python object does not, and
    this is the one error this design already made: the spike died with
    `'Tool' object has no attribute 'inputSchema'` at the line building the tool
    list, nowhere near anything that looks like a protocol concern. A `_FakeTool`
    carrying only the snake-case name fails loudly if the conversion reaches for
    the other one.
    """
    schema = {"type": "object", "properties": {"text": {"type": "string"}}}
    converted = agent._as_ollama_tool(_FakeTool("check_text", "Check a text.", schema))
    assert converted["type"] == "function"
    assert converted["function"]["name"] == "check_text"
    assert converted["function"]["parameters"] == schema


def test_a_very_long_tool_description_is_truncated() -> None:
    """denckring's own docstrings run long, and four of them in every request is
    context the model spends on prose rather than on the call."""
    converted = agent._as_ollama_tool(_FakeTool("x", "y" * 4000, {}))
    assert len(converted["function"]["description"]) == 900


# ── the turn loop ───────────────────────────────────────────────────────────


class _FakeSession:
    """Stands in for an MCP session. Records what was called."""

    def __init__(self, result: str = '{"satisfied": true}') -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._result = result

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((name, arguments))

        class _Block:
            text = self._result

        class _Result:
            content: ClassVar[list[Any]] = [_Block()]

        return _Result()


def _model(replies: list[dict[str, Any]]) -> Any:
    """A fake `models.chat` returning `replies` in order."""
    remaining = list(replies)

    def chat(model: str, messages: list[Any], tools: list[Any]) -> tuple[dict[str, Any], str]:
        return remaining.pop(0), ""

    return chat


def test_a_tool_call_is_executed_and_fed_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        models,
        "chat",
        _model(
            [
                {
                    "tool_calls": [
                        {"function": {"name": "check_text", "arguments": {"text": "Esel"}}}
                    ]
                },
                {"content": "It satisfies."},
            ]
        ),
    )
    session = _FakeSession()
    transcript = agent.Transcript(question="q", model="m")
    asyncio.run(agent._loop(session, [], transcript, 4))

    assert session.calls == [("check_text", {"text": "Esel"})]
    assert [step.name for step in transcript.steps] == ["check_text"]
    assert json.loads(transcript.steps[0].arguments) == {"text": "Esel"}
    assert transcript.steps[0].result == '{"satisfied": true}'
    assert transcript.answer == "It satisfies."
    assert transcript.problem == ""


def test_an_answer_with_no_tool_call_is_kept_and_not_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Worth keeping rather than rejecting: a model that answers without calling
    anything has not demonstrated what the page exists to demonstrate, and the
    page says so — but it is not a failure of the wiring."""
    monkeypatch.setattr(models, "chat", _model([{"content": "I think so."}]))
    transcript = agent.Transcript(question="q", model="m")
    asyncio.run(agent._loop(_FakeSession(), [], transcript, 4))
    assert transcript.answer == "I think so."
    assert transcript.steps == []
    assert transcript.problem == ""


def test_a_model_that_never_stops_calling_is_stopped(monkeypatch: pytest.MonkeyPatch) -> None:
    call = {"tool_calls": [{"function": {"name": "check_text", "arguments": {}}}]}
    monkeypatch.setattr(models, "chat", _model([call] * 3))
    transcript = agent.Transcript(question="q", model="m")
    asyncio.run(agent._loop(_FakeSession(), [], transcript, 3))
    assert "stopped" in transcript.problem
    assert len(transcript.steps) == 3


def test_a_model_failure_is_reported_not_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    def chat(model: str, messages: list[Any], tools: list[Any]) -> tuple[dict[str, Any], str]:
        return {}, "Could not reach Ollama."

    monkeypatch.setattr(models, "chat", chat)
    transcript = agent.Transcript(question="q", model="m")
    asyncio.run(agent._loop(_FakeSession(), [], transcript, 4))
    assert transcript.problem == "Could not reach Ollama."


# ── the guards before a session is ever opened ──────────────────────────────


def test_an_empty_question_never_spawns_a_server() -> None:
    transcript = asyncio.run(agent.run("   ", "m"))
    assert transcript.problem == "Ask something first."


def test_a_missing_server_is_named_rather_than_failing_inside_anyio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`shutil.which` is checked first on purpose: a missing binary otherwise
    surfaces from inside anyio's task group, wrapped in an ExceptionGroup whose
    outermost line says nothing about PATH."""
    monkeypatch.setattr("explorer.agent.shutil.which", lambda _: None)
    transcript = asyncio.run(agent.run("anything", "m"))
    assert "denckring-mcp" in transcript.problem
    assert "PATH" in transcript.problem


# ── the provider ────────────────────────────────────────────────────────────


def test_a_model_ollama_refuses_is_listed_with_its_own_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The three German and European models cannot call tools, and the page must
    say why rather than dropping them: a reader would otherwise see one
    English-first model offered and learn nothing about the rest."""
    monkeypatch.setattr(models, "_TOOL_SUPPORT", {})
    monkeypatch.setattr(
        models,
        "_post",
        lambda path, payload: (
            (None, "registry.ollama.ai/library/teuken-7b:latest does not support tools")
            if payload["model"] == "teuken-7b"
            else ({"message": {}}, "")
        ),
    )
    assert models.supports_tools("gemma4") == (True, "")
    supported, reason = models.supports_tools("teuken-7b")
    assert supported is False
    assert "does not support tools" in reason


def test_the_tool_probe_is_asked_once_per_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(models, "_TOOL_SUPPORT", {})
    calls: list[str] = []

    def post(path: str, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        calls.append(payload["model"])
        return {"message": {}}, ""

    monkeypatch.setattr(models, "_post", post)
    models.supports_tools("gemma4")
    models.supports_tools("gemma4")
    assert calls == ["gemma4"]


def test_no_daemon_is_a_message_not_a_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(models, "HOST", "http://127.0.0.1:1")
    found, problem = models.available()
    assert found == []
    assert "Could not reach Ollama" in problem


# ── the page ────────────────────────────────────────────────────────────────


def test_the_page_renders_without_a_daemon(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(models, "available", lambda: ([], "Could not reach Ollama at nowhere."))
    response = client.get("/agent")
    assert response.status_code == 200
    assert "Could not reach Ollama" in response.text


def test_the_page_offers_both_halves_of_the_surface() -> None:
    """One preset checks and one generates, so a recording shows `check_text`
    and `apply_procedure` without anyone typing."""
    assert len(agent.PRESETS) == 2
    assert "check_text" in agent.PRESETS[0][1]
    assert "apply_procedure" in agent.PRESETS[1][1]
