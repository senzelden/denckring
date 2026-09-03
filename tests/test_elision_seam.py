"""A word glued to a proclitic by elision was invisible to the noun index.

The tokeniser keeps an apostrophe-bearing token whole — `l'île`, `d'espoir` —
because 94 real French words carry an internal apostrophe of their own
(`aujourd'hui`) and splitting every apostrophe unconditionally would misread
those. No noun does, though, so a leading `proclitic'` before a noun is
always an elision boundary, never part of the noun itself. `noun_index`
looked the whole token up and never found it, so `l'îlot` — the correct S+7
of `l'île` — failed as `changed_a_non_noun`, while retyping the source
unchanged passed under `ambiguous_nouns="strict"`, which exists to catch
exactly that. Bare `île` worked, so one word gave two verdicts depending on
a preceding `l'`. Both `s_plus_7` and `n_plus_7` share the seam; `s_plus_7`
delegates to `n_plus_7`'s `displace`/`displacement_report` entirely.

Chapter 6's trap 1 again: a lookup normalising differently from the way its
table is keyed. The prosody path already learned it
(`denckring_fr_data._table_entry`: try the token whole, then fall back past
the last apostrophe). The lexicon path never did, until now.
"""

import pytest

from denckring import apply, check

pytest.importorskip("denckring_fr_data")


def test_the_correct_displacement_of_an_elided_noun_is_satisfied() -> None:
    """`île` (index 44740) + 3 is `îlot` — verified against the shipped
    lexicon, not hand-computed. The `l'` proclitic is unchanged."""
    assert check(
        "s_plus_7", "l'îlot", lang="fr", source="l'île", offset=3, ambiguous_nouns="strict"
    ).satisfied


def test_retyping_the_elided_source_unchanged_is_flagged_under_strict() -> None:
    """`île` is a listed noun left alone — `strict` exists for precisely
    this, and the proclitic must not hide it."""
    report = check(
        "s_plus_7", "l'île", lang="fr", source="l'île", offset=3, ambiguous_nouns="strict"
    )
    assert not report.satisfied
    assert report.violations[0].rule == "ambiguous_noun_unchanged"


def test_a_wrong_displacement_of_an_elided_noun_is_a_violation() -> None:
    report = check(
        "s_plus_7", "l'îlotier", lang="fr", source="l'île", offset=3, ambiguous_nouns="strict"
    )
    assert not report.satisfied
    assert report.violations[0].rule == "wrong_displacement"
    assert report.violations[0].expected == "l'îlot"


def test_a_changed_proclitic_is_its_own_violation() -> None:
    """The proclitic is not a noun and must never change; conflating this
    with `changed_a_non_noun` would name the wrong cause, the same mistake
    the sweep found in the unfixed row."""
    report = check(
        "s_plus_7", "d'îlot", lang="fr", source="l'île", offset=3, ambiguous_nouns="strict"
    )
    assert not report.satisfied
    assert report.violations[0].rule == "changed_proclitic"


def test_de_espoir_displaces_by_three() -> None:
    """`espoir` (index 15417) + 3 is `esprits` — a second proclitic, `d'`."""
    assert check(
        "s_plus_7", "d'esprits", lang="fr", source="d'espoir", offset=3, ambiguous_nouns="strict"
    ).satisfied


def test_the_typographic_apostrophe_is_recognised_too() -> None:
    """The typographic apostrophe (U+2019) behaves like the ASCII `'`."""
    assert check(
        "s_plus_7",
        "l\u2019îlot",
        lang="fr",
        source="l\u2019île",
        offset=3,
        ambiguous_nouns="strict",
    ).satisfied


def test_apply_produces_the_elided_displacement_and_it_round_trips() -> None:
    """The generator, not just the checker: `apply` must keep the proclitic
    and displace only the noun, and its own output must satisfy the fix
    above."""
    produced = apply("s_plus_7", "l'île paraît très loin", lang="fr", offset=3)
    assert produced == "l'îlot paraît très loin"
    assert check(
        "s_plus_7", produced, lang="fr", source="l'île paraît très loin", offset=3
    ).satisfied


def test_n_plus_7_shares_the_fix_through_the_default_offset() -> None:
    """`ami` (index 1291) + 7 is `amidon` — `n_plus_7`'s default offset,
    proving the shared code path rather than re-deriving it for `s_plus_7`
    alone."""
    assert check("n_plus_7", "l'amidon", lang="fr", source="l'ami").satisfied


def test_a_consonant_initial_target_keeps_the_written_proclitic_literally() -> None:
    """Known, honest limitation, pinned rather than hidden: choosing between
    `l'`/`le`/`la` for a displaced noun needs the noun's grammatical gender,
    which this pack's noun list does not carry. The proclitic is preserved
    exactly as written rather than re-elided, so a displacement landing on a
    consonant-initial noun produces a string most French speakers would
    correct by hand. `aïoli` (index 3284) + 1 is `b` — the shipped lexicon's
    own alphabetic-order artefact, not a constructed example.
    """
    produced = apply("s_plus_7", "l'aïoli", lang="fr", offset=1)
    assert produced == "l'b"
    assert check("s_plus_7", produced, lang="fr", source="l'aïoli", offset=1).satisfied


def test_dictionary_folds_are_unchanged_when_no_elision_is_present() -> None:
    """The ordinary, non-elided path — untouched by this fix."""
    assert check("s_plus_7", "chatière", lang="fr", source="chat", offset=3).satisfied
