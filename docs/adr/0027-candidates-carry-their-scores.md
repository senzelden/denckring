# 27. `_produce` returns `Produced`, so a candidate can carry its score

## Context

ADR 0026 made `_produce(text, pack, params) -> list[str]` the single primitive
across all 27 generators, and it was right about the shape a generator needs
when it has several answers. It was not enough for a generator that has an
*opinion* about them.

Two things a generator knows have nowhere to go in a list of strings.

The first is a score. The anagram search ranks its covers by the SCOWL band of
their least common word, so `room dirty` comes ahead of `morty dior` for a
reason a caller can read. A bare string arrives with that reason stripped off,
and the caller is left trusting the order without being told what produced it.

The second is that the search gave up. `Production.truncated` already answers
"was there more?", but the spine derives it from `len(found) > limit` — it can
see that `max_results` capped a result set, and that is the only way it can
ever see anything. A search that abandons its own node budget returns *fewer*
results, not more, so that derivation is false precisely when the honest answer
is true. ADR 0026's design spec named this case in advance as one the surface
did not yet carry.

## Decision

`_produce(text, pack, params) -> Produced`, where

```python
class Produced(BaseModel):
    candidates: list[Candidate]
    truncated: bool = False
```

`Produced.truncated` is the generator's own statement, and `produce()` combines
it with the spine's: `produced.truncated or len(found) > limit`. Both mean the
same thing to a reader — what you were shown is not everything — and only one
of them is visible from the spine.

Still one primitive. A `_produce_scored` overlay implemented by `anagram` alone
would have been a smaller diff, and it is the thing ADR 0026 refused in
writing: two primitives make every consumer ask which a given procedure
implements. Changing the one primitive's type keeps that question unaskable.

`plain(texts)` wraps a list of strings into a `Produced` with no metrics and no
truncation. All twenty-seven generators say exactly that today, in one call
each, rather than spelling out a `Candidate(text=...)` comprehension; `anagram`
is the one expected to stop, once its search has a band to report.

## Consequences

This is churn across 27 files to serve one row's ranking, on a surface
stabilised the day before. Twenty-six of those files gain nothing from the
change and pay for it anyway — two import lines and a `plain(...)` wrapper
each. The `anagram` search that motivates it does not exist yet at the time of
this ADR; the type is being widened ahead of the caller that needs it, which is
the opposite of the order this project usually works in. The argument for doing
it now rather than later is that the alternative is worse, not that the timing
is good.

The alternative considered was a `_produce_scored` overlay, left beside the
existing `_produce` and implemented by `anagram` only. Rejected because it
reintroduces exactly the two-primitive condition ADR 0026 named — one day after
it was named — and because `paragram`'s history is the argument against it: a
generator moved from needing one shape to needing another without its own logic
changing at all, and the same can happen to any of the other twenty-six with
respect to scores.

`Production.texts` is retained as a computed field rather than removed, so
nothing outside had to change *to read* a `Production`: `apply --json`, the MCP
surface and every Python caller still ask for `texts` and still get a list of
strings, and it still appears in `model_dump()`.

That holds for readers only, and the qualifier is the point. `texts` became
read-only, so anything that *built* a `Production` had to move from `texts=` to
`candidates=` — the four constructions in this project's own test suite did,
and any code outside it that constructs one will have to as well. This ADR is
not claiming the change was free; it is claiming the break fell on writers,
who are few and inside the library, rather than on readers, who are many and
outside it.

The retained field is also the honest cost on the reading side — the scores are
invisible to every existing consumer until one asks for `candidates` by name. A
caller reading `texts` today sees a ranking with its reasons removed and no
indication that reasons exist. Nothing prompts them to look.

`Produced` and `Production` are two models with a `truncated` field that mean
related but different things, and a reader will have to keep them apart. The
docstrings say which is which; that is the whole mitigation, and it is a real
cost of not simply reusing `Production` as the primitive's return type — which
was not available, because `Production` carries `procedure` and
`metrics["found"]`, both of which the spine computes and a generator should not
be asked to fill in.

This amends ADR 0026 rather than replacing it. Everything 0026 decided still
stands: one primitive and not two, best first, `apply` as `produce(...).texts[0]`,
the filtering guard, `NOTHING` unwaivable by `allow_identity`, and
`max_results` defaulting to ten. Only the primitive's return type changed, and
the empty check moved from `if not produced` to `if not produced.candidates` —
a `Produced` with no candidates is still `DegenerateOutput(NOTHING)`, on the
same path, before the filter runs.

Out of scope, and unchanged: no generator gains real metrics here. `paragram`
computes a ranking it discards and is the obvious candidate, but its score is
not sourced the way a SCOWL band is, and naming a metric for it is a separate
argument this change does not need to win. It wraps with `plain()` like the
other twenty-six.
