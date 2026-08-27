import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import BaseModel
from typer.testing import CliRunner

from denckring.cli import app
from denckring.core import registry
from denckring.core.base import ConstructiveProcedure
from denckring.core.protocol import LanguagePack, Meta, Report

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


class _NoParams(BaseModel):
    """A model of its own rather than `BaseModel` itself, which cannot be one of the
    bases `apply_params_model` combines: it is already a base of `ApplyParams`, and
    the MRO has nowhere to put it."""


class _TakesNoSeed(ConstructiveProcedure[_NoParams, BaseModel]):
    """A generator that draws nothing, which no *real* one can yet demonstrate.

    After the pilot migration every generator but `cut_up` still declares `seed`
    in its `apply` signature and so accepts it whatever it does with it. This
    stands in until Task 4 migrates a source-relative generator that genuinely
    has no seed, at which point the two tests below can name it instead.
    """

    id = "takes_no_seed"

    def __init__(self) -> None:
        # Deliberately not `super().__init__()`: it reads the catalogue, and
        # every catalogued id without an implementation declares capabilities
        # the core pack lacks — the spine would raise `MissingCapability`
        # before parameter validation, which is the half under test here.
        self.meta = Meta(
            id=self.id,
            names={"en": "takes no seed"},
            definitions={"en": "A stand-in with no parameters of its own."},
            source="test double",
            family="word",
            attribution="traditional",
            checkability="self",
            kind="constructive",
            languages=["en"],
        )

    @classmethod
    def params_model(cls) -> type[_NoParams]:
        return _NoParams

    def _check(self, text: str, pack: LanguagePack, params: _NoParams) -> Report:
        return self._report(good=1, total=1, violations=[], metrics={})

    def _apply(self, text: str, pack: LanguagePack, params: BaseModel) -> str:
        return text.upper()


@pytest.fixture
def takes_no_seed() -> Iterator[str]:
    """Registered by hand, because `register` requires a module named for the id."""
    registry._REGISTRY[_TakesNoSeed.id] = _TakesNoSeed()
    try:
        yield _TakesNoSeed.id
    finally:
        del registry._REGISTRY[_TakesNoSeed.id]


def test_apply_without_a_seed_does_not_invent_one(tmp_path: Path, takes_no_seed: str) -> None:
    """`--seed` defaults to `None`, and the unset default used to be forwarded anyway.

    Harmless while `seed` was a signature keyword every generator swallowed. Now
    that it is a parameter only the procedures that draw declare, forwarding the
    unset value would make `denckring apply` fail for every procedure that does
    not — on every invocation, seed asked for or not.
    """
    path = tmp_path / "t.txt"
    path.write_text("quiet", encoding="utf-8")
    result = runner.invoke(app, ["apply", takes_no_seed, str(path)])
    assert result.exit_code == 0
    assert "QUIET" in result.stdout


def test_asking_a_procedure_that_does_not_draw_for_a_seed_says_so(
    tmp_path: Path, takes_no_seed: str
) -> None:
    """The other direction, and the reason not to filter by what the procedure accepts:
    a caller who asked for a seed should be told the procedure has none, not ignored."""
    path = tmp_path / "t.txt"
    path.write_text("quiet", encoding="utf-8")
    result = runner.invoke(app, ["apply", takes_no_seed, str(path), "--seed", "5"])
    assert result.exit_code == 2
    assert "seed" in result.stdout


def test_apply_still_forwards_a_seed_that_was_asked_for(tmp_path: Path) -> None:
    path = tmp_path / "t.txt"
    path.write_text("one two three four five six seven eight", encoding="utf-8")
    args = ["apply", "cut_up", str(path), "--seed", "5"]
    assert runner.invoke(app, args).stdout == runner.invoke(app, args).stdout


def test_unknown_language_is_reported_not_traced(tmp_path: Path) -> None:
    path = tmp_path / "t.txt"
    path.write_text("text", encoding="utf-8")
    result = runner.invoke(app, ["check", "lipogram", str(path), "--lang", "fr"])
    assert result.exit_code == 2
    assert "denckring[fr]" in result.stdout


def test_version_prints_the_installed_version() -> None:
    """`__version__` was exported from the library but unreachable from the command
    line, which is where a bug report is written from."""
    from denckring import __version__

    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout
