"""One cause, several rows: a parameter compared against folded text.

`fold_diacritics` defaults to true, the text side folds, and the parameter side
did not — so an accented parameter was unsatisfiable and the violation mixed a
folded `found` with an unfolded `expected`. ADR 0035, and the 2026-09-02 MCP
sweep, Finding 1.
"""

import pytest

from denckring import check
from denckring.core.errors import InvalidParams


def test_a_german_umlaut_vowel_is_satisfiable() -> None:
    """`vowel="ä"` reported found "a" against expected "ä" — the seam exactly."""
    assert check("univocalic", "Bäh", lang="de", vowel="ä").satisfied


def test_the_umlaut_vowel_still_rejects_a_foreign_vowel() -> None:
    report = check("univocalic", "Bähe", lang="de", vowel="ä")
    assert not report.satisfied
    assert [v.found for v in report.violations] == ["e"]


def test_an_unfolded_umlaut_vowel_is_distinct_from_its_base() -> None:
    """With folding off, `ä` and `a` are different letters and must stay so."""
    assert not check("univocalic", "Bah", lang="de", vowel="ä", fold_diacritics=False).satisfied
    assert check("univocalic", "Bäh", lang="de", vowel="ä", fold_diacritics=False).satisfied


def test_two_umlaut_vowels_are_satisfiable() -> None:
    assert check("bivocalic", "Bähö", lang="de", vowels="äö").satisfied


def test_an_eszett_consonant_is_refused_by_name() -> None:
    """`consonant="ß"` was unsatisfiable and reported a two-letter `expected`
    against a one-character `got`. D4 refuses it and names the way out."""
    with pytest.raises(InvalidParams) as caught:
        check("monoconsonantal", "Straße", lang="de", consonant="ß")
    assert "fold_diacritics" in str(caught.value)


def test_an_eszett_consonant_works_with_folding_off() -> None:
    assert check(
        "monoconsonantal", "ßeiß", lang="de", consonant="ß", fold_diacritics=False
    ).satisfied


def test_english_is_unchanged_by_the_parameter_fold() -> None:
    """The seam is invisible in ASCII, which is why English never saw it."""
    assert check("univocalic", "Persever, ye perfect men", lang="en", vowel="e").satisfied
    assert check("monoconsonantal", "nine no one", lang="en", consonant="n").satisfied


def test_an_eszett_in_an_acrostic_target_claims_two_units() -> None:
    """`expected` was a two-character "ss" compared against a one-character
    `got` — a "letter" that no unit could ever match. Flattened, ß claims the
    two units its two letters need. ADR 0035, D3.
    """
    assert check("acrostic", "Sonne\nsehr\ntanzt", lang="de", target="ßt", unit="line").satisfied


def test_the_flattened_target_still_reports_a_wrong_letter() -> None:
    report = check("acrostic", "Sonne\nmehr\ntanzt", lang="de", target="ßt", unit="line")
    assert not report.satisfied
    assert [(v.rule, v.found, v.expected) for v in report.violations] == [
        ("wrong_letter", "m", "s")
    ]


def test_telestich_inherits_the_flattened_target() -> None:
    """`telestich` subclasses `Acrostic` and reads the last letter of each unit."""
    assert check("telestich", "das\nes\nvot", lang="de", target="ßt", unit="line").satisfied


def test_a_double_acrostic_target_flattens_on_both_edges() -> None:
    """Both targets carry a `ß`, deliberately. An ASCII `last` passes unchanged
    under the unflattened code, so it could not show the second edge was fixed:
    with `last="ßt"` the pre-fix expression yields the two units `["ß", "t"]`
    and the third line becomes an `extra_line`.
    """
    assert check(
        "double_acrostic",
        "sonnes\nsehrs\ntanzt",
        lang="de",
        first="ßt",
        last="ßt",
    ).satisfied


def test_a_german_lipogram_forbidding_an_umlaut_is_satisfiable() -> None:
    """`forbidden="ä"` reported no hits because the text side folds `ä` to `a`
    and the parameter never did — the inverted verdict in ADR 0035's "Known
    remaining": the text plainly contains the letter and the row said it did
    not.
    """
    assert check("lipogram", "Wolken ziehen über den Fluss", lang="de", forbidden="ä").satisfied


def test_the_umlaut_lipogram_still_rejects_the_forbidden_letter() -> None:
    report = check("lipogram", "Wolken ziehen über den Fluss und Wälder", lang="de", forbidden="ä")
    assert not report.satisfied
    assert any(v.rule == "forbidden_letter" for v in report.violations)


def test_a_german_pangrammatic_lipogram_forbidding_an_umlaut_is_satisfiable() -> None:
    assert check(
        "pangrammatic_lipogram", "bcdefghijklmnopqrstuvwxyz", lang="de", forbidden="ä"
    ).satisfied


def test_the_umlaut_pangrammatic_lipogram_still_rejects_the_forbidden_letter() -> None:
    report = check("pangrammatic_lipogram", "abcdefghijklmnopqrstuvwxyz", lang="de", forbidden="ä")
    assert not report.satisfied
    assert any(v.rule == "forbidden_letter" for v in report.violations)


def test_a_german_tautogram_on_an_umlaut_initial_is_satisfiable() -> None:
    assert check("tautogram", "Ärger Ähnlich Ärmel", lang="de", initial="ä").satisfied


def test_the_umlaut_tautogram_still_rejects_a_foreign_initial() -> None:
    report = check("tautogram", "Ärger Berg Ähnlich", lang="de", initial="ä")
    assert not report.satisfied
    assert [v.found for v in report.violations] == ["Berg"]


def test_a_french_homoteleuton_on_an_accented_final_is_satisfiable() -> None:
    """`final="é"` reported `wrong_final` on both words, because the text side
    folds `é` to `e` and the parameter never did."""
    assert check("homoteleuton", "café passé", lang="fr", final="é").satisfied


def test_the_accented_homoteleuton_still_rejects_a_foreign_final() -> None:
    report = check("homoteleuton", "café chat", lang="fr", final="é")
    assert not report.satisfied
    assert [v.found for v in report.violations] == ["chat"]


def test_an_abecedarian_umlaut_start_is_satisfiable() -> None:
    text = "Ärger folgt\nBerg steht\nCurry duftet"
    assert check("abecedarian", text, lang="de", start="ä").satisfied


def test_an_abecedarian_umlaut_start_is_not_vacuously_satisfied() -> None:
    """`start="ä"` used to fall back to index 0 whenever the raw letter was not
    in the flat alphabet, coincidentally agreeing with the correct answer for
    `ä` (index 0) and disagreeing for any other umlaut. `ö` folds to `o`,
    index 14 — the unfixed code silently checked against `start="a"` instead
    and reported every line wrong.
    """
    text = "Ozean ruht\nParadies wacht\nQuelle blinkt"
    assert check("abecedarian", text, lang="de", start="ö").satisfied


def test_an_abecedarian_umlaut_start_is_refused_with_folding_off() -> None:
    """With folding off, `ä` is not a letter of the flat `de` alphabet at all —
    a decision this row's own alphabet forces, named rather than silently
    defaulted."""
    with pytest.raises(InvalidParams) as caught:
        check(
            "abecedarian",
            "Ärger folgt\nBerg steht",
            lang="de",
            start="ä",
            fold_diacritics=False,
        )
    assert "alphabet" in str(caught.value)


def test_a_serial_lipogram_umlaut_start_is_accepted_under_folding() -> None:
    """`serial_lipogram` refused `start="ä"` outright, even with folding on —
    stricter than the fold this row's own comparison already performs on the
    text side. `ä` folds to `a`, so this is `start="a"` under another spelling
    and must be accepted the same way — not full 26-part satisfaction, just
    that the refusal is gone.
    """
    report = check("serial_lipogram", "bcdefghijklmnopqrstuvwxyz", lang="de", start="ä")
    assert not any(v.rule == "forbidden_letter" for v in report.violations)


def test_a_serial_lipogram_umlaut_start_is_still_refused_with_folding_off() -> None:
    with pytest.raises(InvalidParams) as caught:
        check(
            "serial_lipogram",
            "Bcdfghijk\nLmnopqrst",
            lang="de",
            start="ä",
            fold_diacritics=False,
        )
    assert "alphabet" in str(caught.value)
