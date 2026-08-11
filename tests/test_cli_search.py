from typer.testing import CliRunner

from denckring.cli import app

runner = CliRunner()


def test_search_finds_a_procedure_by_alias() -> None:
    result = runner.invoke(app, ["search", "rhopalic"])
    assert result.exit_code == 0
    assert "snowball" in result.stdout


def test_search_finds_a_procedure_by_id_fragment() -> None:
    assert "lipogram" in runner.invoke(app, ["search", "lipo"]).stdout


def test_search_is_case_insensitive() -> None:
    assert "snowball" in runner.invoke(app, ["search", "RHOPALIC"]).stdout


def test_search_reports_no_match_and_exits_one() -> None:
    result = runner.invoke(app, ["search", "zzzznotathing"])
    assert result.exit_code == 1
    assert "No procedure" in result.stdout


def test_list_filters_by_family() -> None:
    result = runner.invoke(app, ["list", "--family", "letter"])
    assert "lipogram" in result.stdout
    assert "sonnet" not in result.stdout


def test_list_rejects_an_unknown_family() -> None:
    result = runner.invoke(app, ["list", "--family", "nonsense"])
    assert result.exit_code == 2
