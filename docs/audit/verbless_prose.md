# verbless_prose

*Audited 2026-09-20, on the row being added (ADR 0045). The 2026-08-31 pass's source text is not preserved in the repository; this pass uses a freshly chosen ordinary text, as the 2026-09-19 files do.*

| | |
|---|---|
| kind | `restrictive` |
| family | `syntax` |
| checkability | `self` |
| generator | no |
| requires | `pos`, `tokens` |
| declares | en |
| runs in | en |

**Verdict: clean.**

## Checked against an ordinary text

- **en** — satisfied: `False`, score `0.8065`, violations: `finite_verb`, `finite_verb`, `finite_verb`, `finite_verb` (6 total)

Metrics: `words` 31, `undecided_words` 2.

An ordinary paragraph is built on finite verbs, so rejecting it is the row working rather than a finding. The `undecided_words` count is the honest part of the report: two of the thirty-one tokens are forms the tagger never saw in training, and any violation on one of those carries a note saying so.

## Generated from it

No generator. `kind: restrictive`, and ADR 0002 makes `apply` optional; choosing what to write without a finite verb is the writing, not a transformation of the input.

## Findings

Nothing anomalous in this probe. The row's real limits are not visible here and are recorded where they are measurable instead — in `src/denckring/eval/fixtures/golden/verbless_prose.yaml`, which carries three `satisfied: false` cases that are **false positives on genuinely verbless Dickens**, and in ADR 0045's Consequences. This probe uses ordinary prose, which the row rejects for the right reason; a probe cannot show the failure mode that matters for a restrictive row, which is the opposite one.
