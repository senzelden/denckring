# homosyntaxism

*Audited 2026-09-20, on the row being added (ADR 0045). The 2026-08-31 pass's source text is not preserved in the repository; this pass uses a freshly chosen ordinary text, as the 2026-09-19 files do.*

| | |
|---|---|
| kind | `both` |
| family | `syntax` |
| checkability | `source` |
| generator | no |
| requires | `pos`, `tokens` |
| declares | en |
| runs in | en |

**Verdict: clean, and the identity probe is informative.**

## Checked against an ordinary text

Probed as every `checkability: source` row in this pass is: the text handed to the row as its own source.

- **en** — satisfied: `False`, score `0.5161`, violations: `repeated_word`, `repeated_word`, `repeated_word`, `repeated_word` (15 total)

Metrics: `tokens` 31, `undecided_words` 2.

**Not a defect, and worth contrasting with `homoconsonantism`**, which the same probe scores `1.0`. A text trivially preserves its own consonant skeleton, so the identity case satisfies that row. It does *not* satisfy this one: every tag matches — there is not a single `wrong_pos` in the fifteen — but every open-class word is the source's own, so the novelty half of the rule rejects all fifteen.

That is the clearest available evidence that the "new words" ruling is load-bearing rather than decorative. Under the weaker reading of the definition, which checks part of speech alone, this row would call every text a homosyntaxism of itself.

## Generated from it

No generator. `kind: both`, but ADR 0002 makes `apply` optional and `homoconsonantism` is the precedent: choosing new words of the same class to make new sense is invention, not a mechanical transformation. Recorded in the module docstring.

## Findings

Nothing anomalous. The row's real overclaim is not visible in this probe and is recorded in its catalogue `notes:` instead: the comparison is a positional UPOS sequence, so it verifies neither that the text is a *rewriting* of the source nor that sentence boundaries correspond. Word salad carrying the right tags in the right order satisfies it.
