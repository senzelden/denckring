"""The skill reaches the package through these, so their JSON is a contract."""

import json

from typer.testing import CliRunner

from denckring.cli import app

runner = CliRunner()


def test_describe_json_is_parseable_and_complete() -> None:
    result = runner.invoke(app, ["describe", "lipogram", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["id"] == "lipogram"
    assert "params" in payload
    assert payload["scholarly"] is None


def test_describe_scholarly_flag() -> None:
    result = runner.invoke(app, ["describe", "lipogram", "--json", "--scholarly"])
    payload = json.loads(result.stdout)
    assert payload["scholarly"]["source"]


def test_list_json_is_a_list_of_summaries() -> None:
    result = runner.invoke(app, ["list", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert payload[0]["id"]
    assert "runnable" in payload[0]


def test_describe_reports_an_unknown_id_without_a_traceback() -> None:
    result = runner.invoke(app, ["describe", "nosuch", "--json"])
    assert result.exit_code != 0
    assert "Traceback" not in result.stdout


def test_list_json_rejects_kind_filter() -> None:
    result = runner.invoke(app, ["list", "--json", "--kind", "restrictive"])
    assert result.exit_code != 0
    assert "Traceback" not in result.stdout


def test_list_json_rejects_status_filter() -> None:
    result = runner.invoke(app, ["list", "--json", "--status", "implemented"])
    assert result.exit_code != 0
    assert "Traceback" not in result.stdout
