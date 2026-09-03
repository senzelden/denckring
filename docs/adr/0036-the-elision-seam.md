# 36. A leading proclitic is not a noun, and it is not a rhyme word either

## Context

`s_plus_7` and `n_plus_7` walk a source text word by word, looking each one up in
`pack.noun_index` and comparing the candidate against the displacement the checker
computes. Measured on the branch point, this inverted the verdict rather than merely
missing it:

| Call — `offset: 3`, `ambiguous_nouns: "strict"` | Result | Should be |
|---|---|---|
| `l'îlot` from source `l'île` — the correct S+7 | `satisfied: false`, `changed_a_non_noun` | satisfied |
| `l'île` from source `l'île` — the source retyped unchanged | `satisfied: true`, score 1.0 | flagged; `strict` exists for exactly this |

Bare `île` worked (`île` → `îlot` under the same offset), so one word gave two verdicts
depending on a preceding `l'`. `d'`, `qu'` and the typographic `’` behaved the same. Both
rows share the defect: `s_plus_7` delegates entirely to `n_plus_7`'s `displace` and
`displacement_report`.

**The cause is `noun_index`'s own lookup, not the tokeniser.** `word_spans` keeps an
apostrophe-bearing token whole on purpose — 94 real French words carry an internal
apostrophe of their own (`aujourd'hui`, `prud'homme`), and splitting every apostrophe
unconditionally would misread those. `denckring_fr_data`'s syllable and phoneme lookups
(`_table_entry`) already learned this: try the token whole against the table first, and
only on a miss fall back past the last apostrophe. `noun_index` never got that fallback,
so `noun_index("l'île")` returned `None` even though `noun_index("île")` succeeds
(index 44740). This is chapter 6's trap 1 again — a lookup normalising differently from
the way its table is keyed.

**Unlike the syllable table, no noun carries an internal apostrophe** — checked against
the shipped 44,746-entry list, zero matches. So for this row specifically, an apostrophe
in a word handed to `noun_index` is *always* an elision boundary, never part of the noun,
and the try-whole-first step the syllable path needs is not needed here: splitting is
always safe.

## Decision

`n_plus_7.py` gains `split_elision(word) -> (prefix, tail)`, splitting at the last of `'`
or `’`. `displace` and `displacement_report` both work on the tail for every lookup,
comparison and displacement, and treat the prefix as a separate, inert unit that must
match exactly between source and candidate — a new `changed_proclitic` violation, distinct
from `changed_a_non_noun`, because the fault is the prefix, not the noun.

**The prefix is reattached exactly as written, never re-elided against the displaced
noun's own initial sound.** `l'île` displaces to `l'îlot` correctly because both `île` and
`îlot` start with a vowel. A displacement landing on a consonant-initial noun keeps the
same written proclitic — `l'aïoli` displaced by one entry becomes `l'b`, which no French
speaker would write by hand. Choosing correctly between `l'`/`le`/`la` (and `d'`/`de`,
`qu'`/`que`) needs the displaced noun's grammatical gender and its initial sound class
(vowel, mute h, aspirated h), none of which the noun list carries. Building that is its
own decision, not folded into this one; `tests/test_elision_seam.py` pins the literal
behaviour so it is a known limitation rather than a silent one.

Language-blind by construction: no English or German word carries an apostrophe, so
`split_elision` is a no-op there and the fix costs nothing outside French.

**`split_elision` lives in `core/text.py`, not `n_plus_7.py`, because a second caller
needed it the same day.** `identical_rhyme` (`core/prosody.py`) compares each rhyme
scheme line's final word against another's to decide whether they are the same word —
`l'amour` and `amour` are, and the comparison read them as different, so a minimal pair
differing only by a leading `l'` matched by `does_rhyme` and by neither `identical_rhyme`
nor `does_not_rhyme`, scoring 1.0 where the bare pair correctly failed.
`hemeling`/`limerick`/`rhyme_scheme` all share `core/prosody.scheme_violations`, so one
fix reaches all three. Sharper than a generic gap: `hemeling` publishes
`allow_identical` as *"Permit a word to rhyme with itself, as French rime riche does"* —
the row explicitly models French self-rhyme, and the dial was bypassed by the commonest
orthographic fact in the language. This caller does not need the try-whole-first step
either, for a different reason than `noun_index`'s: it only ever compares one split
segment against another split the same way, so even a genuine apostrophe-word compared
with itself still comes out correctly identical.

**Also fixed the same day: `kangaroo_word`'s own lookup, a different root cause under the
same MCP sweep finding.** `synonym: "école"` failed `not_a_word` under default
`fold_diacritics`, because `is_word` is not fold-aware — French keeps its accents on
purpose (ADR 0009) — and `kangaroo_word` folded the synonym before asking it, so a
diacritic-folded `ecole` could never match the table's `école`. Not an elision bug and
`split_elision` is not involved: every other `is_word` caller in this codebase
(`paragram`, `word_ladder`, `semordnilap`) already checks membership on the word as
written and folds only for its own scattering/order comparison, so the fix is `is_word`
on `params.synonym` rather than on the pre-folded copy — bringing the one row that
disagreed into line with the rest, not a new decision.

## Consequences

**The generator inherits the same literal-reattachment limit as the checker.**
`apply("s_plus_7", "l'aïoli", offset=1)` returns `l'b`, and its own checker accepts it —
consistent, not obviously grammatical. This is the same shape of cost this project has
taken before: `ambiguous_nouns`'s default, `monoconsonantal`'s French `y`, and it is
recorded rather than hidden.

**`changed_proclitic` is a new rule name.** Any caller pattern-matching on
`displacement_report`'s violation rules for these two procedures gains one more value.

**Both related sub-findings from the same MCP sweep finding are fixed alongside this
one**, recorded above rather than as open items: `kangaroo_word`'s accent-folding bug and
`identical_rhyme`'s elision blindness on `hemeling`, `limerick` and `rhyme_scheme`.

## Alternatives considered

**Splitting every apostrophe-bearing token at the tokeniser.** Rejected: it would misread
the 94 genuine apostrophe words the tokeniser was deliberately built to keep whole, and
every other row that tokenises French text — not only these two — would inherit the
change untested.

**Reconstructing correct elision on the output** (choosing `l'`/`le`/`la` from the
displaced noun's gender and initial sound). Rejected for this decision: the noun list
carries no gender, so it would need a second data source and a design of its own, for a
cost this fix does not need to pay to close the sweep's finding — the finding was a
verdict *inversion*, not a request for grammatical polish.
