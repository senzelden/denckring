"""`is_word` is not fold-aware, and `kangaroo_word` folded before asking it.

French keeps accents in its word list on purpose (ADR 0009) — `is_word` casefolds
internally but never strips diacritics — so a `synonym` folded to `ecole` could
never match the table's `école`. `synonym: "école"` failed `not_a_word` under
`fold_diacritics: true`, the default, for every accented French synonym: a large
share of the vocabulary. Every other `is_word` caller in this codebase (`paragram`,
`word_ladder`, `semordnilap`) already checks membership on the word as written and
folds only for its own scattering/order comparison; `kangaroo_word` is the one row
that folded first. ADR 0036.
"""

import pytest

from denckring import check

pytest.importorskip("denckring_fr_data")


def test_an_accented_french_synonym_is_recognised_under_default_folding() -> None:
    """`écologie` scatters `école`'s letters in order and is itself a real,
    distinct word — a natural pair, not a constructed one."""
    assert check("kangaroo_word", "écologie", lang="fr", synonym="école").satisfied


def test_the_folded_comparison_still_catches_a_non_word() -> None:
    report = check("kangaroo_word", "écologie", lang="fr", synonym="ecoel")
    assert not report.satisfied
    assert report.violations[0].rule == "not_a_word"


def test_the_order_check_still_uses_the_folded_forms() -> None:
    """Distinctness and ordering are unaffected by this fix — only which form
    reaches `is_word` changes."""
    report = check("kangaroo_word", "écologie", lang="fr", synonym="logique")
    assert not report.satisfied
    assert report.violations[0].rule == "synonym_not_in_order"
