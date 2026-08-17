# denckring — the syllabic batch

**Date:** 2026-08-17
**Status:** draft
**Scope:** batch B of 7 — every unbuilt row whose constraint is measured in syllables

## Purpose

Implement `dactylic_hexameter`, `elegiac_couplet`, `sapphic_stanza`, `alcaic_stanza`,
`double_dactyl`, `renga` and `haibun`, taking `implemented` from 79 to 86.

These are the seven unbuilt rows that need `syllables` and not `phonemes` for rhyme. Four
are classical metres and three are stanza shapes. They are specified together at the
maintainer's direction; the size is noted under [Sequencing](#sequencing) and handled by
the plan rather than by splitting the spec.

The batch also repairs a defect in the existing prosody machinery that makes the metrical
rows uncheckable as things stand — see [The out-of-dictionary defect](#the-out-of-dictionary-defect).
That repair is the reason to do this batch before batch C's eleven rhymed forms, which
inherit the same fault.

## What already exists

More than batch A had. The batch is mostly composition, not invention.

| Component | What it gives us |
|---|---|
| `core/prosody.py` — `metre_violations(line, pack, pattern, offset)` | Scans one line against a stress pattern. `?` means "either", and violations name the *word*, not the syllable index, because the word is what a writer can act on. |
| `core/prosody.py` — `MAX_COMBINATIONS = 4096` | A cap so a pathological line cannot hang the checker. Above it, only each word's first pronunciation is tried. |
| `procedures/rhyme_scheme.py` — `form_report(...)` | Composes rhyme scheme, metre and refrains, "so a sonnet is a rhyme scheme plus a metre and says so". |
| `procedures/syllable_count.py` — `line_syllables`, `pattern_result` | Per-line syllable totals against an expected pattern, already emitting `lines` and `estimated_words`. |
| `haiku`, `tanka`, `cinquain`, `senryu`, `alexandrine`, `hendecasyllable` | Six built syllabic procedures, all going through `pattern_result`. |

`hendecasyllable` sets the house convention for honesty about scope. Its docstring reads:
*"Checks the syllable measure only, not the caesura or the stress pattern."* Every
procedure in this batch states what it does not check, in the same voice.

## Decisions

| Decision | Rationale |
|---|---|
| The four classical metres are checked by **stress**, not by syllable count alone | Classical quantity is vowel length, which English does not have; English verse substitutes stress, and has since the Renaissance. Counting syllables only would make `dactylic_hexameter` accept any prose of the right length — measured: a flat prose line of comparable length fits **0 of the 32** valid hexameter patterns under stress, but is indistinguishable from verse under a syllable count. A count-only hexameter is `syllable_count` under a second name, which is the argument that gave `pangrammatic_window` its required `max_length`. |
| Each such row declares **`phonemes`**, not `stress` | Established by running: `pack.stress_patterns(word)` is phoneme-backed and raises against `PHONEMES`. The rows currently declare `[tokens, syllables]`. `requires` gates `check`, so an undeclared capability is a latent crash — the same discipline that removed three stale `tokens` entries in batch A, applied in the other direction. |
| `?` is extended to mean classical **anceps** on the pattern side | The FREE marker looks like anceps but is not: established by running, `_fits("1", "?")` is `False`. Today `?` means only "this *word* is a free monosyllable, so it takes whatever beat the line needs" — a property of the word, never of the pattern. Sapphics and alcaics both have anceps positions, so `_fits` gains one clause making a `?` in the *pattern* accept any mark. After that the scholarly patterns transcribe directly. |
| Out-of-dictionary words degrade rather than raise | See below. This is a repair, not a preference. |
| `renga` and `haibun` ship checking their structural skeleton only | Both definitions contain clauses no text checker can reach — renga's collaborative composition, haibun's verse "condensing rather than continuing". The alternative was deferring them; shipping an honest partial check matches `hendecasyllable`, and a row that is catalogued but unbuilt teaches a reader nothing. Each states the gap in its docstring and in a catalogue note. |
| `double_dactyl` does not check the rhyme | Its catalogue definition does not mention rhyme, and checking it would pull `phonemes` into a row that otherwise needs only syllables. Recorded as a note on the row rather than silently omitted. |
| No `apply` anywhere in this batch | All seven rows are `kind: restrictive`, and ADR 0002 makes a generator meaningless for those. |

## The out-of-dictionary defect

The metrical rows cannot be built on the machinery as it stands. Longfellow's own
hexameter fails, and not because it is unmetrical:

```
>>> check("dactylic_hexameter", "This is the forest primeval, the murmuring pines and the hemlocks")
MissingCapability: Procedure "<word 'hemlocks'>" requires the capability 'phonemes',
                   which the 'en' language pack does not provide.
```

The pack *does* provide `phonemes`. `hemlocks` is simply absent from CMUdict, and
`_forms_or_raise` in `denckring-en-data` signals that by raising `MissingCapability` —
a capability error for a vocabulary gap. One ordinary English noun aborts the whole
check.

This is wrong twice over: the exception names a condition that is not true, and an
unknown word is a normal event in real verse rather than an exceptional one. The
syllable path already handles it correctly — `pack.syllable_count(word)` returns
`(count, exact)` and falls back to a heuristic, and `line_syllables` propagates the
estimate count because *"the estimate count is what keeps a heuristic pack honest —
every syllabic report carries it, and installing `denckring[en]` drives it to zero."*

**The fix mirrors that contract in the stress path.** A new `word_stress(word, pack)`
in `core/prosody.py` returns `(patterns, exact)`. For a word CMUdict knows, it returns
the real patterns and `True`. For one it does not, it returns a single all-`?` pattern
of the heuristic syllable length and `False` — the word is scanned for length but
constrains no beat. `metre_violations` gains a third return value, the estimated-word
count, and every metrical report in this batch carries it as `estimated_words`, the
metric name the syllabic procedures already use.

This changes `metre_violations`'s signature, which `form_report` and `rhyme_scheme` call.
Both are updated in the same task; no other caller exists.

A caller wanting the strict behaviour still has it: `estimated_words > 0` says the scan
leaned on the heuristic, exactly as it does for syllables today.

## Components

Each procedure owes the same four files as every other, and the existing parametrised
invariants enforce all four:

| File | Responsibility |
|---|---|
| `src/denckring/procedures/<id>.py` | The checker, registered with `@register`. One module per procedure (ADR 0007). |
| `tests/strategies/<id>.py` | `satisfying()` and `violating()`, both returning `CaseStrategy`. |
| `src/denckring/eval/fixtures/golden/<id>.yaml` | At least one satisfying and one violating case, recording what the checker actually returns. |
| `tests/test_<id>.py` | The cases a generator will not reach. |

Plus four changes to `core/prosody.py`, all shared:

- **`_fits` gains anceps.** One clause, so a `?` in the *pattern* accepts any mark, where
  today only a `?` in the *word* is honoured. Verified absent: `_fits("1", "?")` is
  currently `False`, so a pattern written with anceps rejects every fixed-stress word at
  that position. Both `sapphic_stanza` and `alcaic_stanza` depend on this. The existing
  word-side meaning is unchanged, and `rhyme_scheme`'s patterns contain no `?`, so no
  built procedure changes behaviour.
- **`word_stress(word, pack) -> tuple[list[str], bool]`** — the out-of-dictionary repair above.
- **`stanza_violations(text, pack, patterns, *, allow=None)`** — a metre check taking **one
  pattern per line** rather than one pattern for every line, because sapphics and alcaics
  change shape from line to line. `patterns[i]` applies to line *i*; a line count mismatch
  reports `wrong_line_count`.
- **`feet(units, count)`** and pattern-set matching — a foot may substitute, so a metre is a
  *set* of acceptable patterns rather than one. `feet([("100", "11")] * 4 + [("100",)] + [("11", "10")])`
  expands to the 32 patterns of dactylic hexameter. A line satisfies if it fits **any** of
  them; the reported violation comes from the closest-fitting candidate, so the writer is
  told about one scansion rather than thirty-two.

The set is bounded by construction — hexameter is 2⁴ × 2 = 32 — and the existing
`MAX_COMBINATIONS` cap still guards the per-line pronunciation search inside each attempt.

## The seven procedures

Stress notation: `1` stressed, `0` unstressed, `?` anceps. Patterns are the English
accentual reading of the classical measure, which is what the docstrings say.

### `dactylic_hexameter`

Params: none.

Six feet. Feet 1–4 are a dactyl `100` or a spondee `11`; foot 5 is a dactyl; foot 6 is a
spondee `11` or a trochee `10`. Thirty-two patterns, 13–17 syllables. The fifth foot is
fixed as a dactyl because a spondaic fifth is rare enough that accepting it would cost
more in false positives than it buys — noted on the row.

Violations: `wrong_stress`, `wrong_line_length` (both from the shared scanner).
Metrics: `lines`, `estimated_words`.

### `elegiac_couplet`

Params: none.

Line 1 is a dactylic hexameter, exactly as above. Line 2 is the so-called pentameter: two
hemiepes, `(100|11) (100|11) 1` then `100 100 1`. The first half admits spondaic
substitution and the second does not — that asymmetry is the form, and a checker that
allowed substitution throughout would accept lines no elegist wrote.

Lines are checked in pairs, so a text of four lines is two couplets. An odd line count
reports `wrong_line_count`. The definition's "the pair forming one unit of sense" is not
checked and the docstring says so.

Violations: `wrong_stress`, `wrong_line_length`, `wrong_line_count`.

### `sapphic_stanza`

Params: none.

Four lines, `11 / 11 / 11 / 5`. Lines 1–3 are the sapphic hendecasyllable
`101?100101?` — trochee, trochee-with-anceps, dactyl, trochee, trochee-with-anceps.
Line 4 is the adonic `1001?`. Syllable counts verified against the patterns: 11 and 5.

Violations: `wrong_stress`, `wrong_line_length`, `wrong_line_count`.

### `alcaic_stanza`

Params: none.

Four lines, `11 / 11 / 9 / 10`. Lines 1–2 are alcaic hendecasyllables `?1011100101`;
line 3 is the enneasyllable `?101?1011`; line 4 the decasyllable `100100101?`.

These three patterns were wrong in the first draft of this spec — 10, 8 and 9 syllables
against the 11, 9 and 10 the form requires. They are given here as literal strings, and
the plan's first step for this row is to assert their lengths in a test before anything
scans against them, because a metre spec that miscounts its own line is worse than none.

Violations: as `sapphic_stanza`.

### `double_dactyl`

Params: none.

Eight lines in two quatrains. Lines 1–3 and 5–7 are double dactyls, `100100`, six
syllables. Lines 4 and 8 are `100 1`, four syllables. Line 1 is a nonsense phrase, line 2
names a person, and one line of the second quatrain is a single double-dactylic word.

Of those three, only the last is mechanically checkable: it is a line of exactly one token
whose syllable count is six. That is checked, as `no_double_dactylic_word`. The nonsense
phrase and the naming are not checked — nonsense is a lexicon question the row does not
declare, and naming a person needs an entity recogniser this project does not have. The
rhyme between lines 4 and 8 is not checked either, per the decision above. All four
omissions are stated in the docstring and on the row.

Violations: `wrong_stress`, `wrong_line_length`, `wrong_line_count`,
`no_double_dactylic_word`.

### `renga`

Params: `links: int | None = None` (how many stanzas to require; unset means any number,
provided the alternation holds).

A chain of alternating stanzas separated by blank lines: a three-line `5-7-5` then a
two-line `7-7`, repeating. The chain must begin with a three-line stanza and must contain
at least two stanzas — one stanza is a hokku, not a renga.

Uses the new `paragraph_spans` from batch A to find stanzas, then `pattern_result` per
stanza.

That renga is *composed collaboratively*, and that each link joins only to its neighbour
rather than to the whole, are the definition's substance and neither is a property of the
text. Both are named in the docstring as unchecked.

Violations: `wrong_syllable_count`, `wrong_stanza_shape`, `too_few_links`.
Metrics: `stanzas`, `estimated_words`.

### `haibun`

Params: none.

Prose paragraphs and haiku alternating, separated by blank lines, beginning with prose and
ending with a haiku. A haiku block is three lines of `5-7-5`; a prose block is anything
else, and is checked only for *being* prose — one or more lines that do not parse as
`5-7-5`. There must be at least one of each.

Whether the verse condenses the passage before it rather than continuing it is the whole
point of the form and is not checkable; the docstring says so plainly, and says that a
haibun failing it will still be reported satisfied.

Violations: `wrong_syllable_count`, `missing_haiku`, `missing_prose`, `wrong_alternation`.
Metrics: `blocks`, `estimated_words`.

## Error handling

Nothing new. Parameter validation is Pydantic's, surfaced as `InvalidParams` by
`parse_params`. `MissingCapability` keeps its real meaning — a pack that genuinely lacks
`phonemes` — and stops being raised for an unknown word, which is the repair above.

## Testing

| Test | What it protects |
|---|---|
| `test_strategies.py` (existing, parametrised) | `satisfying()` checks true, `violating()` checks false, per row |
| `test_golden.py` / `test_invariants.py` (existing) | Fixtures record reality; every declared language has a case |
| Per-procedure unit tests | An empty text, a text one line short, a line whose only fault is one misplaced stress, and — for every metrical row — a real line of the form from the literature |
| `tests/test_prosody.py` | The three new helpers directly: `word_stress` on a known and an unknown word, `stanza_violations` on a line-count mismatch, and `feet` expanding to exactly 32 hexameter patterns |

Two testing rules carried from batch A, where they caught real defects:

- **No vacuous verdicts.** An empty text must be unsatisfied *and* carry violations. A
  report that is unsatisfied while listing nothing is a defect; it shipped twice in this
  project before being caught.
- **Strategies must reach every violation rule they can.** A `violating()` that only ever
  produces one rule is a weakness to report, and every draw must be genuinely rejected.

Each metrical row's golden fixture carries at least one line from the literature, so the
fixtures record that the checker accepts real verse and not only constructed examples.
Longfellow's hexameter is the specific case that motivated the out-of-dictionary repair
and belongs in `dactylic_hexameter`'s fixture for that reason.

## Sequencing

One spec, but the work has a hard internal order: the prosody repair and the two new
helpers come first, because four of the seven rows cannot be written against the current
machinery at all. The plan divides accordingly —

1. `core/prosody.py`: the `_fits` anceps clause, `word_stress`, the `metre_violations`
   signature change, and the two callers updated
2. `stanza_violations` and `feet`
3. `dactylic_hexameter`, then `elegiac_couplet` (which reuses its pattern set)
4. `sapphic_stanza`, `alcaic_stanza`
5. `double_dactyl`
6. `renga`, `haibun`

Steps 3–6 are independent of each other once 1–2 land.

This is the largest batch this process has run — seven rows against batch A's four, plus
three pieces of shared machinery. The risk is not correctness, which the review loop
catches, but that a defect in step 1 propagates into six later rows before anyone sees it.
The plan therefore gates steps 3–6 behind a review of steps 1–2 rather than dispatching
them together.

## Out of scope

- Batch C's eleven rhymed forms, though they inherit the prosody repair.
- German or any language beyond `en`. All seven rows declare `languages: [en]`, and
  CMUdict is English-only; these are the rows a German pronouncing dictionary would
  unlock, which is a distribution question, not a procedure one.
- `test_invariants.py`'s two properties silently skipping procedures whose no-param
  `check` raises. Six of these seven take no required parameters and so are covered, but
  the underlying gap is batch-independent and belongs in its own change.
- Any `apply`. All seven rows are restrictive.
