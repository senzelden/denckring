# Language packs

What a third-party language pack must implement, and how it tells the library
what it can do.

`LanguagePack` and `get_pack` are importable from `denckring` and are under the
README's stability promise: a method here keeps its signature and meaning, and a new
one arrives as an optional member a caller reads with `getattr`.

::: denckring.core.protocol.LanguagePack

::: denckring.core.protocol.Constructive

## Capabilities

A pack does not declare a language "supported" or not — it declares a `capabilities`
set, built from string constants defined in `denckring.lang.base`: `TOKENS`,
`ALPHABET`, `FOLD_DIACRITICS`, `LETTER_SHAPES`, `SYLLABLES`, `SYLLABLES_HEURISTIC`,
`SYLLABLES_DICTIONARY`, `WORDS`, `NOUNS`, `GLOSSES`, `PHONEMES` and `STRESS`. A
procedure, in turn, declares a `requires` list of the same strings on its catalogue
entry. `BaseProcedure.check` compares the two before running anything: if the pack's
`capabilities` do not cover everything the procedure `requires`, it raises
[`MissingCapability`](errors.md#denckring.core.errors.MissingCapability) naming the
procedure, the language and the missing capability, rather than falling back to an
approximation. Adding a language pack is a matter of implementing
[`LanguagePack`](#denckring.core.protocol.LanguagePack) and declaring which of these
strings it can honestly back — nothing more.

## Word membership and the graded list

`is_word` and `graded_words` answer different questions, and in English they
disagree on purpose. `is_word` is the membership oracle of
[ADR 0015](../adr/0015-lexicon-capabilities.md): WordNet's noun lemmas and CMUdict's
headwords, deliberately broad ("could this be a word"). `graded_words` is SCOWL's size
classes of [ADR 0028](../adr/0028-the-graded-lexicon.md), a ranking by commonness. Each
holds words the other lacks: SCOWL has verbs and adjectives neither oracle source
carries (`abjure`), and also entries that are not words at all (`payed` and `numbest`
sit in band 10), so `is_word` is not widened to cover it. A caller wanting everyday
words should not treat either as that list, but use the curated everyday-words view
(planned).
