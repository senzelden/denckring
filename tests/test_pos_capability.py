"""The `pos` capability's contract, independent of any row that uses it.

Split from the two procedures' own files on purpose: these assert the rules ADR
0045 decided — what a pack without the capability must do, which extra is named
when it is missing, and that a tag cannot carry a reading no annotation has —
and those rules must keep holding if either row is ever cut.
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from denckring.core.errors import MissingCapability, extra_for
from denckring.core.protocol import PosTag
from denckring.lang import get_pack
from denckring.lang.base import POS
from denckring.lang.de import GermanPack
from denckring.lang.en import EnglishPack
from denckring.lang.fr import FrenchPack


@pytest.mark.parametrize("pack", [EnglishPack(), GermanPack(), FrenchPack()])
def test_a_pack_without_the_capability_refuses_rather_than_guessing(pack: object) -> None:
    """The rule every capability here follows: a pack whose capability is
    undeclared must raise, not approximate. Core English has a spelling
    heuristic for syllables and has nothing at all for word classes."""
    assert POS not in pack.capabilities  # type: ignore[attr-defined]
    with pytest.raises(MissingCapability) as exc_info:
        pack.pos_tags(["she", "walks"])  # type: ignore[attr-defined]
    assert exc_info.value.capability == POS


def test_the_remedy_names_the_pos_extra_and_not_the_language() -> None:
    """`pos` comes from `denckring-en-pos`, which is not the extra named after
    the language. Answering an English `pos` refusal with `denckring[en]` would
    be the remedy-nobody-can-follow defect ADR 0030 fixed for German stress."""
    assert extra_for("en", POS) == "pos"


@pytest.mark.parametrize("lang", ["de", "fr"])
def test_no_extra_is_named_for_a_language_that_has_no_tagger(lang: str) -> None:
    """ADR 0045 ships `pos` English-only. Falling through to the language's own
    extra would tell a German caller to install something that has never carried
    a tagger and which they probably already have.

    Asserted as `is None` rather than `!= lang`: the failure being guarded
    against is naming *any* installable extra, not naming this one.
    """
    assert extra_for(lang, POS) is None


def test_an_unsupplied_pair_is_not_recorded_as_a_permanent_ceiling() -> None:
    """The two sets mean different things and neither may absorb the other.
    French has no lexical stress and never will (ADR 0034); German has no
    tagger *yet*. Collapsing them would turn an unbuilt distribution into a
    statement about the language.
    """
    from denckring.core.errors import _PERMANENTLY_MISSING, _UNSUPPLIED_TODAY

    assert ("de", POS) in _UNSUPPLIED_TODAY
    assert ("de", POS) not in _PERMANENTLY_MISSING
    assert ("fr", "stress") in _PERMANENTLY_MISSING
    assert ("fr", "stress") not in _UNSUPPLIED_TODAY


class TestTheInstalledTagger:
    """Skipped where `denckring[pos]` is not installed, like every other
    data-dependent suite here. CI's matrix syncs the extra, so these run there."""

    @staticmethod
    def pack() -> object:
        pytest.importorskip("denckring_en_pos")
        return get_pack("en")

    def test_the_composed_pack_declares_the_capability(self) -> None:
        assert POS in self.pack().capabilities  # type: ignore[attr-defined]

    def test_one_tag_per_token_and_no_tag_for_an_empty_sentence(self) -> None:
        pack = self.pack()
        words = ["the", "lamps", "were", "burning"]
        assert len(pack.pos_tags(words)) == len(words)  # type: ignore[attr-defined]
        assert pack.pos_tags([]) == []  # type: ignore[attr-defined]

    def test_only_a_verb_or_auxiliary_may_carry_a_verb_form(self) -> None:
        """What the joint label exists to prevent. Two independently-argmaxed
        models can return `NOUN` carrying `Fin`, which is a reading no
        annotation in the treebank has; a joint label cannot.

        Asserted over a paragraph rather than one sentence so the claim is about
        the label space and not about one lucky tagging.
        """
        pack = self.pack()
        sentences = [
            ["she", "walks", "home", "before", "the", "lamps", "are", "lit"],
            ["night", "the", "long", "road", "empty", "the", "lamps", "still", "burning"],
            ["the", "road", "taken", "by", "the", "others", "had", "been", "washed", "away"],
        ]
        for words in sentences:
            for tag in pack.pos_tags(words):  # type: ignore[attr-defined]
                if tag.verb_form is not None:
                    assert tag.upos in {"VERB", "AUX"}, tag

    #: Surface forms that are a noun in one clause and a finite verb in another,
    #: as `(form, nominal sentence, index, verbal sentence, index)`. Ten rather
    #: than one, so the test is a claim about the capability and not about a
    #: single lucky tagging — all ten were measured before being written down.
    #:
    #: Note what the nominal sentences all are: complete clauses. The first
    #: version of this test used the bare fragment *the evening walks* and
    #: failed, and the tagger was right — that fragment IS a clause, and reading
    #: `walks` as its finite verb is the better reading. A guard whose example is
    #: ambiguous tests the example, not the code.
    AMBIGUOUS: ClassVar[list[tuple[str, list[str], int, list[str], int]]] = [
        ("walks", ["the", "evening", "walks", "were", "long"], 2, ["she", "walks", "home"], 1),
        ("runs", ["the", "morning", "runs", "were", "long"], 2, ["he", "runs", "fast"], 1),
        ("books", ["the", "books", "were", "old"], 1, ["she", "books", "a", "room"], 1),
        ("rose", ["a", "rose", "in", "the", "garden"], 1, ["the", "sun", "rose", "slowly"], 2),
        ("watch", ["the", "watch", "was", "gold"], 1, ["they", "watch", "the", "road"], 1),
        ("lights", ["the", "lights", "were", "dim"], 1, ["she", "lights", "a", "candle"], 1),
        ("cooks", ["the", "cooks", "were", "tired"], 1, ["he", "cooks", "dinner"], 1),
        ("paints", ["the", "paints", "were", "dry"], 1, ["she", "paints", "birds"], 1),
        ("plays", ["the", "plays", "were", "short"], 1, ["she", "plays", "chess"], 1),
    ]

    @pytest.mark.parametrize("form,nominal,noun_at,verbal,verb_at", AMBIGUOUS)
    def test_context_decides_the_reading_which_is_why_the_capability_exists(
        self,
        form: str,
        nominal: list[str],
        noun_at: int,
        verbal: list[str],
        verb_at: int,
    ) -> None:
        """One surface form, two clauses, two readings. If this stops holding the
        capability has stopped earning its cost — a per-word lookup would be
        cheaper and would answer just as well.

        Both halves are asserted, not just that they differ: "they differ" also
        passes if the tagger has simply swapped them.
        """
        pack = self.pack()
        noun = pack.pos_tags(nominal)[noun_at]  # type: ignore[attr-defined]
        verb = pack.pos_tags(verbal)[verb_at]  # type: ignore[attr-defined]
        assert (noun.upos, noun.verb_form) == ("NOUN", None), f"{form} in {nominal}"
        assert (verb.upos, verb.verb_form) == ("VERB", "Fin"), f"{form} in {verbal}"

    def test_an_invented_word_is_reported_as_one_the_tagger_never_saw(self) -> None:
        """`known` is this capability's `exact`. A row reporting a violation on
        a token where it is False has to say so, so it must actually be False
        for a form outside the training data — and True for an ordinary one."""
        pack = self.pack()
        tags = pack.pos_tags(["the", "zorblatt", "quivered"])  # type: ignore[attr-defined]
        assert tags[0].known is True
        assert tags[1].known is False

    def test_tagging_the_same_sentence_twice_agrees(self) -> None:
        """A weak check kept deliberately, and labelled as weak.

        Two calls in one process would agree even if `_predict` resolved ties by
        dict order, so this cannot fail for the reason it looks like it is about.
        The tie-break is tested directly below; this one only catches a tagger
        that has become stateful across calls.
        """
        pack = self.pack()
        words = ["the", "lamps", "were", "burning", "still"]
        assert pack.pos_tags(words) == pack.pos_tags(words)  # type: ignore[attr-defined]

    def test_every_tag_is_the_declared_shape(self) -> None:
        pack = self.pack()
        for tag in pack.pos_tags(["she", "walks"]):  # type: ignore[attr-defined]
            assert isinstance(tag, PosTag)
            assert tag.upos.isupper()


