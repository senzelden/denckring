# denckring — a German lexicon, and the pack that carries it

**Date:** 2026-08-16
**Status:** approved
**Scope:** `lexicon.words` and `lexicon.nouns` for German, in a new data distribution

## Purpose

Give the German pack the two lexical capabilities the English pack already has, so that
five implemented procedures stop being English-only. German currently declares
`tokens`, `alphabet`, `fold_diacritics` and `letter_shapes` — enough for Batch 1's
letter work, and nothing that needs to know whether a string is a word.

The interface for this already exists. `BasePack` declares `is_word`, `nouns` and
`noun_index`, each raising `MissingCapability`, and `EnglishDataPack` overrides them.
No protocol changes; this is a second implementation of a settled shape.

## The finding that prompted this

Two corrections to earlier assumptions, both worth recording because both were wrong in
a way that would have wasted work.

**`n_plus_7`, `s_plus_7`, `anagram` and `slenderizing` are not blocked on a lexicon.**
They were described as waiting on a capability. They are not: `n_plus_7` and `s_plus_7`
require `lexicon.nouns`, which the English pack has provided since ADR 0015, and the
other two require only `tokens` and `fold_diacritics`. Their missing `apply` is ordinary
work and is **out of scope here**, so that it does not ride along on a data change.

**Installing a German data pack would break the package outright.** Core declares
`de = "denckring.lang.de:GermanPack"` in the `denckring.lang` entry-point group, and
`lang._install` raises `DuplicatePack` when two entry points claim one language. A
second distribution claiming `de` therefore raises on the first `get_pack("de")` call.
English is immune only because core English is a built-in *default* rather than an entry
point, which is what lets `denckring-en-data` override it. This must be fixed before any
data exists to install.

## Decisions

| Decision | Rationale |
|---|---|
| German moves from entry point to built-in default | The only arrangement in which a data pack can override a core pack. Makes `de` behave exactly like `en`. Amends ADR 0010. |
| A new `denckring-de-data` distribution | ADR 0013's pattern, unamended. Keeps the core wheel free of several MB and preserves the per-language licence quarantine for whichever language arrives next with a worse licence. |
| Wikidata Lexemes as the source, CC0 | No attribution and no share-alike, unlike igerman98 (GPL-2/3) or a Wiktionary dump (CC BY-SA). Measured coverage: 188,947 noun lexemes, 1,399,865 inflected noun forms. |
| The generating queries are committed | The vendored files are reproducible. CMUdict is not, and a second opaque blob is not worth adding. |
| Casefold for comparison; keep umlauts and ß | `fold_diacritics` would collide `Bär` with `Bar`. ADR 0009 made folding a *procedure* parameter precisely so the data layer does not decide it for every caller. |
| Stored lemmas keep their capitalisation | German nouns are capitalised. `nouns()` is read by people as well as indexed by N+7. |
| Synonyms, antonyms, glosses stay unimplemented for German | ADR 0015: naming a capability before a checker can honestly use it is the error that ADR exists to prevent. |

## Architecture

```
denckring (core, MIT)
  lang/__init__.py     _DEFAULTS = {"en": EnglishPack(), "de": GermanPack()}
  lang/base.py         is_word / nouns / noun_index → MissingCapability
       ▲                                    ▲
       │ subclasses                         │ subclasses
denckring-en-data                    denckring-de-data          (new)
  entry point en                       entry point de
  CMUdict + WordNet                    Wikidata Lexemes, CC0
  LICENSE-CMUDICT, LICENSE-WORDNET     LICENSE-WIKIDATA
```

`GermanDataPack(GermanPack)` overrides three methods and extends `capabilities` with
`NOUNS` and `WORDS`. Nothing else in core changes except the two lines that move German
out of the entry-point group and into the defaults.

## Components

**`denckring_de_data.nouns_path` / `words_path`** — gzipped text, one entry per line,
read through `lru_cache` as `pronunciations()` already is.

