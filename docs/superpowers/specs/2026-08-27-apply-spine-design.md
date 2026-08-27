# denckring — the apply spine

**Date:** 2026-08-27
**Status:** draft
**Scope:** give `apply()` the template method `check()` has, so the generator half can state the truth about itself
**Branch point:** `2eea947` (154 catalogued · 128 implementable · 119 implemented · 119 validated)

## Purpose

A developer tested the MCP surface across two rounds and sent back a list of defects.
Most of them are one absence.

`check()` is a template method on `BaseProcedure`. It resolves the pack, enforces
`meta.requires`, and refuses unknown parameters, so — in its own docstring — "an
individual procedure module cannot forget those checks." `apply()` has none of that.
ADR 0002 made it optional, so it lives off the base class entirely, is discovered by
`getattr`, and all 27 generators hand-roll the same preamble.

Five reported defects are that absence, reached from five directions:

- **`seed` is a reserved hole in all 27 generators.** `apply(self, text, *, lang, seed,
  **params)` binds a caller's `seed=` to the RNG slot before `**params` is reached, so
  `parse_params` never sees it and cannot refuse it. Confirmed across all 27:
  `seed="not-an-int"` is accepted, unvalidated, by every one. The report blamed
  `diastic` for ignoring unknown parameters; the fault is the signature, and it is
  shared.
- **`cut_up` skips `parse_params` entirely** and accepts any parameter at all. It is the
  only one of the 27 that does.
- **`anagram`, `paragram`, `spoonerism` and `word_ladder` hand-roll
  `require_capability`** inside `apply`, each in its own way.
- **Nine rows declare a generative `kind` with no generator behind them**, and report
  `missing: []`, so nothing in the data says so.
- **`anagram` cannot declare the capability its generator uses.** Its own comment
  explains why: `requires` gates `check` too, and declaring `lexicon.words` would break
  a checker that has always worked on core alone. The comment is correct. That is the
  bug — one list serving two halves with different needs, and no field for the second.

The codebase has reached for this twice already and worked around it both times.
`diastic.py:24-32` carries a twelve-line comment documenting the `seed` collision
exactly — "Python binds a keyword matching an explicit parameter name to that parameter
before any of it reaches `**params`, silently" — and renames its field to dodge it.
`cut_up.py:20-21` defines `CutUpApplyParams`, a params model for the apply half, which
nothing ever uses: `params_model()` returns `CutUpParams` and `apply` never validates.
This spec finishes what both of those started.

## The invariant that let it through

The eval harness asserts that `check_text` on the output of `apply_procedure` is
satisfied, for every constructive procedure. The identity passes that trivially. So does
`check_text anagram text:"listen" source:"listen"`.

A generator that returns its input satisfies every gate this project runs — on a project
whose stated thesis is that the validator is the eval. The round-trip property is
necessary and not sufficient, and it has no companion.

## What already exists

- `BaseProcedure.check()`, the template method this mirrors, and `parse_params`, which
  already raises `InvalidParams` naming the accepted set.
- `DiacriticParams`, `RhymeParams`, `SourceParams` — the established pattern of carrying
  an editorial decision as a mixin so it reaches `params_schema()` for free.
- ADR 0009, which decided that a question with no single right answer is a parameter
  rather than a policy, and that the exclusion is enforced by type: `prisoners_constraint`
  has no `fold_diacritics` field, so no caller can ask it to fold.
- `Constructive`, a `runtime_checkable` Protocol the CLI already uses instead of `getattr`.
- `NoCandidateWord`, which `diastic` raises rather than return text its own checker
  rejects — the principle this spec applies at the spine.

## Decisions

1. **`apply` gets a template method, mirroring `check`.** ADR 0002 is amended, not
   reversed: `apply` stays optional, but a procedure that has one inherits a spine.
2. **`seed` becomes an ordinary parameter** on a `SeedParams` mixin, carried only by the
   ten procedures that randomise.
3. **`apply_requires` is a separate field on `Meta`**, because `requires` gates `check`
   and the generator's needs are not the checker's.
4. **`apply` must not return its input, by default.** `check` stays permissive — a text
   genuinely is a permutation of itself, and the letter arithmetic is not wrong.
