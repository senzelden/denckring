"""A line meets its syllable count when some reading of its words does (ADR 0054).

Until 0.4.0 the line-count rows summed each word's *first* CMUdict pronunciation,
while metre and rhyme tried every one (ADR 0014). `every family sings` failed a
haiku's five as seven syllables, with `estimated_words` at zero, when the
dictionary lists the two-syllable `every` and `family` the writer meant. The rows
now read every listed form, and evidence marks a word it read more than one way
`ambiguous`.
"""

from __future__ import annotations

import pytest

from denckring import check, describe
from denckring.lang import get_pack
from denckring.lang.base import SYLLABLES_HEURISTIC, BasePack
from denckring.lang.de import GermanPack
from denckring.lang.en import EnglishPack
from denckring.lang.fr import FrenchPack

pytest.importorskip("denckring_en_data")

#: The audit's case (A3): 7 syllables read first-form, 5 as spoken.
EVERY_FAMILY = "every family sings\nin the quiet evening rain\nsilence falls on us"

#: Lines for the pack invariants: English and German words with and without listed
#: variants, and French mute e before a vowel and before a consonant.
LINES = {
    "en": ["every family sings", "our fire burns an hour", "the owl awakes"],
    "de": ["du sehen gehen Eis", "der Wind zieht durch das Land"],
    "fr": ["une femme aimable entre", "la belle rose tombe"],
}
#: Every installed pack and the three built-in defaults, where they count syllables
#: at all (French's built-in pack does not).
PACKS: list[BasePack] = [
    pack
    for pack in (*(get_pack(lang) for lang in LINES), EnglishPack(), GermanPack(), FrenchPack())
    if isinstance(pack, BasePack) and SYLLABLES_HEURISTIC in pack.capabilities
]


def _pack(lang: str) -> BasePack:
    """The installed pack, typed as the class that carries the new methods."""
    pack = get_pack(lang)
    assert isinstance(pack, BasePack)
    return pack


@pytest.mark.parametrize("pack", PACKS, ids=lambda p: type(p).__name__)
def test_the_first_reading_is_always_one_of_the_readings(pack: BasePack) -> None:
    """`syllable_count` is the first form; `syllable_counts` must contain it and agree
    on whether it was looked up, or the two surfaces describe different words."""
    for line in LINES[pack.lang]:
        for word in pack.tokenize(line):
            count, exact = pack.syllable_count(word)
            counts, counts_exact = pack.syllable_counts(word)
            assert count in counts, (word, count, counts)
            assert exact == counts_exact, word
        total, estimated = pack.line_syllables(line)
        totals, totals_estimated = pack.line_syllable_counts(line)
        assert total in totals, (line, total, totals)
        assert estimated == totals_estimated, line


@pytest.mark.parametrize("pack", PACKS, ids=lambda p: type(p).__name__)
def test_a_pack_that_counts_its_own_lines_reads_its_own_variants_too(pack: BasePack) -> None:
    """French overrides `line_syllables` because it counts a line, not its words
    (ADR 0034). Inheriting `line_syllable_counts` would sum the words again and
    undo that, and the line rows read the new method."""
    cls = type(pack)
    if cls.line_syllables is not BasePack.line_syllables:
        assert cls.line_syllable_counts is not BasePack.line_syllable_counts, cls.__name__
        for line in LINES[pack.lang]:
            total, estimated = pack.line_syllables(line)
            assert pack.line_syllable_counts(line) == (frozenset({total}), estimated)


def test_english_reads_every_listed_pronunciation() -> None:
    pack = _pack("en")
    assert pack.syllable_count("every") == (3, True)
    assert pack.syllable_counts("every") == (frozenset({2, 3}), True)
    assert pack.line_syllable_counts("every family") == (frozenset({4, 5, 6}), 0)


def test_a_word_read_through_its_stem_takes_every_form_of_the_stem() -> None:
    """`amblings` is not in CMUdict; `ambling` is, as three syllables and as two."""
    pack = _pack("en")
    assert pack.syllable_count("amblings") == (3, False)
    assert pack.syllable_counts("amblings") == (frozenset({2, 3}), False)


def test_german_keeps_its_first_transcription() -> None:
    """Not a gap: German Wiktionary's list for a word carries its inflected forms'
    transcriptions too. `du` lists eight, among them `ˈdaɪ̯nɐ` (*deiner*), so reading
    every form would count `du` as two syllables (ADR 0054)."""
    pack = _pack("de")
    assert pack.syllable_counts("du") == (frozenset({1}), True)


def test_the_audit_haiku_passes_and_says_it_rested_on_a_variant() -> None:
    report = check("haiku", EVERY_FAMILY)
    assert report.satisfied, report.violations
    assert not report.estimated
    every = next(e for e in report.evidence if e.subject == "every")
    assert every.basis == "ambiguous"
    assert every.value == "2 or 3 syllables"
    rain = next(e for e in report.evidence if e.subject == "rain")
    assert rain.basis == "dictionary"
    assert rain.value == "1 syllables"


