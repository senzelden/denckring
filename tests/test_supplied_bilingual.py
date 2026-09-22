import copy
import json
from typing import Any

import pytest

from denckring import check
from denckring.core.errors import InvalidParams
from denckring.core.protocol import Report

GLOSS: dict[str, Any] = {
    "version": "supplied-bilingual-v1",
    "source_language": "en",
    "target_language": "fr",
    "provenance": "constructed test data; not a verified bilingual dictionary",
    "glosses": {"cat": ["petit animal"], "dog": ["animal fidèle"]},
}
SOUND: dict[str, Any] = {
    "version": "supplied-bilingual-v1",
    "source_language": "en",
    "target_language": "fr",
    "provenance": "constructed test data; not a verified bilingual dictionary",
    "alphabet": ["a", "b", "c"],
    "source_pronunciations": {"cat": ["a", "b"]},
    "target_pronunciations": {"chat": ["a", "b"], "mot": ["a", "c"]},
}


def gloss(candidate: str, source: str = "cat dog", data: dict[str, Any] | None = None) -> Report:
    return check(
        "definitional_translation",
        candidate,
        source=source,
        data=json.dumps(GLOSS if data is None else data),
    )


def sound(
    candidate: str, source: str = "cat", data: dict[str, Any] | None = None, threshold: float = 0
) -> Report:
    return check(
        "homophonic_translation",
        candidate,
        source=source,
        data=json.dumps(SOUND if data is None else data),
        max_distance=threshold,
    )


def test_glosses_cover_each_occurrence_in_order_without_extras() -> None:
    assert gloss("petit animal animal fidèle").satisfied
    assert gloss("PETIT animal, animal fidèle!").satisfied
    for candidate in (
        "animal fidèle petit animal",
        "petit animal",
        "petit animal animal fidèle extra",
    ):
        assert not gloss(candidate).satisfied
    assert not gloss("petit animal", "cat cat").satisfied
    assert gloss("petit animal petit animal", "cat cat").satisfied


def test_ambiguous_prefixes_need_complete_segmentation_not_greedy_matching() -> None:
    data = copy.deepcopy(GLOSS)
    data["glosses"] = {"cat": ["x", "x y"], "dog": ["z"]}
    assert gloss("x y z", data=data).satisfied
    data["glosses"] = {"cat": ["x y", "x"], "dog": ["y z"]}
    assert gloss("x y z", data=data).satisfied


def test_missing_gloss_and_empty_source_fail_explicitly() -> None:
    report = gloss("petit animal", "cat missing")
    assert not report.satisfied
    assert [v.rule for v in report.violations] == ["unknown_gloss"]
    assert not gloss("", "").satisfied


def test_sound_distance_and_inclusive_boundary() -> None:
    assert sound("chat").satisfied
    report = sound("mot", threshold=0.5)
    assert report.satisfied
    assert report.metrics["distance"] == 0.5
    assert not sound("mot", threshold=0.49).satisfied
    assert not sound("mot chat", threshold=0).satisfied


def test_unknown_pronunciations_cannot_shorten_the_comparison() -> None:
    for source, target in (("cat unknown", "chat"), ("cat", "chat unknown")):
        report = sound(target, source=source, threshold=1)
        assert not report.satisfied
        assert "distance" not in report.metrics
        assert any(v.rule == "unknown_pronunciation" for v in report.violations)
    assert not sound("", "").satisfied
    assert not sound("", "cat").satisfied


def test_word_boundaries_are_not_silently_compared_as_phonemes() -> None:
    data = copy.deepcopy(SOUND)
    data["target_pronunciations"] = {"un": ["a"], "mot": ["b"]}
    assert sound("un mot", data=data).satisfied


