# 5. Continuous `score`, not a boolean

## Context

The primary consumer of a `Report` is a retry loop: a model generates a text, the
checker rejects it, and the violations are fed back for another attempt.

## Decision

`score` is a float in `[0, 1]`, monotone in violation count, and `satisfied` is exactly
`score == 1.0` for every procedure without exception.

## Consequences

A caller can tell whether a text missed by one word or by fifty, which is what makes an
automatic retry loop converge instead of thrashing. The strict equivalence between
`satisfied` and `score == 1.0` gives one invariant that can be property-tested across
the entire registry, so a procedure cannot quietly disagree with the convention.
An empty text is vacuously satisfied for restriction procedures and unsatisfied at
score 0.0 for `pangram`; each procedure records this in its golden fixtures.
