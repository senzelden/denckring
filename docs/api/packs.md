# Language packs

What a third-party language pack must implement, and how it tells the library
what it can do.

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
