"""A verdict records how it was reached, not only what it was.

`Report` said `satisfied` and `score` and nothing about the run behind them, so
reproducing one needed three facts none of its output carried: which version
decided, which pack answered, and which data that pack was reading. Two of them
were not reachable from Python at all — no pack exposed a version, and
`Production` never echoed the seed it was handed, so `apply --seed 7 --json`
printed an object that did not contain 7.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import get_args

import pytest
from typer.testing import CliRunner

import denckring
from denckring import __version__, check, produce
from denckring.cli import app
from denckring.core.protocol import Evidence
from denckring.core.provenance import SCHEMA_VERSION, pack_digests, pack_provenance, provenance
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
    """`check --json` is named in the README among the stable surfaces, so
    the stamp has to reach it too."""
    source = tmp_path / "t.txt"
    source.write_text("a conforming bit of writing\n", encoding="utf-8")
    result = CliRunner().invoke(
        app, ["check", "lipogram", str(source), "--param", "forbidden=z", "--json"]
    )
    assert result.exit_code == 0, result.stdout
    assert json.loads(result.stdout)["provenance"]["denckring"] == __version__


_REPORT_KEYS = frozenset(
    {
        "procedure",
        "satisfied",
        "score",
        "violations",
        "metrics",
        "evidence",
        "provenance",
        "estimated",
    }
)
_PRODUCTION_KEYS = frozenset(
    {"procedure", "candidates", "truncated", "metrics", "provenance", "texts"}
)

#: Every key `Report` and `Production` serialise, and every value `Evidence.basis` can
#: take, per schema version. An added field or basis value changes a set; finding no
#: entry for the version in force means it landed without the minor bump
#: `SCHEMA_VERSION`'s own comment requires (U3 review I2). A closed value set is
#: shape too: a parser holding 1.1's two bases refuses a report carrying a third.
SERIALISED_KEYS: dict[str, dict[str, frozenset[str]]] = {
    "1.1": {
        "Report": _REPORT_KEYS,
        "Production": _PRODUCTION_KEYS,
        "Evidence.basis": frozenset({"dictionary", "estimated"}),
    },
    "1.2": {
        "Report": _REPORT_KEYS,
        "Production": _PRODUCTION_KEYS,
        "Evidence.basis": frozenset({"dictionary", "ambiguous", "estimated"}),
    },
}


def test_the_schema_version_moves_with_the_serialised_shape() -> None:
    report = check("lipogram", "a text", forbidden="e")
    production = produce("anagram", "listen")
    shapes = SERIALISED_KEYS.get(SCHEMA_VERSION)
    assert shapes is not None, f"no recorded shape for schema {SCHEMA_VERSION}"
    assert set(report.model_dump(mode="json")) == shapes["Report"]
    assert set(production.model_dump(mode="json")) == shapes["Production"]
    basis = Evidence.model_fields["basis"].annotation
    assert set(get_args(basis)) == shapes["Evidence.basis"]


def test_the_readme_states_the_schema_version_in_force() -> None:
    """The stability promise names the version a JSON consumer pins to. It said `1.1`
    after the bump to `1.2` (U6 review I1), and nothing noticed: a consumer pinning it
    would refuse every report the release writes."""
    import re

    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    stated = re.findall(r"`(\d+\.\d+)` since", readme)
    assert stated == [SCHEMA_VERSION], stated


def test_pack_provenance_carries_content_digests() -> None:
    digests = denckring.pack_provenance("en").digests
    assert {"graded_words", "files"} <= set(digests)
    assert all(len(v) == 64 for v in digests.values())


def test_the_graded_words_digest_is_the_documented_canonical_form() -> None:
    """The promise is that a caller can recompute it (ADR 0060 D4)."""
    words = denckring.get_pack("en").graded_words()
    payload = json.dumps(sorted(words.items()), ensure_ascii=False, separators=(",", ":"))
    expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    assert denckring.pack_provenance("en").digests["graded_words"] == expected


def test_a_pack_lacking_a_surface_omits_its_digest() -> None:
    class Bare:
        data_distributions: tuple[str, ...] = ()

    assert pack_digests(Bare()) == {}


def test_a_check_does_not_pay_for_digests() -> None:
    report = denckring.check("lipogram", "abc", forbidden="e")
    assert report.provenance is not None and report.provenance.pack.digests == {}


def test_a_surface_that_raises_a_capability_error_omits_its_digest() -> None:
    from denckring.core.errors import MissingCapability

    class Partial:
        data_distributions: tuple[str, ...] = ()

        def graded_words(self) -> dict[str, int]:
            return {"a": 1}

        def nouns(self) -> set[str]:
            raise MissingCapability("p", "xx", "nouns")

    assert set(pack_digests(Partial())) == {"graded_words"}


def test_the_files_digest_is_stable_and_follows_the_data() -> None:
    first = denckring.pack_provenance("en").digests["files"]
    assert denckring.pack_provenance("en").digests["files"] == first
    assert denckring.pack_provenance("fr").digests["files"] != first


def test_the_files_digest_ignores_metadata_and_follows_data(tmp_path: Path) -> None:
    """The rule: package bytes move it, dist-info (which carries the version) does not."""
    from denckring.core.provenance import _trees_digest

    pkg = tmp_path / "pkg_data"
    (pkg / "data").mkdir(parents=True)
    (pkg / "data" / "words.txt").write_text("alpha\n")
    (pkg / "__pycache__").mkdir()
    (pkg / "__pycache__" / "x.pyc").write_bytes(b"1")
    dist = tmp_path / "pkg_data-1.0.dist-info"
    dist.mkdir()
    (dist / "METADATA").write_text("Version: 1.0\n")

    before = _trees_digest({"pkg-data": pkg})
    (dist / "METADATA").write_text("Version: 2.0\n")
    (pkg / "__pycache__" / "x.pyc").write_bytes(b"2")
    assert _trees_digest({"pkg-data": pkg}) == before
    (pkg / "data" / "words.txt").write_text("beta\n")
    assert _trees_digest({"pkg-data": pkg}) != before
