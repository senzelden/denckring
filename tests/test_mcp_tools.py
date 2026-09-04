"""The four tools, called directly. No client, no transport."""

import asyncio
import re

import pytest

pytest.importorskip("mcp", reason="needs denckring[mcp]")

from denckring.mcp.server import (
    apply_procedure_tool,
    check_text_tool,
    describe_procedure_tool,
    list_procedures_tool,
    server,
)


def test_list_returns_summaries() -> None:
    rows = list_procedures_tool()
    assert isinstance(rows, list), rows
    assert rows
    assert rows[0]["id"]


def test_list_filters_by_query() -> None:
    rows = list_procedures_tool(query="lipogram")
    assert isinstance(rows, list), rows
    assert {row["id"] for row in rows} >= {"lipogram", "serial_lipogram"}


def test_an_unmatched_filter_is_an_empty_list_not_an_error() -> None:
    """`summaries` filters; it does not reject. The list tool has no failure mode."""
    assert list_procedures_tool(family="nosuchfamily") == []


def test_describe_returns_the_param_schema() -> None:
    described = describe_procedure_tool("lipogram")
    assert "properties" in described["params"]


def test_check_returns_a_report() -> None:
    report = check_text_tool("lipogram", "brown fox", {"forbidden": "e"})
    assert report["satisfied"] is True


def test_check_reports_a_violation_a_model_can_act_on() -> None:
    report = check_text_tool("lipogram", "the fence", {"forbidden": "e"})
    assert report["satisfied"] is False
    assert report["violations"][0]["rule"] == "forbidden_letter"
    assert report["violations"][0]["offset"] is not None


def test_an_unknown_procedure_is_data_not_an_exception() -> None:
    """A raised error reaches the model as a transport failure it cannot read."""
    result = check_text_tool("nosuch", "text")
    assert result["code"] == "unknown_procedure"
    assert result["detail"]["suggestions"] == []


def test_bad_params_are_data_not_an_exception() -> None:
    result = check_text_tool("pangrammatic_window", "text", {"max_length": 3})
    assert result["code"] == "invalid_params"


def test_apply_returns_text() -> None:
    result = apply_procedure_tool("n_plus_7", "the cat sleeps")
    assert result["text"]
    assert result["text"] != "the cat sleeps"


def test_apply_on_a_restrictive_procedure_is_data_not_an_exception() -> None:
    result = apply_procedure_tool("lipogram", "text", {"forbidden": "e"})
    assert "code" in result


def test_the_client_sees_names_without_the_implementation_suffix() -> None:
    """`_tool` exists so the functions stay importable. A client must not see it."""
    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert names == {"list_procedures", "describe_procedure", "check_text", "apply_procedure"}


def test_no_description_sends_the_model_to_a_tool_that_is_not_there() -> None:
    """A description naming `check_text_tool` tells the model to call something absent."""
    tools = asyncio.run(server.list_tools())
    internal = {tool.name + "_tool" for tool in tools}
    for tool in tools:
        referenced = set(re.findall(r"`(\w+)`", tool.description or ""))
        assert not referenced & internal, f"{tool.name} names an internal function"


def test_a_device_path_that_escapes_its_search_directories_is_data_not_a_leak() -> None:
    """The path a client supplies for `device` is exactly as untrusted as any other param.

    `check_text_tool` passes `params` straight through to `check(...)`, so a model
    asking for `device="../../etc/passwd"` reaches `device.load` directly — the same
    route the CLI's `--param device=...` takes. The fix lives in `device.load`
    (`tests/test_device.py` covers it in depth); this pins that the MCP tool, which is
    what actually exposes `device` to a model, surfaces the rejection as ordinary data
    rather than as a transport failure — or as a loaded file.
    """
    result = check_text_tool(
        "denckring", "wort", {"device": "../../../../../../etc/passwd"}, lang="de"
    )
    assert result["code"] == "unknown_device"


def test_apply_procedure_carries_the_other_results() -> None:
    from denckring.mcp.server import apply_procedure_tool

    out = apply_procedure_tool("every_nth_word", "one two three four", {"n": 2})
    assert out["text"] == "two four"
    assert out["texts"] == ["two four"]
    assert out["truncated"] is False


def test_apply_procedure_text_is_still_the_first_text() -> None:
    """Additive: `text` keeps its meaning, so no existing caller breaks."""
    from denckring.mcp.server import apply_procedure_tool

    out = apply_procedure_tool("cut_up", "one two three four", {"seed": 1})
    assert out["text"] == out["texts"][0]


def test_apply_procedure_carries_the_metrics_a_ranking_was_computed_from() -> None:
    """ADR 0031's `attestation: "mask"` is a no-op over MCP without this.

    `denckring` ranks its spun words by whether the dictionary attests them and
    puts that on each `Candidate.metrics`; `anagram` ranks covers by the SCOWL
    band of their least common word. The tool returned `texts` alone, so a client
    was shown an order and never the number it was computed from — which
    `Candidate`'s own docstring calls the thing a caller "deserves to see".
    """
    from denckring.mcp.server import apply_procedure_tool

    out = apply_procedure_tool(
        "denckring", "", {"attestation": "mask", "max_results": 5}, lang="de"
    )
    assert "candidates" in out, out
    assert [c["text"] for c in out["candidates"]] == out["texts"]
    assert any(c["metrics"] for c in out["candidates"]), "every metric was dropped"


def test_apply_procedure_reports_a_language_it_cannot_generate_in() -> None:
    """`constructive` is language-blind and `apply_missing` is not.

    `anagram` is `constructive: true` everywhere, and in German its generator
    cannot run at all: SCOWL ships in `denckring-en-data` alone (ADR 0028). A
    caller who did what `apply_procedure`'s docstring said — read `constructive`
    — was sent straight into a `missing_capability`.
    """
    from denckring.mcp.server import apply_procedure_tool, describe_procedure_tool

    described = describe_procedure_tool("anagram", lang="de")
    assert described["constructive"] is True
    assert described["apply_missing"] == ["lexicon.graded_words"]

    refused = apply_procedure_tool("anagram", "dormitory", lang="de")
    assert refused["code"] == "missing_capability"


def test_the_apply_docstring_sends_callers_to_the_language_aware_field() -> None:
    """The docstring named `constructive` and never `apply_missing`, so it was
    telling callers to read the field that cannot answer the question."""
    from denckring.mcp.server import apply_procedure_tool

    doc = apply_procedure_tool.__doc__ or ""
    assert "apply_missing" in doc
