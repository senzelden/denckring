# 15. One capability per question the lexicon is asked

## Context

Thirteen catalogued rows declared `lexicon.nouns`. They wanted five different things:
word membership (`charade`, `semordnilap`, `word_square`), an ordered noun list
(`n_plus_7`, `s_plus_7`), synonyms (`kangaroo_word`, `synonymic_substitution`,
`chimera`), antonyms (`antonymic_substitution`, `antonymic_translation`) and glosses
(the `definitional_*` family).

A row asking for a thesaurus while declaring it needs a noun list is the same class of
error as a catalogue definition promising more than its checker verifies.

## Decision

`lexicon.words` and `lexicon.nouns` are separate capabilities with a pack behind them.
`lexicon.synonyms`, `lexicon.antonyms` and `lexicon.glosses` are named on the rows that
need them and have **no** pack behind them, which is the honest state.

Naming a capability before there is a checker that can honestly use it would repeat the
mistake being fixed here, so those three stay unimplemented until a procedure can
answer them without guessing.

## Consequences

`denckring status` is unchanged in shape but truer in content: the eight remaining rows
now say what they are actually waiting for.

The membership oracle is deliberately broad, and broad in a way callers inherit. It is
the union of WordNet's noun lemmas and CMUdict's headwords, so it answers "could this be
a word" rather than "is this in a dictionary of standard English" — CMUdict lists `tac`,
which means `cat` reverses into something this oracle calls a word. `semordnilap` rests
on that and says so.

The noun list is restricted to purely alphabetic lemmas. N+7 walks it, and a
displacement has to be a word the tokeniser gives back whole: `cat's-paw` comes back as
three tokens and would break the correspondence between source and result.
