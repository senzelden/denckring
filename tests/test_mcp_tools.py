"""The four tools, called directly. No client, no transport."""

import pytest

pytest.importorskip("mcp", reason="needs denckring[mcp]")

from denckring.mcp.server import (
    apply_procedure_tool,
    check_text_tool,
    describe_procedure_tool,
    list_procedures_tool,
)


def test_list_returns_summaries() -> None:
    rows = list_procedures_tool()
    assert rows
    assert rows[0]["id"]


def test_list_filters_by_query() -> None:
    rows = list_procedures_tool(query="lipogram")
    assert {row["id"] for row in rows} >= {"lipogram", "serial_lipogram"}


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
