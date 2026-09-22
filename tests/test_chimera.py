"""Chimera: one text's frame, refilled from three donors.

Every text here is real English rather than generated letters, for the reason
`test_homosyntaxism.py` gives: the verdict comes from a tagger and a tagger has
nothing to say about `zzzz`.

The four rulings in the module docstring each have a test that fails if the
ruling is reversed, rather than only a passing case — reversing a ruling should
have to change a test that says what the ruling was.
"""

from typing import Any

import pytest

from denckring import apply, check, produce
from denckring.core.errors import DegenerateOutput, InvalidParams, NoCandidateWord
from denckring.core.protocol import Report
from denckring.lang import get_pack
from denckring.procedures.chimera import donor_words, recase

FRAME = "The quick boy opened the door."
NOUNS = "The cold wind carried the letter."
VERBS = "The warm girl watched the river."
ADJECTIVES = "The small child painted the table."

#: Annotated `Any` rather than `str`, and the reason is `lang`: `check` and
#: `apply` take it as a keyword typed `Literal["en", "de", "fr"]`, so
#: `mypy --strict` reads `**DONORS` of type `dict[str, str]` as a call that
#: might bind a plain `str` to it — the same collision `ApplyParams` warns
#: about for a field of that name, met from the calling side.
DONORS: dict[str, Any] = {
    "nouns_from": NOUNS,
    "verbs_from": VERBS,
    "adjectives_from": ADJECTIVES,
}


def _check(text: str, **overrides: str) -> Report:
    return check("chimera", text, source=FRAME, **{**DONORS, **overrides})


def test_a_frame_refilled_from_three_donors_is_satisfied() -> None:
    report = _check("The small wind watched the letter.")
    assert report.satisfied
    assert report.metrics["tokens"] == 6.0


def test_a_content_word_from_no_donor_is_a_violation() -> None:
    report = _check("The small mountain watched the letter.")
    assert not report.satisfied
    violation = report.violations[0]
    assert violation.rule == "not_from_donor"
    assert violation.found == "mountain"
    assert violation.expected == "NOUN from nouns_from"


def test_a_content_word_from_the_wrong_donor_is_a_violation() -> None:
    """The role keying is the row's whole parameter decision, so it is checked
    against the case that would survive without it: `river` is a noun, and it is
    in `verbs_from` — which is where the verbs come from, and only the verbs. A
    checker treating the three donors as one bag of words would accept this."""
    report = _check("The small river watched the letter.")
    assert not report.satisfied
    assert [violation.found for violation in report.violations] == ["river"]
    assert report.violations[0].rule == "not_from_donor"
    assert report.violations[0].expected == "NOUN from nouns_from"


def test_a_position_carrying_the_wrong_word_class_is_a_violation() -> None:
    report = _check("The small watched watched the letter.")
    assert not report.satisfied
    violation = report.violations[0]
    assert violation.rule == "wrong_pos"
    assert violation.expected == "NOUN"


def test_a_frame_word_that_did_not_survive_is_a_violation() -> None:
    """The frame is what survives. Every content word here is drawn correctly
    and the row still fails, which is the half of the definition a
    donor-membership-only checker would drop."""
    report = _check("A small wind watched the letter.")
    assert not report.satisfied
    violation = report.violations[0]
    assert violation.rule == "frame_word_changed"
    assert violation.found == "A"
    assert violation.expected == "The"


def test_a_frame_word_in_another_case_survives() -> None:
    """Ruling 4, pinned as a rule and not as today's output: the comparison is
    casefolded, so a capitalised determiner is not a failure to refill anything.
    If a later decision makes the comparison exact, this is the test that has to
    change to say so."""
    report = _check("THE small wind watched the letter.")
    assert report.satisfied
    assert not report.violations


def test_a_drawn_word_may_repeat_and_may_equal_the_word_it_replaced() -> None:
    """Ruling 2. `letter` fills both noun positions, and `quick` is the frame's
    own adjective — legal here, where the donor is a lexicon, and illegal in
    `homosyntaxism`, where the source is the text being rewritten."""
    report = _check(
        "The quick letter watched the letter.",
        adjectives_from="The quick child painted the table.",
    )
    assert report.satisfied


def test_a_text_shorter_than_its_frame_reports_each_unanswered_position() -> None:
    report = _check("The small wind watched.")
    assert not report.satisfied
    assert [violation.rule for violation in report.violations] == ["missing_word", "missing_word"]
    assert [violation.expected for violation in report.violations] == [
        "the",
        "NOUN from nouns_from",
    ]
    assert all(violation.offset is None for violation in report.violations)


