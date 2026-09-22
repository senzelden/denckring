import gzip
import hashlib
import json
from pathlib import Path
from typing import cast

import pytest

from denckring import check
from denckring.core.errors import MissingCapability
from denckring.lang.en import EnglishPack

DATA = pytest.importorskip("denckring_en_data")
PIDS = ["antonymic_substitution", "antonymic_translation", "synonymic_substitution"]


@pytest.mark.parametrize("pid", PIDS)
def test_every_occurrence_needs_a_relation_and_extra_words_fail(pid: str) -> None:
    target = "large" if pid == "synonymic_substitution" else "small"
    assert check(pid, f"{target} {target}", source="big big").satisfied
    for candidate in (target, f"{target} {target} {target}", "big big"):
        assert not check(pid, candidate, source="big big").satisfied


@pytest.mark.parametrize("pid", PIDS)
def test_unknown_function_words_and_empty_sources_never_pass(pid: str) -> None:
    target = "large" if pid == "synonymic_substitution" else "small"
    report = check(pid, f"{target} qzxq", source="big qzxq")
    assert not report.satisfied
    assert report.metrics["unknown_words"] == 1
    assert "unknown_relation" in [v.rule for v in report.violations]
    assert not check(pid, "", source="").satisfied
    assert not check(pid, "the " + target, source="the big").satisfied


@pytest.mark.parametrize("pid", PIDS)
def test_order_case_and_punctuation(pid: str) -> None:
    source = "big hot"
    target = "large spicy" if pid == "synonymic_substitution" else "small cold"
    assert check(pid, target.upper() + "!", source=source).satisfied
    assert not check(pid, " ".join(reversed(target.split())), source=source).satisfied


def test_base_capabilities_refuse_and_data_is_immutable() -> None:
    for relation in ("synonyms", "antonyms"):
        with pytest.raises(MissingCapability):
            getattr(EnglishPack(), relation)("big")
        table = DATA.relations(relation)
        with pytest.raises(TypeError):
            cast(dict[str, tuple[str, ...]], table)["big"] = ("fabricated",)
        assert all(word not in targets for word, targets in table.items())
        assert all(target.isalpha() for targets in table.values() for target in targets)


def test_relation_data_matches_its_auditable_metadata() -> None:
    root = Path(DATA.__file__).parent / "data"
    metadata = json.loads((root / "metadata.json").read_text())
    for relation in ("synonyms", "antonyms"):
        payload = (root / f"{relation}.json.gz").read_bytes()
        assert hashlib.sha256(payload).hexdigest() == metadata["relations"][relation]["sha256"]
        assert (
            len(json.loads(gzip.decompress(payload))) == metadata["counts"][f"{relation}.json.gz"]
        )
        assert metadata["relations"][relation]["lexicon"] == "oewn:2024"


def test_public_gate_does_not_pretend_core_has_relations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("denckring.lang.get_pack", lambda lang="en": EnglishPack())
    with pytest.raises(MissingCapability):
        check("antonymic_substitution", "cold", source="hot")


@pytest.mark.parametrize("lang", ["de", "fr"])
@pytest.mark.parametrize("capability", ["lexicon.synonyms", "lexicon.antonyms", "corpus.proverbs"])
def test_missing_capability_does_not_recommend_an_extra_that_cannot_help(
    lang: str, capability: str
) -> None:
    from denckring.core.errors import extra_for

    assert extra_for(lang, capability) is None
