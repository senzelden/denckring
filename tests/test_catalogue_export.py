import csv
import io
import json
from pathlib import Path

from typer.testing import CliRunner

from denckring import describe
from denckring.cli import app
from denckring.core import catalogue
from denckring.eval.harness import implemented_ids

runner = CliRunner()


def test_json_export_contains_every_row() -> None:
    result = runner.invoke(app, ["catalogue", "export", "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload["procedures"]) == len(catalogue.ids())
    assert payload["licence"].startswith("CC BY 4.0")


def test_json_export_rows_carry_the_new_fields() -> None:
    payload = json.loads(runner.invoke(app, ["catalogue", "export", "--format", "json"]).stdout)
    row = next(r for r in payload["procedures"] if r["id"] == "snowball")
    assert row["family"] == "letter"
    assert row["attribution"]
    assert "rhopalic" in row["aliases"]


def test_csv_export_has_one_line_per_row_plus_a_header() -> None:
    result = runner.invoke(app, ["catalogue", "export", "--format", "csv"])
    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    assert len(rows) == len(catalogue.ids())
    assert rows[0]["id"]


def test_export_writes_to_a_file_when_asked(tmp_path: Path) -> None:
    target = tmp_path / "catalogue.json"
    result = runner.invoke(
        app, ["catalogue", "export", "--format", "json", "--output", str(target)]
    )
    assert result.exit_code == 0
    assert json.loads(target.read_text(encoding="utf-8"))["procedures"]


def test_unknown_format_is_rejected() -> None:
    result = runner.invoke(app, ["catalogue", "export", "--format", "xml"])
    assert result.exit_code == 2


def test_json_export_rows_carry_their_corpus_share() -> None:
    """ADR 0062: additive. An implemented row carries the same `corpus` as `describe`;
    a catalogued row with no checker has no golden cases to count, and says so with
    `null` rather than with zeros that would read as "counted, none found"."""
    payload = json.loads(runner.invoke(app, ["catalogue", "export", "--format", "json"]).stdout)
    implemented = set(implemented_ids())
    for row in payload["procedures"]:
        if row["id"] in implemented:
            assert row["corpus"] == describe(row["id"]).corpus.model_dump(), row["id"]
        else:
            assert row["corpus"] is None, row["id"]
    keys = set(next(r for r in payload["procedures"] if r["id"] == "acrostic")["corpus"])
    assert keys == {"external_passing", "external_failing", "constructed", "self_generated", "gap"}
