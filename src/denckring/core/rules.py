"""What kind of failure each `violation.rule` names (audit C3).

Every row declares the rules its checker can emit (`BaseProcedure.rules`, U3), and
a consumer grading many rows wants to count failures by kind, not by 169 rule
names: a forbidden letter, a missing letter and a line out of order are different
mistakes for a writer to make. denckring-bench kept that map itself, in a file it
re-checked by hand against every release. It is here instead, keyed by the rule
string, which is shared vocabulary: `missing_line` means the same on every row
that emits it.

One category per rule, and the set is closed. The bench's eight classes were drawn
over a pool with no prosodic rows and no data-driven rows; `sound` and
`unreadable` are added for the two kinds of failure only those rows have.
"""

from __future__ import annotations

from typing import Literal

Category = Literal[
    "excluded_letter",
    "inventory",
    "word_choice",
    "position",
    "structure",
    "count",
    "length",
    "transcription",
    "sound",
    "unreadable",
]

#: Each category, and what a rule in it says about the text.
CATEGORIES: dict[str, str] = {
    "excluded_letter": (
        "The text uses a letter the constraint rules out: a forbidden letter, a vowel or "
        "consonant outside the allowed set, a letter outside the bank or name."
    ),
    "inventory": (
        "The letters used are not the required inventory: a required letter missing, one "
        "repeated or left over, or a letter tally or window wrong."
    ),
    "word_choice": (
        "A word is ruled out, or a word that must be in the lexicon, or of a kind, is not."
    ),
    "position": (
        "A letter or word is not where the constraint puts it: the wrong initial, final, "
        "opening, closing or end word, or out of order."
    ),
    "structure": (
        "A relation the text must hold between its parts fails: mirror symmetry, a "
        "square's rows and columns, a refrain, a chain or a split, a device's order."
    ),
    "count": (
        "Units have the wrong number or size: lines, stanzas, rows, parts, sentences or "
        "words of the wrong count or length."
    ),
    "length": "The text, or its source, is too short for the checker to judge.",
    "transcription": (
        "The answer departs from what its source and rule give: a word, letter, line or "
        "sentence wrong, missing, extra, out of place, unchanged or not from the source."
    ),
    "sound": (
        "A judgement on pronunciation fails: a rhyme, a stress, a syllable count, a sound "
        "too near or too far."
    ),
    "unreadable": (
        "The checker could not read part of the text: a word its dictionary or the "
        "supplied data lacks, under a setting that fails it rather than leaving it out."
    ),
}

