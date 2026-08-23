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
