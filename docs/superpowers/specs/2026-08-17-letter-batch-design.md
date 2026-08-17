# denckring — the letter batch, and the shape of the remaining backlog

**Date:** 2026-08-17
**Status:** approved
**Scope:** batch A of 7 — the four buildable rows in the `letter` family

## Purpose

Implement `belle_absente`, `pangrammatic_window`, `paragram` and `serial_lipogram`, taking
`implemented` from 75 to 79.

The batch is chosen for its size, not its value. It is the smallest complete group in the
backlog, needs no capability the packs lack and no helper that does not already exist, so
its real job is to prove the pipeline — spec, plan, parallel implementers, review loop —
on work where a mistake in the *process* costs four procedures rather than eighteen.

## The backlog this comes from

54 catalogued rows are unbuilt and mechanically checkable. 46 of them need nothing the
English pack lacks; the other 8 wait on `lexicon.synonyms`, `lexicon.antonyms` or
`lexicon.glosses`, which ADR 0015 deliberately left unimplemented.

Grouped by the machinery they share rather than by catalogue family, because that is what
decides how much of each batch is reuse:

| Batch | Rows | Shares |
|---|---|---|
| **A — letter** | 4 | `alphabet` and folding only. **This spec.** |
| B — form, syllabic | 7 | The existing syllable machinery |
| C — form, rhymed | 11 | `rhyme_scheme` and the metre helpers |
| D — word | 8 | Mixed; four are source-relative |
| E — extraction | 6 | All source-relative |
| F — translation | 6 | All source-relative, and the hardest to check honestly |
| G — syntax | 4 | Mixed |

Two facts shape everything after A. The 18 form rows are 39% of the backlog and depend on
`syllables`/`phonemes` — CMUdict, which only English has — so they will ship English-only
and are the batch a German pronouncing dictionary would unlock. And 26 of the 46 are
`checkability: source`, so their fixtures carry a source and their checkers are
comparisons rather than inspections.

## Decisions

| Decision | Rationale |
|---|---|
| `pangrammatic_window` takes a **required** `max_length` | "As short as possible" is not decidable from one text. Without a bar the procedure is `pangram` under a second name. ADR 0009's principle: the editorial choice becomes a parameter, not a hidden constant. Required rather than defaulted, because an invented default would look authoritative. |
| `paragram` checks for a one-letter word pair **within** the text | The row says `checkability: self` and requires no lexicon, so the property has to be visible in the text alone. Two words of equal length differing at exactly one position satisfies that, and matches "turning the alteration into the point of the line" — both halves of the swap are present. |
| `paragram` gets a lexicon-gated `apply` | The row is `kind: both`. Shipping it without a generator would reopen the gap just closed for `anagram`, `slenderizing`, `n_plus_7` and `s_plus_7`. Same shape as `anagram`: `require_capability` inside `apply`, and `requires` untouched so `check` stays core-only. |
| `serial_lipogram` mirrors `abecedarian`'s `unit`, but **not** its inferred `start` | `abecedarian` infers the starting letter from the first unit's initial, because its constraint is a presence. A serial lipogram's constraint is an *absence*, and a short paragraph is missing many letters, so nothing can be inferred. `start` defaults to the alphabet's first letter — which is Tryphiodorus's own arrangement, book 1 omitting alpha. |
| `serial_lipogram`'s default unit is the paragraph | Tryphiodorus wrote 24 *books*. Lines would make the constraint change every line, which is a different procedure. Needs a `paragraph_spans` helper beside `line_spans`. |
| Each row's `requires` is verified against actual use | The German branch found `semordnilap` and `word_square` declaring `fold_diacritics` they no longer called. `requires` gates `check`, so a stale entry raises `MissingCapability` for a caller who needed nothing. |

## Components

Each procedure is four files. The existing invariants enforce all four: `test_strategies.py`
is parametrised by procedure id and imports `tests/strategies/<id>.py`, and
`test_every_declared_language_has_a_golden_case` requires the fixture.

| File | Responsibility |
|---|---|
| `src/denckring/procedures/<id>.py` | The checker, registered with `@register`. One module per procedure (ADR 0007). |
| `tests/strategies/<id>.py` | `satisfying()` and `violating()`, both returning `CaseStrategy` — the module contract. |
| `src/denckring/eval/fixtures/golden/<id>.yaml` | At least one satisfying and one violating case, recording what the checker actually returns. |
| `tests/test_<id>.py` | Unit tests for the cases a generator will not reach. |