def test_an_unanswered_position_on_an_unseen_form_says_so() -> None:
    """The honesty note reaches the positions with no word to point at too: the
    frame's `cart` is a form the tagger never saw, and the verdict that the text
    still owes a noun there rests on that guess."""
    report = check(
        "chimera",
        "The small wind.",
        source="The quick boy opened the cart.",
        **DONORS,
    )
    notes = [violation.note for violation in report.violations]
    assert notes == [None, None, "tagged from a form the tagger never saw in training"]


def test_a_text_longer_than_its_frame_reports_the_tail_once() -> None:
    report = _check("The small wind watched the letter today.")
    assert not report.satisfied
    assert [violation.rule for violation in report.violations] == ["extra_words"]
    assert report.violations[0].found == "today"


def test_an_empty_frame_is_not_vacuously_satisfied() -> None:
    report = check("chimera", "The small wind watched the letter.", source="", **DONORS)
    assert report.score == 0.0
    assert report.violations[0].rule == "extra_words"


def test_an_empty_text_and_an_empty_frame_are_vacuously_satisfied() -> None:
    assert check("chimera", "", source="", **DONORS).satisfied


def test_a_violation_offset_points_into_the_whole_text() -> None:
    """Not into the sentence the token fell in: the offending noun is in the
    second sentence, so an offset rebased per sentence would be 29, not 64."""
    text = "The small wind watched the letter. The small letter watched the mountain."
    report = check(
        "chimera",
        text,
        source="The quick boy opened the door. The warm man pushed the table.",
        **DONORS,
    )
    assert not report.satisfied
    offset = report.violations[0].offset
    assert offset is not None
    assert text[offset:].startswith("mountain")
    assert offset == 64


def test_a_violation_on_an_unseen_form_says_so() -> None:
    report = _check("The small cart watched the letter.")
    violation = report.violations[0]
    assert violation.found == "cart"
    assert violation.note is not None
    assert "never saw" in violation.note


def test_undecided_words_counts_positions_the_tagger_guessed_at() -> None:
    """Reported whether or not the position produced a violation: this text is
    satisfied and a reader deciding how far to trust that needs the count."""
    report = check(
        "chimera",
        "The small cart watched the letter.",
        source=FRAME,
        **{**DONORS, "nouns_from": "The cold cart carried the letter."},
    )
    assert report.satisfied
    assert report.metrics["undecided_words"] == 1.0


def test_check_returns_a_verdict_when_a_donor_supplies_nothing() -> None:
    """Ruling 1, the checking half: an empty donor makes the constraint
    unsatisfiable, not malformed, so `check` scores it rather than raising."""
    report = _check("The small wind watched the letter.", adjectives_from="Dogs run and birds fly.")
    assert not report.satisfied
    assert [violation.rule for violation in report.violations] == ["not_from_donor"]
    assert report.violations[0].found == "small"


def test_apply_refuses_a_donor_that_supplies_nothing() -> None:
    """Ruling 1, the generating half. The message must name the field, because
    a caller with three donors cannot otherwise tell which one was empty."""
    with pytest.raises(InvalidParams) as excinfo:
        apply("chimera", FRAME, **{**DONORS, "adjectives_from": "Dogs run and birds fly."})
    assert "adjectives_from" in str(excinfo.value)


def test_apply_tolerates_an_empty_donor_the_frame_never_needs() -> None:
    """The other half of ruling 1: a frame with no adjective in it is not harmed
    by an adjectiveless `adjectives_from`, so the refusal is per position
    reached rather than per donor supplied."""
    produced = apply(
        "chimera",
        "The boy opened the door.",
        **{**DONORS, "adjectives_from": "Dogs run and birds fly."},
        seed=2,
    )
    assert "boy" not in produced


def test_what_the_generator_makes_satisfies_its_own_checker() -> None:
    """The round-trip property, carried here because `chimera` is
    `PARAMETER_GATED` out of `test_round_trip.py`: three donors are parameters
    that harness does not supply. Run over a range of seeds, so the property is
    about the generator and not about one draw."""
    for seed in range(12):
        produced = apply("chimera", FRAME, **DONORS, seed=seed)
        assert check("chimera", produced, source=FRAME, **DONORS).satisfied, produced