5. **`kind` is not rewritten for the nine.** It is a claim about the form, and a
   homoconsonantism genuinely can be generated. `describe()` reports the install.

## Components

### 1. The spine

`ConstructiveProcedure(BaseProcedure[P])` in `core/base.py`:

```python
def apply(self, text: str, *, lang: Lang = "en", **params: Any) -> str:
    pack = get_pack(lang)
    for capability in (*self.meta.requires, *self.meta.apply_requires):
        require_capability(pack, capability, self.id)
    parsed = self.parse_apply_params(params)
    return self._guard_degenerate(text, self._apply(text, pack, parsed), parsed)
```

`_apply(self, text, pack, params) -> str` is abstract, matching `_check`'s signature
shape so the two halves read alike.

`apply_params_model()` defaults to `params_model()`. Only procedures with
generator-specific parameters override it, and `cut_up`'s orphaned `CutUpApplyParams`
becomes the first real user of that hook rather than dead code.

The 27 rename `apply` → `_apply` and delete their preambles: the `get_pack` import, the
`parse_params({"source": text, **params})` line, and the four hand-rolled
`require_capability` calls.

### 2. `seed` as a parameter

```python
class SeedParams(BaseModel):
    """Mixed into every procedure that draws at random.

    A field, not a signature keyword: a keyword matching an explicit parameter
    binds there before `**params` is reached, which is why it could never be
    validated. `diastic` documents the collision and renames around it.
    """
    seed: int | None = Field(default=None, description="Fixes the draw, for a repeatable result.")
```

Inherited by the ten that draw: `arca_musarithmica`, `cent_mille_milliards`, `cut_up`,
`denckring`, `ideenwuerfeln`, `llull_figure`, `melting_text`, `poesie_automat`,
`recombination`, `wechselsatz`. The other seventeen do not inherit it, so `seed` cannot
be passed to them at all — ADR 0009's exclusion-by-type, applied again.

`Constructive.apply` loses its explicit `seed`, becoming
`def apply(self, text: str, *, lang: Lang = "en", **params: Any) -> str: ...`.
`cli.py:148` must stop passing `seed=seed` unconditionally, since it currently sends it
to every procedure including the deterministic ones.

This is the one public break. `seed=5` keeps working where the procedure randomises, and
begins erroring — deliberately — where it does not.

### 3. `apply_requires`

`Meta` gains `apply_requires: list[str] = []`. `anagram` declares `lexicon.words`, which
it has always used and never been able to say.

`describe()` gains `apply_missing`, computed the way `missing` already is, so a caller
can tell "this install cannot check it" from "this install cannot generate it".

### 4. Non-degeneracy

`allow_identity: bool = False`, and a new `DegenerateOutput` error raised when the guard
fires. `apply` returning its input is the same defect as `diastic` returning `""` —
handing back text that misrepresents what the procedure did — and gets the same
treatment.

Measured against a single-sentence English input, four of the 27 return their input
today: `boustrophedon`, `cent_mille_milliards`, `recombination`, `wechselsatz`. All four
for the same reason — the input was too small to feed the procedure, and they no-op
rather than say so. `boustrophedon` needs more than one line, `cent_mille_milliards`
needs fourteen, `recombination` needs several sentences.

These are fixed at the cause, not waived with `allow_identity=True`: each raises an
input-adequacy error naming what it needed. The guard is what surfaces them, which is
the argument for the guard.

`wechselsatz` is separately reported as having no template grammar — that its checker
accepts only the source with line breaks removed. This spec fixes only its silent
no-op. The grammar is chapter 2.

### 5. The nine, and the install

The nine rows are `buchstabwechsel`, `definitional_expansion`, `definitional_literature`,
`homoconsonantism`, `homovocalism`, `larding`, `lipogrammatic_translation`, `tmesis`,
`univocalic_translation`. All nine have working checkers; only the metadata is wrong,
and only about this install.

`Description` gains `constructive: bool` and `apply_missing: list[str]`, so
`kind: both, constructive: false` states both true things at once — the form admits
generation, this install has no generator. `Summary` gains `constructive` for the same
reason `runnable` is already there.

Two consequential lines are corrected: `apply_procedure`'s docstring stops claiming
"Sixteen of the procedures are constructive" — it is 27 — and `cli.py:142` stops
printing `"is both and has no apply()"`, which contradicts itself.