@pytest.mark.parametrize(
    "field,value",
    [("version", "unknown"), ("target_language", "en"), ("provenance", " "), ("surprise", True)],
)
def test_bad_data_headers_are_parameter_errors(field: str, value: object) -> None:
    for pid, original in (("definitional_translation", GLOSS), ("homophonic_translation", SOUND)):
        data = copy.deepcopy(original)
        data[field] = value
        extra: dict[str, Any] = {"max_distance": 0} if pid == "homophonic_translation" else {}
        with pytest.raises(InvalidParams):
            check(
                pid,
                "x",
                source="cat",
                data=json.dumps(data),
                **extra,
            )


@pytest.mark.parametrize(
    "mapping",
    [
        {"cat": []},
        {"cat": [""]},
        {"cat": ["..."]},
        {"cat": ["x"], "CAT": ["y"]},
        {"two words": ["x"]},
    ],
)
def test_invalid_gloss_entries_are_rejected(mapping: dict[str, Any]) -> None:
    data = copy.deepcopy(GLOSS)
    data["glosses"] = mapping
    with pytest.raises(InvalidParams):
        gloss("x", data=data)


def test_duplicate_json_and_wrong_language_are_rejected() -> None:
    data = json.dumps(GLOSS).replace('"glosses":', '"provenance": "duplicate", "glosses":')
    with pytest.raises(InvalidParams):
        check("definitional_translation", "x", source="cat", data=data)
    with pytest.raises(InvalidParams):
        check("definitional_translation", "x", lang="de", source="cat", data=json.dumps(GLOSS))
    with pytest.raises(InvalidParams):
        check(
            "homophonic_translation",
            "x",
            lang="de",
            source="cat",
            data=json.dumps(SOUND),
            max_distance=0,
        )


@pytest.mark.parametrize("alphabet", [["a", "a"], [""], ["a b"], ["a"]])
def test_shared_alphabet_is_validated(alphabet: list[str]) -> None:
    data = copy.deepcopy(SOUND)
    data["alphabet"] = alphabet
    with pytest.raises(InvalidParams):
        sound("chat", data=data)


def test_threshold_is_required_finite_and_bounded() -> None:
    for value in (-1, 1.01, float("nan"), float("inf")):
        with pytest.raises(InvalidParams):
            sound("chat", threshold=value)
    with pytest.raises(InvalidParams):
        check("homophonic_translation", "chat", source="cat", data=json.dumps(SOUND))


def test_resource_limits_fail_as_parameters() -> None:
    with pytest.raises(InvalidParams):
        gloss("x", "cat " * 4097)
    data = copy.deepcopy(SOUND)
    data["source_pronunciations"]["cat"] = ["a"] * 4097
    with pytest.raises(InvalidParams):
        sound("chat", data=data)


def test_non_default_source_language_and_unicode_normalization() -> None:
    data = copy.deepcopy(GLOSS)
    data["source_language"] = "de"
    data["glosses"] = {"Katze": ["créature"]}
    assert check(
        "definitional_translation",
        "cre\u0301ature",
        lang="de",
        source="KATZE",
        data=json.dumps(data),
    ).satisfied
    phonetic = copy.deepcopy(SOUND)
    phonetic["source_language"] = "de"
    phonetic["source_pronunciations"] = {"Katze": ["a", "b"]}
    assert check(
        "homophonic_translation",
        "chat",
        lang="de",
        source="KATZE",
        data=json.dumps(phonetic),
        max_distance=0,
    ).satisfied


@pytest.mark.parametrize("raw", ["{", "null", '{"value": NaN}', 123])
def test_malformed_json_is_an_explicit_parameter_error(raw: object) -> None:
    with pytest.raises(InvalidParams):
        check("definitional_translation", "x", source="cat", data=raw)


@pytest.mark.parametrize("entry", [[], [""], ["undeclared"]])
def test_pronunciation_entries_cannot_be_empty_or_undeclared(entry: list[str]) -> None:
    data = copy.deepcopy(SOUND)
    data["source_pronunciations"]["cat"] = entry
    with pytest.raises(InvalidParams):
        sound("chat", data=data)