def test_a_draw_whose_word_class_does_not_survive_is_redrawn() -> None:
    """The defect the row's audit found, pinned on the text and seed that found it.

    `salt` is a NOUN in `nouns_from` and the tagger reads it as PROPN at the
    head of a sentence, so a generator that draws from a pool of the right
    class and stops there produces text its own checker rejects — measured,
    not supposed: before `_produce` re-tagged its own output, seed 0 on this
    text gave `... Salt carried the green crates ...` and a `wrong_pos`
    violation at `Salt`. A word's class is a fact about its position.
    """
    frame = (
        "The old lighthouse kept a steady light. "
        "Sailors watched the dark water and counted every slow turn."
    )
    donors: dict[str, Any] = {
        "nouns_from": "A grocer weighed the apples. "
        "The market held bread, salt and coffee in wooden crates.",
        "verbs_from": "She hurried, stumbled and laughed. "
        "They carried the ladder, painted the shutters and left.",
        "adjectives_from": "The morning was bright and cold. "
        "A thin mist hung over the green fields, quiet and wide.",
    }
    for seed in range(8):
        produced = apply("chimera", frame, **donors, seed=seed)
        report = check("chimera", produced, source=frame, **donors)
        assert report.satisfied, (produced, [v.rule for v in report.violations])


def test_apply_refuses_when_its_greedy_search_runs_out_at_a_position() -> None:
    """The other end of the redraw loop, and the reason it terminates: when a
    position has tried every word its donor offers and none of them still read
    as that class *given what the other positions currently hold*, the generator
    stops and names the position. It does not follow that no filling exists —
    the search is greedy and never revisits a settled position — and the case
    below is the measured proof, so the refusal must not claim exhaustion.

    An earlier version of this test said the refusal meant every word had been
    tried and none could stand there. That was false, and the counterexample
    asserted here is what falsifies it."""
    frame = (
        "The old lighthouse kept a steady light. "
        "Sailors watched the dark water and counted every slow turn."
    )
    donors: dict[str, Any] = {
        "nouns_from": "A grocer weighed salt.",
        "verbs_from": "They carried the ladder, painted the shutters and left.",
        "adjectives_from": "A thin mist hung over the green fields.",
    }
    with pytest.raises(NoCandidateWord) as excinfo:
        apply("chimera", frame, **donors, seed=0)
    message = str(excinfo.value)
    assert "Sailors" in message
    assert "nouns_from" in message
    assert "greedy" in message
    assert "may still exist" in message

    satisfying = (
        "The thin grocer carried a thin salt. "
        "Grocer carried the thin salt and carried every green grocer."
    )
    assert check("chimera", satisfying, source=frame, **donors).satisfied


def test_apply_is_reproducible_from_its_seed() -> None:
    first = apply("chimera", FRAME, **DONORS, seed=11)
    assert first == apply("chimera", FRAME, **DONORS, seed=11)


def test_the_seed_changes_the_draw() -> None:
    """Otherwise `deterministic: false` would be a claim with nothing behind it."""
    drawn = {apply("chimera", FRAME, **DONORS, seed=seed) for seed in range(12)}
    assert len(drawn) > 1


def test_apply_keeps_the_punctuation_and_spacing_of_its_frame() -> None:
    produced = apply("chimera", "The quick boy opened the door, slowly.", **DONORS, seed=1)
    assert produced.endswith(", slowly.")
    assert produced.startswith("The ")


def test_a_substituted_word_inherits_the_frame_words_capitalisation() -> None:
    """Ruling 3, end to end: the frame shouts and so does its replacement.

    `VERBS` holds exactly one VERB, so the drawn word is `watched` whatever the
    seed — named rather than hidden behind alternatives that cannot be drawn."""
    assert donor_words(VERBS, get_pack("en"), "VERB") == ["watched"]
    produced = apply("chimera", "The quick boy OPENED the door.", **DONORS, seed=1)
    assert " WATCHED " in produced
    assert produced.split()[3].isupper()


@pytest.mark.parametrize(
    "word,model,expected",
    [
        ("wind", "boy", "wind"),
        ("Wind", "boy", "wind"),
        ("wind", "Boy", "Wind"),
        ("wind", "BOY", "WIND"),
        ("wind", "A", "Wind"),
    ],
)
def test_recase_follows_the_frame_word(word: str, model: str, expected: str) -> None:
    """A single capital is Initial rather than ALL CAPS — `isupper()` alone
    would upper-case a whole word because the frame word was one letter long."""
    assert recase(word, model) == expected


def test_donor_words_are_first_appearance_order_and_casefold_deduped() -> None:
    """The draw is reproducible from the seed only if the pool it runs over is a
    function of the donor text alone. A pool built from a set would order by
    hash instead."""
    pool = donor_words(
        "The wind carried the letter. The Wind carried the river.", get_pack("en"), "NOUN"
    )
    assert pool == ["wind", "letter", "river"]


