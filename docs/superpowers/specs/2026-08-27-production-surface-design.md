# denckring — the production surface

**Date:** 2026-08-27
**Status:** draft
**Scope:** a second output shape for `apply` — one text for the string surface, all of them for the structured one
**Branch point:** `d88b2b9` (154 catalogued · 128 implementable · 119 implemented · 119 validated)

## Purpose

`apply` returns one string. For most procedures that is the whole truth: N+7 walks the
dictionary and there is one answer; a cut-up under a fixed seed has one shuffle. For the
procedures with many valid answers it is a lie of omission — the generator finds several
and the return type can carry one.

`paragram` is the proof, in code that already shipped. Its `_apply` walks every word,
every position and every letter of the source, keeps whatever the lexicon calls a word,
scores each candidate `(pronounced, is_noun, length)`, and then returns `best_swapped` and
discards the rest. The ranking exists. The search exists. The surface throws the results
away.

`anagram` will be the same case, harder: `dormitory` has thirty-two exact two-word covers
and `dirty room` is one of them. A caller who asks for an anagram and is handed exactly one
has no way to know that.

## The constraint that shapes everything

This project's eval invariant is that `check` accepts what `apply` produced. Measured:

```
check anagram  text:"silent"                  source:"listen"  -> satisfied, 1.0
check anagram  text:"silent\ntinsel\nenlist"  source:"listen"  -> NOT satisfied, 0.333
                                                surplus_letter ee, ii, ll
```

So the string surface cannot carry more than one result. Newline-joining three anagrams
gives `check` a text with three times the letters, and the property that has guarded every
generator in this package through two migrations becomes conditional on procedure kind.

That decides the shape rather than being worked around: **`apply` returns exactly one text,
and the many live somewhere else.** The invariant is not merely preserved but strengthened
— see Testing.

## What already exists

- `ConstructiveProcedure` (ADR 0025), whose `apply` resolves the pack, enforces
  `requires` + `apply_requires`, validates parameters, and guards the result.
- `Report`, the structured return of `check`: `procedure`, the findings, `metrics`. The
  model for this design's counterpart.
- `ApplyParams`, carrying `allow_identity`, inherited by all 27 generators.
- `_guard_degenerate`, which refuses output identical to the input or empty.
- `denckring describe --json`, the existing convention for a structured CLI output.
- `apply_procedure`'s MCP return is already a dict — `{"text": ...}` — so it has room.

## Decisions

1. **`_produce(...) -> list[str]` is the single primitive**, ordered best first. Not an
   optional second method beside `_apply`: two mechanisms for one job is the shape this
   codebase has twice had to remove (`cut_up`'s orphaned `CutUpApplyParams`, the unused
   `apply_params_model` default), and every consumer downstream would have to ask which
   one a given procedure implements.
2. **`apply` returns `texts[0]`.** The string surface stays exactly one text.
3. **`Production` is `Report`'s counterpart** and copies its shape rather than inventing
   one.
4. **The degeneracy guard filters rather than refuses.** It drops degenerate candidates
   and raises only when none survive.
5. **`max_results` defaults to 10**, so a procedure with many answers gives many without
   the caller opting in.
6. **The anagram search is not in this chapter.** This builds the surface; chapter 3 fills
   it.

## Components

### 1. The primitive

```python
@abstractmethod
def _produce(self, text: str, pack: LanguagePack, params: A) -> list[str]:
    """Procedure-specific generation, best first.

    A list even where there is one answer: `apply` returns `texts[0]`, so the
    order is the contract, and a generator that ranks its candidates puts its
    winner at the front.
    """
```

The 27 rename `_apply` → `_produce` and wrap their return. Twenty-six are a one-line
change; `paragram` is the exception and is the pilot below.

`apply` becomes:

```python
def apply(self, text: str, *, lang: Lang = "en", **params: Any) -> str:
    return self.produce(text, lang=lang, **params).texts[0]
```

and `produce` carries the preamble `apply` used to:

```python
def produce(self, text: str, *, lang: Lang = "en", **params: Any) -> Production:
    pack = get_pack(lang)
    for capability in (*self.meta.requires, *self.meta.apply_requires):
        require_capability(pack, capability, self.id)
    parsed = self.parse_apply_params(text, params)
    found = self._guard_degenerate(text, self._produce(text, pack, parsed), parsed)
    # `getattr`, and falling back to 1 rather than 10, for the reason
    # `_guard_degenerate` reads `allow_identity` the same way: a generator may
    # declare an apply-params model that does not inherit `ApplyParams`, and the
    # safe reading of a missing limit is the old single-result behaviour.
    limit = getattr(parsed, "max_results", 1)
    return Production(
        procedure=self.id,
        texts=found[:limit],
        truncated=len(found) > limit,
        metrics={"found": float(len(found))},
    )
```

Trimming happens here, in one place, rather than being trusted from 27 generators.

### 2. `Production`

In `core/protocol.py`, beside `Report`:

```python
class Production(BaseModel):
    """What a generator turned out. `Report`'s counterpart for the other half."""

    procedure: str
    #: Best first. Never empty — a generator with nothing to return raises.
    texts: list[str]
    #: Whether more were found than `max_results` allowed through.
    truncated: bool = False
    metrics: dict[str, float] = Field(default_factory=dict)
```

`texts` is never empty: a generator that can produce nothing raises `NoCandidateWord`,
`InputTooShort` or `DegenerateOutput` as it does today, so an empty list would be a fourth
way of saying a failure that already has three honest names.

### 3. The guard filters

```python
def _guard_degenerate(self, text: str, produced: list[str], params: A) -> list[str]:
    if getattr(params, "allow_identity", False):
        return produced
    kept = [t for t in produced if not self._is_degenerate(text, t)]
    if not kept:
        raise DegenerateOutput(self.id)
    return kept
```

