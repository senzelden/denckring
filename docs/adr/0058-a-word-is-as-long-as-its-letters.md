# 58. A word is as long as its letters

## Context

`snowball` and `reverse_snowball` judge each word's length against an arithmetic
progression, through one shared function, `rhopalic_violations`. It measured a word
with `len` on the token the word pattern returns. That pattern keeps an apostrophe
between letters inside a word, because a contraction or an elision is one word to every
row that counts words (`don't`, `l’âme`). So `len("I'm")` was 3, and a snowball that
went `A I'm the` failed at its second word, while `be I'm` passed.

Every published statement of the row says letters. The definition is "exactly one
letter longer than the word before it", the prompt hint asks for a first word of
`{start}` letters, and the violation's `expected` reads `3 letters`. A writer who counts
letters counts two in `I'm`. denckring-bench found the gap (audit A10), and with it two
readings that look like checker errors to a writer though they are deliberate: a hyphen
splits a word in two, in `sentence_length_constraint` and `snowball_sentence` as
everywhere, and English reads `y` as a consonant, so `monoconsonantal` treats it as one.

## Decision

**A word's length is the number of its letters.** `rhopalic_violations` measures each
word with `letter_spans`, the notion of a letter the letter rows already share, so an
apostrophe is no part of a word's length and `I'm` is two letters. The word is still the
pattern's word: the apostrophe keeps `I'm` one word, and `found` names the whole token.
The letters are read unfolded, so `ß` is one letter, as written, and not the `ss` that
folding gives it. The rows take no `fold_diacritics`, and a length should not depend on
a spelling convention the writer did not choose. For the same reason a ligature is one
letter, as the letter rows already read it: `œuf` is three letters, and `ﬁne` written
with the `ﬁ` ligature is three.

The ruling (R-U9c) covers every row that measures a word's length with `len` on a word
token. A survey of the checkers found that `rhopalic_violations` is the only one:

- `word_ladder` compares lengths of words it has already reduced to letters (`_folded`),
  and its `apply` refuses a start or target that is not all letters;
- `anagram`'s `min_word_length` filters lexicon words, which can only enter a cover by
  spending the source's letters, so each is letters only;
- `paragram` buckets words by length to count pairs for a metric, and judges nothing by
  it;
- `snowball_sentence` and `sentence_length_constraint` count words, not letters;
- every other `len(word)` in a checker measures an offset into the text, which is
  characters by design.

**The hyphen and `y` readings stay, and `describe` states them.** A hyphen splits a word
because compounds are written three ways (`well-known`, `wellknown`, `well known`) and
a count should not depend on which; `y` is a vowel in French and not in English or
German, as each pack lists its vowels (ADR 0035). Both were already published by the
E6 fields of `describe().reading`: `word_examples` runs the word pattern on
`well-known` and shows two words, and `vowels` lists each language's vowels.
`reading.tokenization` stays the pattern itself rather than prose, since a caller can
run a pattern and cannot run a sentence; its field comment now names the two fields
that answer these questions, and the comment on `word_examples` no longer says a length
counts an apostrophe. A test holds the published words to what the length rows count:
`sentence_length_constraint` and `snowball_sentence` count each probe's words, and
`snowball` and `reverse_snowball` count each word's letters.

## Consequences

This is a breaking change to a verdict. A snowball with a contraction or an elision in
it is judged differently: `A I'm the` now passes, and `be I'm` now fails, with `found`
`I'm` and `expected` `3 letters`. The old reading is not available as a parameter, since
it measured something the row never claimed to.

`found` still shows the apostrophe. A reader comparing `I'm` against `3 letters` has to
know the apostrophe is not counted, which the definition and `reading.word_examples`
say but the violation does not.

The hyphen reading is now stated, not changed, so a writer who treats `well-known` as
one nine-letter word in a snowball still fails, as before. The same goes for `y` in an
English `monoconsonantal`. Stating a reading is cheaper than choosing a different one,
and a writer who reads `describe` first will not be surprised, but one who does not
will be, as the bench was.

A letter written decomposed is still read through the word pattern first, and the
pattern does not match a combining mark, so `Bär` typed as `a` and U+0308 is two words,
`Ba` and `r`, in every row that counts words. Counting letters fixes the length of a
word once found, not where it ends. That is a tokenisation question, left open here.

**No verdict or score in the golden corpus moved.** Re-measured over all 687 cases, the
reports are byte-identical before and after: no golden snowball case contains an
apostrophe. The cost of that is that the corpus does not exercise the new reading.
`tests/test_snowball.py` and `tests/test_text_units.py` do.
