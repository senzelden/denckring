import json
from pathlib import Path

from typer.testing import CliRunner

from denckring.cli import app

runner = CliRunner()


def test_list_prints_registered_ids() -> None:
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "lipogram" in result.stdout


def test_check_exits_zero_when_satisfied(tmp_path: Path) -> None:
    path = tmp_path / "t.txt"
    path.write_text("a small conforming bit of writing", encoding="utf-8")
    result = runner.invoke(app, ["check", "lipogram", str(path), "--param", "forbidden=z"])
    assert result.exit_code == 0


def test_check_exits_one_when_unsatisfied(tmp_path: Path) -> None:
    path = tmp_path / "t.txt"
    path.write_text("here is the letter", encoding="utf-8")
    result = runner.invoke(app, ["check", "lipogram", str(path)])
    assert result.exit_code == 1


def test_check_json_emits_a_valid_report(tmp_path: Path) -> None:
    path = tmp_path / "t.txt"
    path.write_text("here is the letter", encoding="utf-8")
    result = runner.invoke(app, ["check", "lipogram", str(path), "--json"])
    payload = json.loads(result.stdout)
    assert payload["procedure"] == "lipogram"
    assert payload["satisfied"] is False


def test_check_reads_stdin() -> None:
    result = runner.invoke(app, ["check", "lipogram", "-"], input="aaa")
    assert result.exit_code == 0


def test_status_prints_the_coverage_line() -> None:
    result = runner.invoke(app, ["status"])
    assert "catalogued" in result.stdout
    assert "validated" in result.stdout


def test_eval_all_is_green() -> None:
    result = runner.invoke(app, ["eval", "--all"])
    assert result.exit_code == 0


def test_show_includes_source_and_params_schema() -> None:
    result = runner.invoke(app, ["show", "lipogram", "--json"])
    payload = json.loads(result.stdout)
    assert payload["meta"]["source"]
    assert "forbidden" in payload["params_schema"]["properties"]


def test_apply_on_a_restrictive_procedure_fails_informatively(tmp_path: Path) -> None:
    path = tmp_path / "t.txt"
    path.write_text("text", encoding="utf-8")
    result = runner.invoke(app, ["apply", "lipogram", str(path)])
    assert result.exit_code == 2
    assert "restrictive" in result.stdout


def test_unknown_language_is_reported_not_traced(tmp_path: Path) -> None:
    path = tmp_path / "t.txt"
    path.write_text("text", encoding="utf-8")
    result = runner.invoke(app, ["check", "lipogram", str(path), "--lang", "fr"])
    assert result.exit_code == 2
    assert "denckring[fr]" in result.stdout
