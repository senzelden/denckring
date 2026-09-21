"""What the tagger build decides before any training happens — ADR 0045.

Tested against CoNLL-U-shaped fixture rows, never a download: the three splits
are 19 MB, and a test that fetched them would be a test nobody runs. The same
reasoning `test_de_frequency_build.py` records.

The decisions pinned here are the ones that would otherwise fail silently. A
model trained through a mis-read treebank does not crash; it just gets worse, and
every accuracy figure in the README would still be produced and still be wrong.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "packages/denckring-en-pos/scripts"))

import build_tagger
from build_tagger import build_tagdict, read_conllu
from denckring_en_pos import perceptron


def parse(text: str) -> list[tuple[list[str], list[str]]]:
    return list(read_conllu(text))


def row(index: str, form: str, upos: str, feats: str = "_") -> str:
    """One CoNLL-U line. Only the columns the build reads carry values."""
    return "\t".join([index, form, "_", upos, "_", feats, "_", "_", "_", "_"])


def test_the_training_and_inference_features_are_the_same_function() -> None:
    """The bug this module layout exists to prevent, asserted structurally.

    A tagger whose training and inference features drift apart does not fail — it
    quietly gets worse, and no test of either half alone can see it. Identity,
    not equality of behaviour on a sample: two copies that agree on the cases a
    test happens to try are exactly the failure being guarded against.
    """
    assert build_tagger.features is perceptron.features


def test_punctuation_is_dropped_because_word_spans_never_yields_it() -> None:
    """The decision that makes the model match its input, and the one that makes
    the reported accuracy lower than the published figures for this feature set."""
    text = "\n".join([row("1", "she", "PRON"), row("2", "walks", "VERB"), row("3", ".", "PUNCT")])
    assert parse(text) == [(["she", "walks"], ["PRON|-", "VERB|-"])]


def test_symbols_are_dropped_with_the_punctuation() -> None:
    text = "\n".join([row("1", "cost", "NOUN"), row("2", "$", "SYM")])
    assert parse(text) == [(["cost"], ["NOUN|-"])]


def test_a_multiword_range_is_not_a_token_of_its_own() -> None:
    """`don't` is annotated as a 1-2 range plus its two parts. Taking the range
    as well would count the word twice and put a form in the vocabulary that the
    tokeniser never produces."""
    text = "\n".join([row("1-2", "don't", "_"), row("1", "do", "AUX"), row("2", "n't", "PART")])
    assert parse(text) == [(["do", "n't"], ["AUX|-", "PART|-"])]


def test_an_empty_node_is_skipped() -> None:
    """Ellipsis nodes ("7.1") are reconstructed material with no surface form."""
    text = "\n".join([row("1", "she", "PRON"), row("1.1", "walks", "VERB")])
    assert parse(text) == [(["she"], ["PRON|-"])]


def test_the_verb_form_feature_is_what_the_label_carries() -> None:
    """`VerbForm` is the whole reason for a joint label: `verbless_prose` turns on
    telling `Fin` from `Part`, and a bare UPOS cannot."""
    text = "\n".join(
        [
            row("1", "were", "AUX", "Mood=Ind|Tense=Past|VerbForm=Fin"),
            row("2", "burning", "VERB", "Tense=Pres|VerbForm=Part"),
            row("3", "lamps", "NOUN", "Number=Plur"),
        ]
    )
    _, labels = parse(text)[0]
    assert labels == ["AUX|Fin", "VERB|Part", "NOUN|-"]


def test_a_feature_column_of_underscore_means_no_verb_form() -> None:
    assert parse(row("1", "lamps", "NOUN"))[0][1] == ["NOUN|-"]


def test_sentences_split_on_blank_lines_and_comments_are_ignored() -> None:
    text = "\n".join(
        [
            "# sent_id = 1",
            "# text = she walks",
            row("1", "she", "PRON"),
            row("2", "walks", "VERB"),
            "",
            "# sent_id = 2",
            row("1", "night", "NOUN"),
        ]
    )
    assert [words for words, _ in parse(text)] == [["she", "walks"], ["night"]]


def test_a_trailing_sentence_with_no_final_blank_line_is_not_lost() -> None:
    """A file that does not end in a newline-separated blank would otherwise drop
    its last sentence, which is a silent loss of training data."""
    assert parse(row("1", "night", "NOUN")) == [(["night"], ["NOUN|-"])]


def test_the_tagdict_takes_only_frequent_and_near_unambiguous_words() -> None:
    """Both halves of the rule, each shown to be load-bearing on its own."""
    frequent_and_stable = [(["the"], ["DET|-"])] * 25
    assert build_tagdict(frequent_and_stable) == {"the": "DET|-"}

    # Stable but rare: nineteen is below the floor of twenty.
    assert build_tagdict([(["the"], ["DET|-"])] * 19) == {}

    # Frequent but ambiguous: 24 of 30 is 0.8, under the 0.97 bar. This is the
    # half that matters — a word like `walks` must reach the perceptron, which is
    # the only part of the model that can read its sentence.
    ambiguous = [(["walks"], ["VERB|Fin"])] * 24 + [(["walks"], ["NOUN|-"])] * 6
    assert build_tagdict(ambiguous) == {}


def test_the_tagdict_is_keyed_by_the_lowercased_form() -> None:
    """Inference looks up `context[index]`, which is lower-cased. A tagdict keyed
    by surface form would silently never hit for a sentence-initial word."""
    assert build_tagdict([(["The"], ["DET|-"])] * 25) == {"the": "DET|-"}
