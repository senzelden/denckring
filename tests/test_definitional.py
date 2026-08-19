"""Replacing a word with what the dictionary says it means.

Every gloss below is read live from the pack rather than hand-typed, per Controller
ruling R4: the brief's own illustration (`"feline mammal usually having thick soft
fur"`) was written from memory and is not OEWN's actual text for `cat`.
"""

from denckring import check
from denckring.lang import get_pack

SOURCE = "the cat sat"

_pack = get_pack("en")


def test_a_word_replaced_by_one_of_its_definitions_is_accepted() -> None:
    """`sat` also resolves — to the Saturday-abbreviation sense, nothing to do with
    sitting, this row's own finding while building its fixtures and the same shape of
    collision as `glosses("aides")` returning the Hades sense — so both `cat` and `sat`
    need expanding here. The brief's own illustration left `sat` untouched, on the
    unstated assumption that an irregular verb form resolves to nothing the way
    `went` does in the third test below; that assumption does not survive being run
    against the real pack, so both words are expanded rather than just the one the
    brief named.
    """
    cat_gloss = _pack.glosses("cat")[0]
    sat_gloss = _pack.glosses("sat")[0]
    text = f"the {cat_gloss} {sat_gloss}"
    assert check("definitional_expansion", text, source=SOURCE).satisfied is True


def test_a_word_left_unexpanded_is_reported() -> None:
    report = check("definitional_expansion", SOURCE, source=SOURCE)
    assert report.satisfied is False
    assert any(v.rule == "not_expanded" for v in report.violations)


def test_words_the_lexicon_cannot_resolve_are_disclosed_not_failed() -> None:
    """`went` needs irregular morphology. A report drawn from partial knowledge
    must say so rather than quietly scoring over fewer words."""
    report = check("definitional_expansion", "he went", source="he went")
    assert report.metrics["estimated_words"] >= 1.0


def test_each_occurrence_needs_its_own_gloss_r6() -> None:
    """Controller ruling R6: the catalogue definition says each substantive word is
    replaced *once*, not that it is replaced somewhere. `cat` appears twice in the
    source below; expanding only the first and leaving the second bare must not pass,
    even though `cat`'s gloss is present in the text — it is present only once, and
    one embedded definition cannot stand in for two occurrences.
    """
    source = "the cat and the cat"
    gloss = _pack.glosses("cat")[0]
    half_expanded = check("definitional_expansion", f"the {gloss} and the cat", source=source)
    assert half_expanded.satisfied is False
    assert any(v.rule == "not_expanded" for v in half_expanded.violations)

    fully_expanded = check("definitional_expansion", f"the {gloss} and the {gloss}", source=source)
    assert fully_expanded.satisfied is True