For the twenty-six single-result generators this is byte-identical to current behaviour:
one candidate, degenerate, nothing survives, raise. For a multi-result generator it is the
point of the change — `anagram` finding `astronomer` among its covers drops that one and
returns the others rather than failing the whole call. The `ignores_input` exemption is
unchanged.

### 4. `max_results`

On `ApplyParams`, beside `allow_identity`, so all 27 inherit it:

```python
max_results: int = Field(
    default=10, ge=1,
    description="How many results to return at most. `apply` always returns the first.",
)
```

Ten rather than one because a caller asking a procedure with many answers for an anagram
expects more than one, and rather than unbounded because `dormitory` alone has thirty-two
two-word covers before any deeper search. `truncated` is what keeps that honest.

### 5. The three surfaces

**Python.** `denckring/__init__.py` gains both:

```python
def apply(procedure_id: str, text: str, *, lang: Lang = "en", **params: Any) -> str: ...
def produce(procedure_id: str, text: str, *, lang: Lang = "en", **params: Any) -> Production: ...
```

`apply` is new at the top level. The package has exported `check` since the beginning and
never exported `apply`, so every Python caller has had to reach through
`registry.get(...)`. Adding `produce` without fixing that would leave the asymmetry in
place while adding to it.

Both raise `UnknownProcedure` for an unknown id, and both raise `NotConstructive` for a
procedure with no generator. That is a new `DenckringError` subclass — the nineteenth, so
`tests/test_error_codes.py`'s inventory pin and the spec's code table both move — carrying
the code `not_constructive`, which the MCP tool already emits today as a hand-built dict
literal. Making it a real error removes that branch: `apply_procedure` catches
`DenckringError` and converts it already, so the tool's output for a non-constructive
procedure is unchanged while the `getattr`-and-branch disappears.

**CLI.** `denckring apply <id>` unchanged. `--json` emits the `Production`, matching
`describe --json`.

**MCP.** `apply_procedure` returns `{"text": ..., "texts": [...], "truncated": ...}`.
Additive: `text` keeps its current meaning and value, so no existing caller breaks. This
is the surface the developer feedback that began this work arrived through, and the one
where the omission was least visible.

### 6. `paragram`, the pilot

Its `_apply` currently tracks `best_score`/`best_word`/`best_swapped` through the loop and
returns one insertion. `_produce` collects `(score, offset, word, swapped)` for every
candidate, sorts by score descending, and renders each into its own output text.

No new lexicon, no new ranking, no new search: `CandidateScore` is already
`(pronounced, is_noun, len)` and already totally ordered. The change is to stop discarding.
This is what makes the pilot worth having — it demonstrates the surface on results the
package was already computing.

## Testing

| Test | Asserts |
|---|---|
| `tests/test_production.py` | `produce` returns best-first, `texts[0] == apply(...)` for every generator, `texts` is never empty, `truncated` is true exactly when more were found than `max_results`. |
| `tests/test_apply_spine.py` | Every generator defines `_produce` and none defines `_apply`; `max_results` is rejected below 1. |
| `tests/test_paragram.py` | The pilot returns more than one result on a text with several candidates, ordered by the score it already computes, and `texts[0]` equals what `apply` returned before this change. |
| Round trip | **Strengthened**: every text in a `Production` satisfies `check`, where today only `apply`'s single result does. Same for non-degeneracy — every text must differ from the input. |
| `tests/test_mcp_tools.py` | `apply_procedure`'s `text` is unchanged for every generator, and `texts[0] == text`. |
| Regression | No generator's `apply` output moves. The 26 single-result generators must return exactly what they return today. |

## Out of scope

- **The anagram multi-cover search.** Chapter 3, with its own spec. At the end of *this*
  chapter `apply anagram "astronomer"` still raises `DegenerateOutput`, because its
  generator still searches `pack.nouns()` and finds only the identity. The surface will be
  ready for the search; the search is separate work resting on a lexicon decision.
  `docs/expansion_ideas/anagram-generation-research.md` carries the measurements.
- **Ranking across procedures.** `Production.texts` is ordered by whatever the generator
  says. Only `paragram` has a real ranking; nothing here invents one for the others.
- **A per-candidate structure.** `texts` is a list of strings, not of objects carrying
  scores or provenance. When a generator has a score worth exposing — an anagram's SCOWL
  band, say — that is the moment to widen it, not before.
- **A generator's own truncation signal.** The spine computes `truncated` from what
  `_produce` returned. A generator with an internal time or solution budget — anagram, in
  chapter 3 — will know it stopped early in a way the spine cannot see, and will need to
  say so. Named here so chapter 3 does not have to rediscover it.
- **`lang` as a reserved keyword.** Still named in `produce`'s signature, as ADR 0025
  records, and still the surviving instance of the hazard that made `seed` unvalidatable.
  Unchanged by this chapter.
- **Derandomizing the round trip.** `tests/test_round_trip.py::test_apply_output_satisfies_check`
  is not derandomized, so a latent generator/checker disagreement surfaces only when
  Hypothesis happens to draw the input that exposes it, rather than reliably. Two such
  disagreements were found this chapter — `cent_mille_milliards` and `recombination`, one
  per task, each blocking until fixed. A controller sweep over all 27 constructive rows
  (400 randomised draws each, Hypothesis's example database disabled) found no further
  ones, but that is weak evidence rather than a clean bill: both known cases were rare
  draws that had previously surfaced through Hypothesis's *stored* counterexamples, which
  the sweep's disabled database does not have and cannot replay. A deliberate exhaustive
  sweep, or derandomizing the property so a failure is at least reproducible rather than
  intermittent, is worth doing before leaning on this property's silence again.
