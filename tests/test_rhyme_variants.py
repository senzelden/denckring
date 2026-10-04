"""A pair kept apart fails only when every reading rhymes; German rhymes its headword (ADR 0057).

Until 0.4.0 one test served both directions of a scheme: two endings rhymed when any
pair of their keys matched. That is right for a pair the scheme wants to rhyme, and
wrong for a pair it wants kept apart. `on` is `AA1 N` and `AO1 N` in CMUdict, so a
sonnet ending one line on `gone` and another on `on` failed `unwanted_rhyme` though
the writer may have meant the reading that keeps them apart (audit A8).

German stress and rhyme read every transcription Wiktionary lists for a word, and the
list carries inflected forms: `du` rhymed with `mich` through *dich*, and scanned as
two syllables through *deiner*.
"""

from __future__ import annotations

import pytest

from denckring import check, describe
from denckring.core.base import RhymeParams
from denckring.core.prosody import may_rhyme, must_rhyme
from denckring.core.protocol import Lang
from denckring.core.registry import all_procedures, get
from denckring.lang import get_pack

pytest.importorskip("denckring_en_data")

#: The audit's probe words: `on` has two readings, `gone` and `dawn` one each.
GONE_ON = "the sun is gone\nthe light went on"
GONE_DAWN = "the sun is gone\nand comes the dawn"


def _keys(*keys: str) -> frozenset[str]:
    return frozenset(keys)


def test_a_wanted_rhyme_needs_one_matching_pair_of_readings() -> None:
    assert may_rhyme(_keys("AA1 N", "AO1 N"), _keys("AO1 N"))
    assert not may_rhyme(_keys("AA1 N"), _keys("AO1 N"))
    assert not may_rhyme(_keys(), _keys("AO1 N"))


def test_an_unwanted_rhyme_needs_every_reader_to_rhyme_the_pair() -> None:
    """Every pairing matches, or the two have the same keys (ADR 0057)."""
    assert must_rhyme(_keys("AO1 N"), _keys("AO1 N"))
    assert must_rhyme(_keys("AA1 N", "AO1 N"), _keys("AA1 N", "AO1 N"))
    assert not must_rhyme(_keys("AA1 N", "AO1 N"), _keys("AO1 N"))
    assert not must_rhyme(_keys("AA1 N", "AO1 N"), _keys("AA1 N", "AO1 N", "OW1 N"))
    # An ending the dictionary lacks rhymes with nothing, as it always has.
    assert not must_rhyme(_keys(), _keys())
    assert not must_rhyme(_keys(), _keys("AO1 N"))


def test_the_audit_probe_keeps_gone_and_on_apart() -> None:
    """`on` may be `AA1 N`, which `gone` is not, so `AB` holds."""
    report = check("rhyme_scheme", GONE_ON, scheme="AB")
    assert report.satisfied, report.violations
    on = next(e for e in report.evidence if e.subject == "on")
    assert on.basis == "ambiguous"


def test_a_pair_with_one_reading_each_still_fails() -> None:
    report = check("rhyme_scheme", GONE_DAWN, scheme="AB")
    assert [v.rule for v in report.violations] == ["unwanted_rhyme"]


def test_the_wanted_side_is_unchanged() -> None:
    assert check("rhyme_scheme", GONE_ON, scheme="AA").satisfied
    assert check("rhyme_scheme", GONE_DAWN, scheme="AA").satisfied


def test_blank_verse_reads_an_unwanted_rhyme_the_same_way() -> None:
    """Blank verse fails any rhyming pair, so it shares the reading, not its own."""
    rules = [v.rule for v in check("blank_verse", GONE_ON).violations]
    assert "unwanted_rhyme" not in rules
    rules = [v.rule for v in check("blank_verse", GONE_DAWN).violations]
    assert "unwanted_rhyme" in rules


def test_two_words_with_the_same_keys_rhyme_for_every_reader() -> None:
    """`fog` and `bog` are each `AA1 G` or `AO1 G`. A speaker who says one way says
    both, so no reader keeps them apart, though reading each word in a different
    accent would. The same holds for a word against itself."""
    for text in ("in the fog\nin the bog", "the wind\nthe wind"):
        report = check("rhyme_scheme", text, scheme="AB")
        assert [v.rule for v in report.violations] == ["unwanted_rhyme"], text
    rules = [v.rule for v in check("blank_verse", "in the fog\nin the bog").violations]
    assert "unwanted_rhyme" in rules


def test_each_pair_is_decided_on_its_own() -> None:
    """The cost ADR 0057 admits: `on` keeps `don` apart only as `AO1 N` and `gone`
    apart only as `AA1 N`. No one reading of `on` does both, and `ABC` still holds."""
    report = check("rhyme_scheme", "a don\nlight on\nall gone", scheme="ABC")
    assert report.satisfied, report.violations


def test_du_does_not_rhyme_with_mich() -> None:
    """*dich*, filed under `du`, gave `du` the key `ɪ ç` (R-U9b)."""
    pytest.importorskip("denckring_de_wiktionary")
    report = check("rhyme_scheme", "ich sage du\ndu siehst mich", scheme="AA", lang="de")
    assert [v.rule for v in report.violations] == ["does_not_rhyme"]
    assert check("rhyme_scheme", "ich sage du\ndu siehst mich", scheme="AB", lang="de").satisfied


def test_du_takes_its_own_stress_and_rhyme() -> None:
    """`du` is `duː`: one syllable, free stress, one key. Not *deiner*'s `ˈdaɪ̯nɐ`."""
    pytest.importorskip("denckring_de_wiktionary")
    pack = get_pack("de")
    assert pack.stress_patterns("du") == ["?"]
    assert pack.rhyme_keys("du") == ["uː"]


def test_rhyme_is_described_on_exactly_the_rows_that_judge_one() -> None:
    for pid in all_procedures():
        rhymes = issubclass(get(pid).params_model(), RhymeParams)
        assert (describe(pid).reading.rhyme is not None) == rhymes, pid


def test_the_english_description_holds_secondary_stress_out() -> None:
    """`describe` says `someday` does not rhyme with `day`; the checker agrees."""
    rhyme = describe("rhyme_scheme").reading.rhyme
    assert rhyme is not None
    assert "'someday'" in rhyme
    assert "every reading" in rhyme
    assert not check("rhyme_scheme", "we leave someday\nwe leave today", scheme="AA").satisfied


@pytest.mark.parametrize("lang", ["de", "fr"])
def test_the_single_key_languages_say_so(lang: Lang) -> None:
    """German and French offer one key per word, as their description says."""
    pytest.importorskip({"de": "denckring_de_wiktionary", "fr": "denckring_fr_data"}[lang])
    rhyme = describe("rhyme_scheme", lang=lang).reading.rhyme
    assert rhyme is not None
    assert "first transcription only" in rhyme or "one transcription" in rhyme
    word = {"de": "du", "fr": "rose"}[lang]
    assert len(get_pack(lang).rhyme_keys(word)) == 1
