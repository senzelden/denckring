from pathlib import Path

import pytest
from typer.testing import CliRunner

from denckring import check, get
from denckring.cli import app
from denckring.core.errors import InvalidParams

runner = CliRunner()


def test_source_is_exposed_in_the_schema() -> None:
    assert "source" in get("anagram").params_schema()["properties"]


def test_missing_source_is_an_invalid_params_error() -> None:
    with pytest.raises(InvalidParams):
        check("anagram", "a candidate text")


def test_cli_reads_the_source_from_a_file(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("listen", encoding="utf-8")
    candidate = tmp_path / "candidate.txt"
    candidate.write_text("silent", encoding="utf-8")
    result = runner.invoke(app, ["check", "anagram", str(candidate), "--source", str(source)])
    assert result.exit_code == 0


def test_source_on_a_procedure_that_takes_none_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("anything", encoding="utf-8")
    candidate = tmp_path / "candidate.txt"
    candidate.write_text("aaa", encoding="utf-8")
    result = runner.invoke(app, ["check", "lipogram", str(candidate), "--source", str(source)])
    assert result.exit_code == 2