Plus one shared addition: `paragraph_spans` in `src/denckring/core/text.py`, beside
`line_spans`, splitting on blank lines and returning `(offset, text)` pairs so violations
keep their offsets.

## The four procedures

### `belle_absente`

Params: `name: str`, plus `DiacriticParams`. The name is folded (when
`fold_diacritics` is set), lower-cased, and reduced to its alphabetic characters — so
`"Georges Perec"` gives twelve constraints, not thirteen, and the space is not one of them.
One line per remaining character.

Line *i* must omit `name[i]` and contain every **other** letter of the alphabet. Violations:
`forbidden_letter_present` (carrying the offset, so the explorer marks it inline),
`missing_letter`, `wrong_line_count`.

A repeated letter in the name means a repeated constraint, which is correct — Perec's
dedications do that.

### `serial_lipogram`

Params: `unit: Literal["paragraph", "line"] = "paragraph"`, `start: str | None = None`,
plus `DiacriticParams`. Part *i* must omit `alphabet[(first + i) % len(alphabet)]`, where
`first` is the index of `start`.

When `start` is unset it is the alphabet's **first letter**, not a value inferred from the
text. This is where the parallel with `abecedarian` stops: that procedure can read its
starting letter off the first line because its constraint is a presence, whereas a missing
letter is indistinguishable from any other letter a short paragraph happens to lack.
Defaulting to `a` is also Tryphiodorus's arrangement, book 1 omitting alpha.

Violations: `letter_present` (with offset), `wrong_part_count`.

### `pangrammatic_window`

Params: `max_length: int` (required, `ge=26`), plus `DiacriticParams`. No `tokens` — this
is letter-level, and the row's `requires` already reflects that.

Satisfied iff the text contains every letter of the alphabet **and** its letter count is
within `max_length`. Violations: `missing_letter`, `window_too_long`. Metrics: `letters`
(the window length) and `missing`.

Like `pangram`, an empty text is unsatisfied rather than vacuous — it supplies none of what
is required — so this checker builds its `Report` directly rather than going through
`_report`, exactly as `pangram` documents.

### `paragram`

Params: `minimum: int = 1` (how many swap pairs the text must contain), plus
`DiacriticParams`.

Check: over the text's words — folded per `fold_diacritics`, lower-cased, and compared as
letters only — find pairs of equal length differing at exactly one position. A word is not
paired with itself, and each unordered pair counts once. Satisfied iff at least `minimum`
such pairs exist. Violations: `no_paragram` when none is
found. Metrics: `pairs`.

`apply`: change one letter of a word in the text to make another word the lexicon knows,
leaving the rest alone. Gated with `require_capability(pack, WORDS, self.id)` inside
`apply`; the catalogue row's `requires` is unchanged, and a note on the row records that the
generator needs a lexicon the checker does not.

## Error handling

Nothing new. Parameter validation is Pydantic's, surfaced as `InvalidParams` by
`parse_params`; a missing capability raises `MissingCapability` from `require_capability`.
`paragram.apply` is the only new refusal path and reuses the existing one.

## Testing

| Test | What it protects |
|---|---|
| `test_strategies.py` (existing, parametrised) | Each new strategy module's `satisfying()` must check true and `violating()` must check false — the generator half of the loop |
| `test_golden.py` / `test_invariants.py` (existing) | Fixtures record reality; every declared language has a case |
| `test_round_trip.py` (existing) | Covers `paragram.apply` once it exists |
| Per-procedure unit tests | The cases a strategy will not reach: an empty name, a repeated letter in the name, a window exactly at `max_length`, a swap pair at the first and last position |

## Out of scope

- Batches B through G.
- The 8 rows blocked on `lexicon.synonyms` / `antonyms` / `glosses`.
- German for any of these four. Three need only `alphabet` and folding, which German has,
  so `de` is likely correct for them — but declaring a language requires a golden case per
  the invariant, and that belongs with the German coverage sweep.
- Any `apply` beyond `paragram`'s. The other three rows are `kind: restrictive`, and
  ADR 0002 makes a generator meaningless for those.
