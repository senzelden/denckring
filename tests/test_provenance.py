"""A verdict records how it was reached, not only what it was.

`Report` said `satisfied` and `score` and nothing about the run behind them, so
reproducing one needed three facts none of its output carried: which version
decided, which pack answered, and which data that pack was reading. Two of them
were not reachable from Python at all — no pack exposed a version, and
`Production` never echoed the seed it was handed, so `apply --seed 7 --json`
printed an object that did not contain 7.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from denckring import __version__, check, produce
from denckring.cli import app
from denckring.core.provenance import SCHEMA_VERSION, pack_provenance, provenance
from denckring.lang import get_pack


def test_every_check_is_stamped(procedure_id: str) -> None:
    """Every registered procedure, because the stamp is applied at the one place
    they all pass through rather than in each of the hundred and twenty-two
    places a `Report` is built — `pangram` builds its own and must still carry it.
    """
    from denckring.core.errors import DenckringError
    from denckring.core.registry import get

    try:
        report = get(procedure_id).check("a text to check")
    except DenckringError:
        pytest.skip("needs a parameter this test does not supply")
    assert report.provenance is not None
    assert report.provenance.denckring == __version__
    assert report.provenance.schema_version == SCHEMA_VERSION


def test_the_schema_version_is_not_the_package_version() -> None:
    """Kept apart on purpose: a caller reads the schema version to decide whether
    it can still parse the object, and tying it to the release would make every
    patch look like a shape change. They may coincide; they must not be the same
    field."""
    dumped = provenance(get_pack("en"), "en").model_dump()
    assert dumped["denckring"] == __version__
    assert dumped["schema_version"] == SCHEMA_VERSION
    # Two keys, so a consumer can pin the shape without pinning the release.
    # They are allowed to hold equal strings; they are not allowed to be one field.
    assert {"denckring", "schema_version"} <= dumped.keys()


def test_a_pack_reports_the_data_it_reads() -> None:
    """German is the case a single version string could not describe: the
    lexicon, the pronunciations and the frequency bands are three distributions,
    and `GermanWiktionaryFrequencyPack` layers all three."""
    german = pack_provenance(get_pack("de"), "de")
    assert german.lang == "de"
    if german.data:  # only with the data extras installed
        assert "denckring-de-data" in german.data
        assert all(version for version in german.data.values())


def test_a_core_pack_names_no_distribution() -> None:
    """A built-in default reads no data files, so it has nothing to name — its
    content is pinned by the package version recorded beside it."""
    from denckring.lang.en import EnglishPack

    assert pack_provenance(EnglishPack(), "en").data == {}


def test_provenance_records_the_fold_policy_in_force() -> None:
    """`fold_diacritics` decides whether `ä` counts as `a`, which is the single
    parameter most able to change a verdict without changing the text. A run that
    does not record it cannot be replayed."""
    assert check("lipogram", "Bar", forbidden="z").provenance.fold_diacritics is True  # type: ignore[union-attr]
    assert (
        check("lipogram", "Bar", forbidden="z", fold_diacritics=False).provenance.fold_diacritics  # type: ignore[union-attr]
        is False
    )


def test_a_procedure_with_no_fold_records_none() -> None:
    """`None` is not `False`. A procedure that never compares letters did not
    choose a policy, and saying it chose the off one would be an invention."""
    assert check("haiku", "one\ntwo\nthree").provenance.fold_diacritics is None  # type: ignore[union-attr]


def test_a_production_echoes_the_seed_it_drew_with() -> None:
    """The reason `Production` needed this at all: `seed` is an input, so it
    appeared nowhere in the output and a caller who had not kept it could not
    repeat the draw."""
    produced = produce("cut_up", "one two three four five six", seed=7)
    assert produced.provenance is not None
    assert produced.provenance.seed == 7


def test_a_generator_that_does_not_draw_records_no_seed() -> None:
    produced = produce("anagram", "dormitory")
    assert produced.provenance is not None
    assert produced.provenance.seed is None


def test_the_cli_json_carries_the_seed(tmp_path: Path) -> None:
    """The failure in the form a user meets it. `apply --seed 7 --json` printed a
    Production that did not contain 7."""
    source = tmp_path / "t.txt"
    source.write_text("one two three four five six seven eight\n", encoding="utf-8")
    result = CliRunner().invoke(app, ["apply", "cut_up", str(source), "--seed", "7", "--json"])
    assert result.exit_code == 0, result.stdout
    assert json.loads(result.stdout)["provenance"]["seed"] == 7


def test_the_cli_check_json_carries_provenance(tmp_path: Path) -> None:
    """`check --json` is named in the README among the five stable surfaces, so
    the stamp has to reach it too."""
    source = tmp_path / "t.txt"
    source.write_text("a conforming bit of writing\n", encoding="utf-8")
    result = CliRunner().invoke(
        app, ["check", "lipogram", str(source), "--param", "forbidden=z", "--json"]
    )
    assert result.exit_code == 0, result.stdout
    assert json.loads(result.stdout)["provenance"]["denckring"] == __version__
