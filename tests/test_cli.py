import json
from pathlib import Path

from typer.testing import CliRunner

from denckring.cli import app
from denckring.core.registry import get
from denckring.eval import harness

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


def test_status_prints_the_instrument_counter_on_its_own_line() -> None:
    """ADR 0033 D3: two counters, and the first keeps its meaning. The zero is printed
    rather than hidden, so the line cannot appear from nowhere with the first
    instrument entry."""
    coverage = harness.status()
    result = runner.invoke(app, ["status"])
    assert result.stdout.splitlines() == [coverage.line(), coverage.instrument_line()]


def test_eval_all_is_green() -> None:
    result = runner.invoke(app, ["eval", "--all"])
    assert result.exit_code == 0


def test_show_includes_source_and_params_schema() -> None:
    result = runner.invoke(app, ["show", "lipogram", "--json"])
    payload = json.loads(result.stdout)
    assert payload["meta"]["source"]
    assert "forbidden" in payload["params_schema"]["properties"]


def test_apply_on_a_restrictive_procedure_fails_informatively(tmp_path: Path) -> None:
    """The message is `NotConstructive`'s, the same one the library and MCP raise —
    the CLI no longer hand-writes its own wording for this failure."""
    path = tmp_path / "t.txt"
    path.write_text("text", encoding="utf-8")
    result = runner.invoke(app, ["apply", "lipogram", str(path)])
    assert result.exit_code == 2
    assert "only checks" in result.stdout


def test_apply_without_a_seed_does_not_invent_one(tmp_path: Path) -> None:
    """`--seed` defaults to `None`, and the unset default used to be forwarded anyway.

    Harmless while `seed` was a signature keyword every generator swallowed. Now
    that it is a parameter only the procedures that draw declare, forwarding the
    unset value would make `denckring apply` fail for every procedure that does
    not — on every invocation, seed asked for or not. `boustrophedon` is one of
    Task 4's seventeen: it takes no seed and needs no parameter beyond the text
    itself, so `--seed` unset must still exit clean.
    """
    path = tmp_path / "t.txt"
    path.write_text("quiet\nzone", encoding="utf-8")
    result = runner.invoke(app, ["apply", "boustrophedon", str(path)])
    assert result.exit_code == 0
    assert "enoz" in result.stdout


def test_asking_a_procedure_that_does_not_draw_for_a_seed_says_so(tmp_path: Path) -> None:
    """The other direction, and the reason not to filter by what the procedure accepts:
    a caller who asked for a seed should be told the procedure has none, not ignored."""
    path = tmp_path / "t.txt"
    path.write_text("quiet\nzone", encoding="utf-8")
    result = runner.invoke(app, ["apply", "boustrophedon", str(path), "--seed", "5"])
    assert result.exit_code == 2
    assert "seed" in result.stdout


def test_apply_still_forwards_a_seed_that_was_asked_for(tmp_path: Path) -> None:
    path = tmp_path / "t.txt"
    path.write_text("one two three four five six seven eight", encoding="utf-8")
    args = ["apply", "cut_up", str(path), "--seed", "5"]
    assert runner.invoke(app, args).stdout == runner.invoke(app, args).stdout


def test_unknown_language_is_reported_not_traced(tmp_path: Path) -> None:
    # "fr" now has a core pack (Task 2), so lipogram runs in it; "es" stands
    # in for a language this install has no pack for.
    path = tmp_path / "t.txt"
    path.write_text("text", encoding="utf-8")
    result = runner.invoke(app, ["check", "lipogram", str(path), "--lang", "es"])
    assert result.exit_code == 2
    assert "denckring[es]" in result.stdout


def test_version_prints_the_installed_version() -> None:
    """`__version__` was exported from the library but unreachable from the command
    line, which is where a bug report is written from."""
    from denckring import __version__

    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_apply_json_emits_a_production() -> None:
    result = runner.invoke(
        app, ["apply", "every_nth_word", "-p", "n=2", "--json"], input="one two three four"
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["procedure"] == "every_nth_word"
    assert payload["texts"] == ["two four"]
    assert payload["truncated"] is False


def test_apply_without_json_still_prints_one_text() -> None:
    result = runner.invoke(
        app, ["apply", "every_nth_word", "-p", "n=2"], input="one two three four"
    )
    assert result.exit_code == 0
    assert result.stdout.strip() == "two four"


def test_a_json_param_is_read_as_json(tmp_path: Path) -> None:
    """`multiple_constraint`'s `constraints` is a list of objects (ADR 0059), which
    `key=value` can only carry as JSON."""
    path = tmp_path / "t.txt"
    path.write_text("the letters were her tender ferments", encoding="utf-8")
    constraints = json.dumps(
        [
            {"id": "univocalic", "params": {"vowel": "e"}},
            {"id": "lipogram", "params": {"forbidden": "a"}},
        ]
    )
    args = ["check", "multiple_constraint", str(path), "-p", f"constraints={constraints}"]
    assert runner.invoke(app, args).exit_code == 0
    path.write_text("the cat sat", encoding="utf-8")
    assert runner.invoke(app, args).exit_code == 1


def test_a_bracketed_value_that_is_not_json_stays_a_string() -> None:
    from denckring.cli import _coerce

    assert _coerce("[ab", structured=True) == "[ab"
    assert _coerce('{"a": 1}', structured=True) == {"a": 1}


def test_json_is_decoded_only_for_a_field_typed_array_or_object() -> None:
    """A string parameter whose value happens to be JSON stays the string it was
    (ruling R-U10f): `source='[1]'` is a one-line source text, not a list."""
    from denckring.cli import _parse_params, _structured

    structured = _structured(get("n_plus_7").params_schema())
    assert "source" not in structured
    assert _parse_params(["source=[1]"], structured) == {"source": "[1]"}
    composite = _structured(get("multiple_constraint").params_schema())
    assert _parse_params(['constraints=[{"id": "lipogram"}]'], composite) == {
        "constraints": [{"id": "lipogram"}]
    }