def test_a_line_no_reading_fits_names_every_reading() -> None:
    report = check("syllable_count", "every family", pattern=[7])
    assert [v.found for v in report.violations] == ["4, 5 or 6 syllables"]
    single = check("syllable_count", "the cat", pattern=[7])
    assert [v.found for v in single.violations] == ["2 syllables"]


@pytest.mark.parametrize("procedure", ["haiku", "senryu"])
def test_the_fixed_forms_inherit_it(procedure: str) -> None:
    assert check(procedure, EVERY_FAMILY).satisfied


def test_renga_reads_variants() -> None:
    hokku = "every family\ncat dog mat sat run sky tree\ncat dog mat sat run"
    wakiku = "cat dog mat sat run sky tree\ncat dog mat sat run sky tree"
    report = check("renga", f"{hokku}\n\n{wakiku}")
    assert report.satisfied, report.violations


def test_haibun_classifies_a_variant_haiku_as_verse() -> None:
    prose = "The road turned north and the rain did not let up until evening."
    haiku = "every family\ncat dog mat sat run sky tree\ncat dog mat sat run"
    assert check("haibun", f"{prose}\n\n{haiku}").satisfied


def test_monosyllabic_prose_accepts_a_word_with_a_one_syllable_reading() -> None:
    """`fire` is F AY1 ER0 first and F AY1 R second."""
    assert check("monosyllabic_prose", "the fire burns").satisfied
    assert not check("monosyllabic_prose", "the evening burns").satisfied


def test_double_dactyl_accepts_a_six_syllable_reading() -> None:
    """`paradoxically` is five syllables first and six second."""
    text = (
        "murmuring beautiful\nbeautiful murmuring\nwonderful carefully\ncarefully song\n"
        "paradoxically\nmurmuring beautiful\nbeautiful murmuring\nwonderful stone"
    )
    rules = {v.rule for v in check("double_dactyl", text).violations}
    assert "no_double_dactylic_word" not in rules


def test_arca_sets_a_phrase_at_any_length_a_reading_gives() -> None:
    """`every family` is 4, 5 or 6 syllables, and the tablet sets only 4."""
    pinakes = '{"syntagmata": {"1": {"4": ["5 3 1 3"]}}}'
    report = check("arca_musarithmica", "5 3 1 3", source="every family", pinakes=pinakes)
    assert report.satisfied, report.violations
    wrong = check("arca_musarithmica", "1 1 1 1", source="every family", pinakes=pinakes)
    assert [v.expected for v in wrong.violations] == ["one of the 1 patterns for 4 syllables"]


def test_metre_evidence_marks_a_word_it_could_read_two_ways() -> None:
    report = check("iambic_pentameter", "and every flower opens to the sun")
    every = next(e for e in report.evidence if e.subject == "every")
    assert every.basis == "ambiguous"
    sun = next(e for e in report.evidence if e.subject == "sun")
    assert sun.basis == "dictionary"


def test_metre_evidence_names_the_form_the_scan_fitted() -> None:
    """The line scans only with `every` as two syllables, `10`; its first form is `100`.
    Evidence naming `100` would describe a reading the verdict did not use (U6 review M3)."""
    report = check("iambic_pentameter", "and every flower opens to the sun")
    assert report.satisfied
    assert next(e for e in report.evidence if e.subject == "every").value == "10"


def test_metre_evidence_on_a_failed_line_names_every_form_tried() -> None:
    report = check("iambic_pentameter", "every every every every every")
    assert not report.satisfied
    values = {e.value for e in report.evidence if e.subject == "every"}
    assert values == {"100/10"}, values


def test_rhyme_evidence_marks_a_word_with_two_keys() -> None:
    report = check("rhyme_scheme", "a heavy log\na misty bog", scheme="AA")
    basis = {e.subject: e.basis for e in report.evidence}
    assert basis == {"log": "dictionary", "bog": "ambiguous"}
    assert not report.estimated


@pytest.mark.parametrize("pid", ["definitional_expansion", "definitional_literature"])
def test_a_row_that_can_leave_words_unjudged_does_not_read_exact(pid: str) -> None:
    """U3 review M3: `describe` said `exact` for rows whose reports can be
    `estimated`. Two published surfaces disagreed on the same row."""
    assert describe(pid).reading.determinacy == "heuristic"


def test_a_pack_that_predates_the_variant_methods_answers_with_its_one_count() -> None:
    """`syllable_counts` and `line_syllable_counts` are not on the `LanguagePack`
    protocol, which a third-party pack satisfies by structure, so a pack without
    them must keep working with the reading it had."""
    from denckring.procedures.syllable_count import line_syllable_counts, word_syllable_counts

    class Older:
        def syllable_count(self, word: str) -> tuple[int, bool]:
            return 3, True

        def line_syllables(self, line: str) -> tuple[int, int]:
            return 9, 1

    pack = Older()
    assert word_syllable_counts("every", pack) == (frozenset({3}), True)  # type: ignore[arg-type]
    assert line_syllable_counts("a\nb", pack) == [  # type: ignore[arg-type]
        (0, frozenset({9}), 1),
        (2, frozenset({9}), 1),
    ]
