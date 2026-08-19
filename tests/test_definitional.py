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


def _expanded(text: str, senses: dict[str, int] | None = None) -> str:
    """`text` with every word the pack resolves replaced by one of its glosses — one
    round of definitional literature, performed rather than checked.

    This is the generator the row deliberately does not ship (ADR 0002), written here so
    the fixtures below are genuine expansions rather than texts hand-assembled to suit
    the checker. `senses` picks a sense per word; anything unnamed takes the first, and a
    word the pack cannot resolve is left standing, which is what the procedure does with
    function words.
    """
    out = []
    for token in _pack.tokenize(text):
        glosses = _pack.glosses(token)
        if not glosses:
            out.append(token)
            continue
        index = (senses or {}).get(token, 0)
        out.append(glosses[min(index, len(glosses) - 1)])
    return " ".join(out)


def test_two_iterations_are_accepted_and_counted() -> None:
    """The row's whole point: a text no single round reaches, but two rounds do. Both
    rounds are performed by `_expanded` above, so the text is a real expansion of a real
    expansion — 46 tokens after one round and 421 after two — and the checker has to
    discover the depth rather than being told it."""
    once = _expanded(SOURCE)
    twice = _expanded(once)

    report = check("definitional_literature", twice, source=SOURCE)
    assert report.satisfied is True
    assert report.metrics["iterations"] == 2.0

    # The intermediate text is a one-round expansion, and one round also counts.
    assert check("definitional_literature", once, source=SOURCE).metrics["iterations"] == 1.0


def test_the_two_definitional_rows_are_not_the_same_row() -> None:
    """A two-round text is not a one-round text. `definitional_expansion` asks for the
    source's own glosses and does not find them in a text where they have themselves been
    expanded; `definitional_literature` is the row that keeps looking."""
    twice = _expanded(_expanded(SOURCE))
    assert check("definitional_expansion", twice, source=SOURCE).satisfied is False
    assert check("definitional_literature", twice, source=SOURCE).satisfied is True


def test_the_third_round_is_inside_the_cap() -> None:
    """`MAX_ROUNDS` is 3, and 3 is reachable rather than merely permitted — the edge is
    worth pinning because the cap is the one number in this row chosen by measurement
    (0.15 s here against 18 s for a fourth round), and a cap that quietly excluded its own
    top round would be a different bound than the docstring claims."""
    thrice = _expanded(_expanded(_expanded(SOURCE)))
    report = check("definitional_literature", thrice, source=SOURCE)
    assert report.satisfied is True
    assert report.metrics["iterations"] == 3.0


def test_a_text_no_number_of_iterations_reaches_is_rejected() -> None:
    """The source retyped unchanged is reachable by zero rounds, and zero rounds is not
    what the procedure asks for. `iterations` reports 0.0 to say no round count in range
    reproduces this text — not that the text is a zero-round expansion."""
    report = check("definitional_literature", "the key", source="the key")
    assert report.satisfied is False
    assert report.metrics["iterations"] == 0.0
    assert any(v.rule == "not_expanded" for v in report.violations)


def test_a_source_with_nothing_to_expand_claims_no_iterations() -> None:
    """`he went` resolves to nothing at all, so no round was searched and none can be
    claimed. The report is vacuously satisfied — `_report`'s contract for `total == 0` —
    but `iterations` stays 0.0 rather than asserting a depth, and `estimated_words`
    discloses how many words went unchecked."""
    report = check("definitional_literature", "he went", source="he went")
    assert report.metrics["iterations"] == 0.0
    assert report.metrics["estimated_words"] >= 1.0