## Testing

| Test | Asserts |
|---|---|
| `tests/test_apply_spine.py` | Every registered generator is a `ConstructiveProcedure` and defines `_apply`; no `_apply` body calls `get_pack`, `parse_params` or `require_capability` itself. |
| `tests/test_apply_params.py` | Every generator rejects an unknown parameter naming the accepted set — `cut_up` included. `seed` is type-checked where accepted and refused where the procedure does not randomise. |
| `tests/test_catalogue.py` | `apply_requires` names only capabilities some installed pack declares, matching the existing rule for `requires`. |
| `tests/test_describe.py` | `constructive == isinstance(get(id), Constructive)` for all 119 rows. This is the assertion that stops the nine drifting again. |
| Eval harness | Output differs from input, for every constructive procedure — the companion to the round-trip property, run beside it. |
| Round trip | Unchanged and still green: this spec must not alter what any generator produces, except the four that stop no-opping. |

## Out of scope

Chapter 2 (generator repairs) and chapter 3 (input flexibility) are separate specs.
Named here so the boundary is explicit:

- **The anagram generator's quality.** It searches `pack.nouns()` rather than the word
  lexicon, which is why "astronomer" returns itself and "listen" escapes to "tinsel".
  One line, large payoff, and chapter 2 — the spine has to exist first for
  `apply_requires` to hold `lexicon.words` honestly. A prototype confirmed exhaustive
  multi-word cover search costs 0.2s, so the bottleneck is lexicon quality and ranking,
  not search, exactly as ADR 0015 predicted in writing.
- **`paragram` appending instead of substituting; `spoonerism` truncating past two
  words; `arca_musarithmica` leaking a Python list repr into `text`; `wechselsatz`'s
  missing template grammar; `denckring`'s `combinations` metric being invariant to
  `require_all_rings`** — all confirmed, all chapter 2.
- **Dictionary selectability** for `n_plus_7`, `s_plus_7` and `anagram`. `n_plus_7`'s own
  definition says "in a chosen dictionary" and offers no such choice, which is a
  definition promising more than the implementation delivers — the defect class ADR 0015
  exists to prevent. Chapter 3.
- **Anagram strictness variants** grounded in named authorities, and `lang` as a
  procedure capability rather than a tool-level enum (French pairs validate perfectly
  under the default pack, yet `lang: "fr"` hard-fails a check needing no language data).
  Chapter 3.
- **N+7's part-of-speech tolerance.** Reported as a false-positive bug; it is the
  documented behaviour of `displacement_report`, which accepts an unchanged noun because
  no word list can rule out its being a verb there, and reports `ambiguous_words`. The
  behaviour is right and the verdict is too confident. A question about what `satisfied`
  should mean when the checker could not tell — chapter 3, if at all.
- **`wechselsatz`'s `drawable` filter.** `_apply` splits a frame on whitespace; `_check`
  reads the produced line back with `word_spans`, a different tokenizer — so an
  alternative like `Nacht-Tag`, which the German pack reads as two words, or `3`, could
  be drawn and then rejected by the checker meant to verify it. The filter closes that
  the narrow way, by simply never drawing such an alternative, which means it silently
  never comes up for the reader — the same silent no-op this chapter otherwise abolishes,
  one level down, and deliberately not fixed here. The real fix is a frame contract
  stating what an alternative may be, refused at the door, which is the template-grammar
  work of chapter 2.
- **`tests/test_round_trip.py`'s `max_examples`, raised 200 → 1000.** `fold_in` and
  `mathews_algorithm` need two blank-line-separated paragraphs, which text drawn
  uniformly from the test alphabet offers about once in three hundred examples; widening
  the alphabet to reach `cent_mille_milliards`, `wechselsatz` and `recombination` spent
  the margin that used to reach them by luck at 200. The suite is not flaky —
  `derandomize=True` fixes the sequence — but it is one shared sequence: if it ever
  shifts, every row this close to the floor fails for everyone at once, not
  intermittently for some. The durable fix is a paragraph-shaped Hypothesis strategy
  that reaches these rows by construction rather than by drawing enough examples to get
  lucky; chapter 3.