def test_a_tie_is_broken_by_the_label_and_not_by_feature_order() -> None:
    """The tie-break in `Tagger._predict`, tested on a model built to tie.

    Scores accumulate in a plain dict, so without the second sort key the winner
    among equals is decided by insertion order, which is feature order, which is
    the order `features()` happens to return. That makes a verdict depend on
    something no reader would think of as part of the model.

    The two taggers below differ only in which feature is listed first. A
    tie-break by label makes them agree; one by dict order makes them disagree.
    """
    pytest.importorskip("denckring_en_pos")
    from denckring_en_pos.perceptron import Tagger

    classes = ["NOUN|-", "VERB|Fin"]
    #: Equal weight on both labels, reached through two different features, so
    #: the two orderings below produce the same scores by different routes.
    one = Tagger(
        weights={"bias": {"NOUN|-": 1.0}, "w x": {"VERB|Fin": 1.0}},
        tagdict={},
        classes=classes,
        vocabulary=frozenset(),
    )
    other = Tagger(
        weights={"w x": {"VERB|Fin": 1.0}, "bias": {"NOUN|-": 1.0}},
        tagdict={},
        classes=classes,
        vocabulary=frozenset(),
    )
    assert one.tag(["x"]) == other.tag(["x"])
    # And it is the label that decides, not whichever arrived first.
    assert one.tag(["x"]) == ["VERB|Fin"]
