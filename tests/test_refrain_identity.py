"""A refrain is the same line returning, whatever punctuation its position wants.

`form_report`, `rondeau` and `pantoum` compared repeated lines raw, so a refrain
that returned with a different stop was read as broken. That is not an edge case:
it is how the fixed forms are printed. Passerat's villanelle (1606) closes its
refrain `Tourterelle:`, then `Tourterelle.`, then `Tourterelle,` as the syntax
around it changes, and Ranchin's triolet returns `du mois de mai` once bare and
once as `de mai !`.

Found by external evidence, which is the whole argument for keeping any: four
canonical texts in research batch 3 failed on it, and none of the 34 constructed
cases in the refrain-bearing rows could — every one of them repeats its refrain
byte-for-byte, because the same author typed both copies.
"""

from __future__ import annotations

from denckring import check

#: Ranchin's triolet, as printed. Lines 1 and 4 are the same line; so are 2 and 8.
#: Only their stops differ.
RANCHIN = """Le premier jour du mois de mai
Fut le plus heureux de ma vie :
Le beau dessein que je formai,
Le premier jour du mois de mai !
Je vous vis et je vous aimai.
Si ce dessein vous plut, Sylvie,
Le premier jour du mois de mai
Fut le plus heureux de ma vie."""


def test_a_canonical_triolet_is_not_broken_by_its_own_punctuation() -> None:
    report = check("triolet", RANCHIN, lang="fr", unknown_rhyme="free")
    assert report.satisfied, [str(v) for v in report.violations]


def test_a_refrain_differing_in_a_word_still_fails() -> None:
    """The guard against over-permissiveness. Without it this fix would turn every
    refrain check into a formality and nothing in the suite would say so."""
    broken = RANCHIN.replace("Le premier jour du mois de mai !", "Le dernier jour du mois de mai !")
    report = check("triolet", broken, lang="fr", unknown_rhyme="free")
    assert not report.satisfied
    assert any(v.rule == "broken_refrain" for v in report.violations)
