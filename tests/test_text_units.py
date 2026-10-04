"""`reading.units` publishes the marks the splitters really use (audit B7).

denckring-bench imported `core.text._CLAUSE_BREAK` so its clause guard would follow
the checker. The published marks replace that import only if they are the
splitters' own, so each is held to its splitter over every character in the Basic
Multilingual Plane: a character is in a unit's marks exactly when it splits `a` from
`b` into two units.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

import denckring
from denckring.core.describe import WORD_PROBES
from denckring.core.protocol import Lang
from denckring.core.text import (
    UNIT_ENDS,
    clause_spans,
    line_spans,
    sentence_spans,
    word_spans,
)

SPLITTERS: dict[str, Callable[[str], list[tuple[int, str]]]] = {
    "line": line_spans,
    "clause": clause_spans,
    "sentence": sentence_spans,
}


@pytest.mark.parametrize("unit", sorted(SPLITTERS))
def test_each_published_mark_is_exactly_what_splits_the_unit(unit: str) -> None:
    split = SPLITTERS[unit]
    splitting = {
        chr(code)
        for code in range(0x10000)
        if not 0xD800 <= code <= 0xDFFF and len(split(f"a{chr(code)}b")) == 2
    }
    assert splitting == set(UNIT_ENDS[unit])


def test_every_unit_has_a_splitter() -> None:
    assert set(UNIT_ENDS) == set(SPLITTERS)


def test_describe_publishes_the_units() -> None:
    reading = denckring.describe("anaphora").reading
    assert reading.units == UNIT_ENDS
    assert set(",;:\n") <= set(reading.units["clause"])
    assert "\n" not in reading.units["sentence"]


def test_crlf_is_one_line_break_though_both_characters_are_marks() -> None:
    """The documented caveat of a character set: `\r\n` is two members, one break."""
    assert {"\r", "\n"} <= set(UNIT_ENDS["line"])
    assert len(line_spans("a\r\nb")) == 2


@pytest.mark.parametrize("lang", ["en", "de", "fr"])
def test_the_word_examples_are_what_the_word_counting_rows_count(lang: Lang) -> None:
    """`reading.word_examples` states the apostrophe, hyphen and digit readings
    (audit E6). It is only worth publishing if it is what a row counts: `every_nth_word`
    with `n=1` keeps exactly the words the tokenizer finds, so for each probe the
    published words are the one answer it passes."""
    reading = denckring.describe("every_nth_word", lang=lang).reading
    assert set(reading.word_examples) == set(WORD_PROBES)
    assert reading.word_examples["well-known"] == ["well", "known"]
    assert reading.word_examples["don't"] == ["don't"]
    pack = denckring.get_pack(lang)
    for probe, words in reading.word_examples.items():
        assert [word for _, word in word_spans(probe, pack)] == words
        answer = " ".join(words)
        report = denckring.check("every_nth_word", answer, lang=lang, source=probe, n=1)
        assert report.satisfied and report.metrics["kept"] == len(words)


@pytest.mark.parametrize("lang", ["en", "de", "fr"])
def test_the_published_vowels_are_what_univocalic_reads(lang: Lang) -> None:
    """A letter is in `reading.vowels` exactly when `univocalic` limited to another
    vowel fails it: `y` is a vowel there in French and a consonant in English and German
    (audit A10, E6)."""
    reading = denckring.describe("univocalic", lang=lang).reading
    pack = denckring.get_pack(lang)
    other = {"a": "e"}
    for letter in sorted(set(pack.alphabet()) | set(reading.vowels)):
        allowed = other.get(letter, "a")
        fails = not denckring.check(
            "univocalic", letter, lang=lang, vowel=allowed, fold_diacritics=False
        ).satisfied
        assert fails == (letter in reading.vowels), letter
    assert ("y" in reading.vowels) == (lang == "fr")