def test_apply_refuses_a_second_source() -> None:
    """`source` is the frame, and `apply` already has it as its text argument.
    Inherited from the spine, asserted here because this row is the first with
    three further text parameters beside it — a caller who reads the schema sees
    four texts and has to learn that one of them is not theirs to pass."""
    with pytest.raises(InvalidParams):
        apply("chimera", FRAME, source="The warm man pushed the table.", **DONORS)


def test_produce_returns_one_candidate() -> None:
    production = produce("chimera", FRAME, **DONORS, seed=4)
    assert len(production.texts) == 1


#: Two donor sets differing only in `adjectives_from`, both with every pool
#: larger than one word. One leaves a position with a single surviving
#: candidate and the other does not, which is what makes the pair a test of the
#: rule rather than of a pool size.
CROWDED: dict[str, Any] = {
    "nouns_from": "A grocer weighed salt and bread.",
    "verbs_from": "They polish the floor, weigh the bread and fold the cloth.",
    "adjectives_from": "The quiet, wide and slow river.",
}
UNCROWDED: dict[str, Any] = {**CROWDED, "adjectives_from": "The morning was bright and cold."}


def _pool_sizes(donors: dict[str, Any]) -> dict[str, int]:
    pack = get_pack("en")
    return {
        upos: len(donor_words(donors[field], pack, upos))
        for upos, field in (
            ("NOUN", "nouns_from"),
            ("VERB", "verbs_from"),
            ("ADJ", "adjectives_from"),
        )
    }


def test_a_position_with_one_surviving_word_is_reported_as_forced() -> None:
    """`forced_positions` states the rule it exists for: a position is forced
    when exactly one donor word still reads as the class it owes *there*, given
    the rest of this output. Asserted where every pool holds at least two words,
    so a count of one-word pools — the cheap thing this could have been, and the
    thing that would miss the collapse the metric exists for — fails it."""
    assert min(_pool_sizes(CROWDED).values()) >= 2
    metrics = produce("chimera", FRAME, **CROWDED, seed=0).candidates[0].metrics
    assert metrics["target_positions"] == 4.0
    assert metrics["forced_positions"] == 1.0


def test_a_position_whose_donor_words_all_survive_is_not_forced() -> None:
    """The other half of the rule, and the pair is the point: these donors
    differ from `CROWDED` in one field, the pool sizes are the same shape, and
    nothing here is forced. A metric that answered from the pools alone could
    not tell the two apart."""
    assert min(_pool_sizes(UNCROWDED).values()) >= 2
    metrics = produce("chimera", FRAME, **UNCROWDED, seed=0).candidates[0].metrics
    assert metrics["target_positions"] == 4.0
    assert metrics["forced_positions"] == 0.0


def test_the_metric_reports_the_position_no_seed_moves() -> None:
    """What the count is *for*: `adjectives_from` here yields one adjective, so
    the frame's adjective slot is `bright` in all twenty seeds while the rest of
    the output moves. `seed` is documented and does nothing at that position,
    and `forced_positions` is the only place a caller can read that."""
    donors: dict[str, Any] = {**CROWDED, "adjectives_from": "The morning was bright."}
    assert _pool_sizes(donors)["ADJ"] == 1
    outputs = {produce("chimera", FRAME, **donors, seed=seed).texts[0] for seed in range(20)}
    assert len(outputs) > 1
    assert all(text.split()[1] == "bright" for text in outputs)
    assert (
        produce("chimera", FRAME, **donors, seed=0).candidates[0].metrics["forced_positions"] >= 1.0
    )


def test_every_pool_collapsing_to_the_frames_own_word_is_degenerate() -> None:
    """The third check/apply asymmetry, recorded in ruling 2. Where every donor
    offers only the word already standing in that position, `_produce` has
    nothing else to draw and hands back the frame — so the spine raises
    `DegenerateOutput`, while `check` calls the same text satisfied. Both are
    right, and a reader meeting only one of them would think one was a bug."""
    frame = "The cold wind blows."
    donors: dict[str, Any] = {
        "nouns_from": "The wind blows.",
        "verbs_from": "The wind blows.",
        "adjectives_from": "The cold wind blows.",
    }
    with pytest.raises(DegenerateOutput):
        apply("chimera", frame, **donors, seed=0)
    assert check("chimera", frame, source=frame, **donors).satisfied
    assert apply("chimera", frame, **donors, seed=0, allow_identity=True) == frame