- `nouns.txt.gz` — noun lemmas in dictionary order, restricted to purely alphabetic
  single tokens. ADR 0015's rule for English applies unchanged: N+7 walks the list, and
  a displacement has to be a token the tokeniser returns whole, so
  `Vereinigte Staaten von Amerika` is excluded.
- `words.txt.gz` — the membership oracle: every inflected form of every German lexeme,
  across **all** lexical categories, unioned with the noun lemmas above. Not nouns
  alone — `charade` and `word_square` ask "is this a word", and a noun-only oracle would
  reject `singen` and `rot`. The measured 1,399,865 is noun forms only and is therefore
  a lower bound on this file; the all-category count is to be recorded when the file is
  generated. Like English, this answers "could this be a word" rather than "is this in a
  dictionary of standard German", and procedures resting on it inherit that.

**`GermanDataPack`** — `is_word`, `nouns`, `noun_index`, plus `_lemma` implementing the
German normalisation above.

**`scripts/build_lexicon.py`** (in the new package) — the SPARQL queries and the
filtering, committed so the vendored files can be regenerated and diffed.

## Data flow

`check("…", lang="de")` → `BaseProcedure.check` → `require_capability(pack, "lexicon.nouns")`
→ `GermanDataPack.noun_index(word)` → `noun_positions()` (cached) → index or `None`.

Identical to the English path. A user without `denckring[de]` installed gets
`MissingCapability("n_plus_7", "de", "lexicon.nouns")` from `require_capability`, which
is the existing behaviour for any unmet capability and needs no new error.

## Catalogue changes

Five implemented rows gain `de` in `languages`:

| row | capability |
|---|---|
| `charade` | `lexicon.words` |
| `semordnilap` | `lexicon.words` |
| `word_square` | `lexicon.words` |
| `n_plus_7` | `lexicon.nouns` |
| `s_plus_7` | `lexicon.nouns` |

No procedure code changes — each already reaches the lexicon through the pack. Each new
language needs a golden fixture, because `test_every_declared_language_has_a_golden_case`
enforces it. That invariant is the acceptance criterion, not an obstacle.

## Error handling

- **Missing distribution.** `MissingCapability`, unchanged.
- **Both packs installed.** Must not raise. This is the regression the entry-point fix
  exists to prevent, and it gets a test that installs both and calls `get_pack("de")`.
- **Corrupt or truncated data file.** The loader fails loudly on read rather than
  returning a partial list — a silently short noun list makes N+7 wrong rather than
  broken, and a wrong answer is worse than an exception.

## Testing

| Test | What it protects |
|---|---|
| `test_every_declared_language_has_a_golden_case` (existing) | Forces a German fixture for each of the five rows |
| `test_round_trip` (existing) | Covers `n_plus_7`'s generator in German once one exists |
| Pack capability declaration | `GermanDataPack.capabilities` ⊇ `{NOUNS, WORDS}` |
| No `DuplicatePack` with both installed | The bug this spec leads with |
| `is_word` / `noun_index` on known German words | The lexicon answers at all |
| `Bär` ≠ `Bar` | The normalisation decision, as a named regression |
| Noun list is single-token and alphabetic | ADR 0015's rule, enforced rather than assumed |

## Out of scope

- `lexicon.synonyms`, `lexicon.antonyms`, `lexicon.glosses` for any language.
- French, and any third language.
- The four missing `apply` implementations (`anagram`, `n_plus_7`, `s_plus_7`,
  `slenderizing`) — unblocked already, and deliberately not bundled with a data change.
- Syllables, phonemes and stress for German. The English pack has them; mirroring those
  needs a pronouncing dictionary, which is a separate question with a separate licence.

## ADR consequences

Two ADRs to write:

- **Amending ADR 0010.** German moves from entry point to built-in default. The
  demonstration ADR 0010 wanted — that a pack can install the way a third-party pack
  installs — is now made by two genuinely external distributions instead of by core
  against itself, which is a stronger demonstration than the one being removed.
- **A new ADR for the German lexicon**, recording the source, the licence, the
  normalisation decision, and the coverage figures, as ADR 0015 did for English.