_BY_CATEGORY: dict[Category, tuple[str, ...]] = {
    "excluded_letter": (
        "forbidden_letter",
        "foreign_consonant",
        "foreign_vowel",
        "letter_outside_bank",
        "letter_outside_name",
        "tall_or_deep_letter",
        "undisplayable_letter",
    ),
    "inventory": (
        "empty_anagram",
        "empty_transposal",
        "missing_letter",
        "missing_vowel",
        "not_a_transposal",
        "repeated_letter",
        "repeated_principle",
        "repeated_vowel",
        "surplus_letter",
        "unused_bank_letter",
        "unused_name_letter",
        "window_too_long",
        "wrong_total",
    ),
    "word_choice": (
        "finite_verb",
        "forbidden_word",
        "not_a_word",
        "palindrome_not_semordnilap",
        "polysyllabic_word",
        "reversal_is_not_a_word",
        "splice_not_a_word",
        "synonym_is_the_word",
    ),
    "position": (
        "out_of_order",
        "spine_letter_missing",
        "synonym_not_in_order",
        "too_few_alliterating",
        "wrong_closing",
        "wrong_end",
        "wrong_end_word",
        "wrong_final",
        "wrong_initial",
        "wrong_letter",
        "wrong_letter_at_position",
        "wrong_opening",
    ),
    "structure": (
        "broken_interlock",
        "broken_refrain",
        "broken_rentrement",
        "different_length",
        "does_not_divide",
        "domain_repeated",
        "halves_do_not_rejoin",
        "invalid_size",
        "line_not_offered",
        "mirror_mismatch",
        "missing_haiku",
        "missing_prose",
        "missing_radif",
        "module_not_on_the_board",
        "no_material_inserted",
        "no_paragram",
        "not_a_chamber",
        "not_closed",
        "not_doubled",
        "not_horizontally_palindromic",
        "not_on_the_rings",
        "not_vertically_palindromic",
        "onsets_not_distinct",
        "repeated_edge",
        "repeated_word",
        "ring_skipped",
        "row_column_mismatch",
        "step_too_large",
        "too_few_splits",
        "too_few_variants",
        "word_not_offered",
        "wrong_alternation",
        "wrong_arity",
        "wrong_ending",
        "wrong_stanza_shape",
    ),
    "count": (
        "empty_grid",
        "extra_line",
        "extra_unit",
        "incomplete_quatrain",
        "interior_terminator",
        "length_mismatch",
        "missing_line",
        "missing_unit",
        "no_tablet_for_length",
        "too_few_links",
        "too_few_steps",
        "too_few_words",
        "wrong_line_count",
        "wrong_number_of_excerpts",
        "wrong_part_count",
        "wrong_row_length",
        "wrong_sentence_count",
        "wrong_sentence_length",
        "wrong_word_count",
        "wrong_word_length",
    ),
    "length": ("empty_source", "empty_stream", "too_short"),
    "transcription": (
        "ambiguous_noun_unchanged",
        "changed_a_non_noun",
        "changed_proclitic",
        "domain_unknown",
        "extra_letters",
        "extra_word",
        "extra_words",
        "frame_word_changed",
        "host_unrecoverable",
        "identical_to_host",
        "invented_part",
        "line_not_turned",
        "line_out_of_fold",
        "missing_intercalated_sentence",
        "missing_part",
        "missing_word",
        "no_displacement",
        "no_number_for_word",
        "no_word_at_number",
        "not_expanded",
        "not_from_donor",
        "not_in_source",
        "not_in_the_corpus",
        "not_the_fold",
        "not_the_gloss_sequence",
        "not_the_graft",
        "pattern_not_on_the_tablet",
        "pattern_without_phrase",
        "phrase_not_set",
        "sentence_dropped",
        "sentence_not_in_source",
        "source_sentence_out_of_place",
        "splice_not_present",
        "unchanged",
        "unknown_tone",
        "unrecoverable",
        "word_not_in_source",
        "word_out_of_rotation",
        "wrong_column_word",
        "wrong_consonant",
        "wrong_digits",
        "wrong_displacement",
        "wrong_headword",
        "wrong_line_end",
        "wrong_pos",
        "wrong_relation",
        "wrong_rendering",
        "wrong_vowel",
        "wrong_word",
    ),
    "sound": (
        "broken_qafia",
        "distance_out_of_band",
        "does_not_rhyme",
        "does_not_scan",
        "identical_rhyme",
        "no_double_dactylic_word",
        "no_repeated_vowel",
        "sound_distance",
        "sound_out_of_band",
        "unwanted_rhyme",
        "wrong_line_length",
        "wrong_stress",
        "wrong_syllable_count",
    ),
    "unreadable": (
        "ambiguous_nouns_undecidable",
        "rhyme_undecidable",
        "unknown_gloss",
        "unknown_pronunciation",
        "unknown_relation",
        "unknown_rhyme",
        "unresolvable_pronunciation",
        "unresolved_phonemes",
        "unresolved_proverb_pair",
    ),
}

#: Every declared rule, mapped to its category. `tests/test_rule_categories.py` holds
#: it to the declarations both ways: no declared rule without a category, no entry
#: for a rule no row declares.
RULE_CATEGORIES: dict[str, Category] = {
    rule: category for category, rules in _BY_CATEGORY.items() for rule in rules
}
