# 25. `apply` gets the spine `check` has

## Context

ADR 0002 made `apply` optional and left it off `BaseProcedure`. `check` is a
template method that resolves the pack, enforces `meta.requires` and refuses
unknown parameters, so — in its own docstring — "an individual procedure module
cannot forget those checks". `apply` had none of that, and all 27 generators
hand-rolled the same preamble.

Each forgot something different. `cut_up` never validated parameters at all.
Four hand-rolled `require_capability`. `anagram` could not declare the lexicon
its generator uses, because `requires` gates `check` too. And `seed`, named
explicitly in the `Constructive` signature, bound before `**params` on every
call, so no params model ever saw it and all 27 accepted `seed="not-an-int"`.

The codebase had reached for this twice. `diastic` carries a twelve-line comment
documenting the `seed` collision and renames its field to dodge it; `cut_up`
carried `CutUpApplyParams`, a params model for the apply half that nothing used.

Separately, the eval harness asserted `check(apply(text))` is satisfied for every
constructive procedure — a property the identity passes trivially. A generator
returning its input satisfied every gate the project ran.

## Decision

`ConstructiveProcedure` carries a concrete `apply()` delegating to an abstract
`_apply()`, mirroring `check()`/`_check()`. It resolves the pack, enforces
`meta.requires` and `meta.apply_requires`, validates parameters, and refuses
output identical to its input.

`seed` becomes a field on `SeedParams`, carried only by the ten procedures that
draw. `allow_identity` is a field on `ApplyParams`, carried by all of them.
`source`, where a generator's params model has it, is supplied by `apply` from
the text it was called with — a caller who also passes `source` names two
texts for one argument, and `parse_apply_params` raises `InvalidParams` rather
than choosing one silently.

`lang` stays a reserved keyword on the shared `apply` signature, the same way
`seed` used to be on `Constructive.apply`: no field on `ApplyParams`, or on
anything it is mixed into, may be named `lang`, because Python still binds a
keyword matching an explicit signature parameter before any of it reaches
`**params`. Closing the collision for `seed` did not close the mechanism that
causes it — only that one name.

ADR 0002 is amended, not reversed: `apply` is still optional, and a procedure
without one is still registered on its checker alone. What changes is that a
procedure which *has* one inherits the spine rather than rebuilding it.

## Consequences

`seed` is typed, reaches a caller who never touches Python, and cannot be passed
to a procedure that does not draw — the exclusion-by-type ADR 0009 gives `fold_diacritics`,
applied again. This is a break: `apply(text, seed=5)` on a deterministic
procedure used to be accepted and ignored, and now raises.

Where it reaches that caller is `describe()`'s `apply_params`, not
`params_schema()`. Those are two schemas, not one: `params_schema()` is the
checker's model, and `seed`, `allow_identity` and a generator's own fields
belong to `apply_params_model()`, which no non-Python surface exposed at all
until `Description.apply_params` carried it to `denckring describe` and MCP's
`describe_procedure`. Merging them would have been the other option and is
wrong: `source` is a checker parameter that `apply` supplies for itself and
refuses from a caller, so one schema could not describe both calls.

`apply_requires` lets `anagram` declare `lexicon.words` without gating a checker
that has always run on core alone, which is what makes `missing` honest for the
generator half.

The non-degeneracy guard surfaced five raise sites across four generators that
returned their input when it could not feed them — `boustrophedon`,
`cent_mille_milliards`, `recombination`, and `wechselsatz` twice over, once for
a frame offering no choice at all and once for a frame whose alternatives the
tokenizer cannot read back as single words. They now raise `InputTooShort`
naming what they needed — as do `spoonerism` and `ideenwuerfeln`, which were
refusing for the identical reason under `NoCandidateWord` and `MalformedCorpus`
respectively, so the code a caller retries on depended on which procedure they
had called. `NoCandidateWord` keeps its narrower meaning (enough units, none of
them suitable) and `MalformedCorpus` keeps `corpus.parse`'s (unreadable, not
merely small). Finding them is the argument for the guard: each had
been silently no-opping, and the round-trip property called it a pass.

The guard refuses an empty result from non-empty input under the same error and
the same `allow_identity`, because it is the same defect: `_report` scores an
empty text 1.0 — vacuously satisfied — so `melting_text.apply("hello", seed=0)`
returning `""` was a satisfied report on a text nobody wrote, and
`every_nth_word` with a stride longer than its input could do it too. A caller
cannot act differently on "identical to the input" and "nothing at all", so they
share a code; `detail()["observed"]` says which was seen.

The second `wechselsatz` case is a guard around a gap the guard did not close.
`_apply` splits its frame on whitespace; `_check` reads the produced line back
with `word_spans`, a different tokenizer. An alternative like `Nacht-Tag`,
which the German pack reads as two words, could be drawn, written out, and then
rejected by the checker that supposedly verifies it. `wechselsatz` now filters
such alternatives out of the draw rather than offering them — which means a
frame that offers only ones like it now raises `InputTooShort` for want of a
choice, and a frame that offers `Nacht-Tag` alongside ordinary words simply
never draws it, silently, for the reader. That is the same class of defect this
chapter exists to end, one level down in the same procedure, and it is
deliberately not fixed here: the actual fix is a frame contract stating what an
alternative may be, refused at the door, which is the template-grammar work of
chapter 2. The filter is the narrow, honest stopgap until then.

`kind` is untouched. It is a claim about the form, and nine rows are honestly
`both` with honestly no generator here; `describe` reports `constructive`
alongside it so both statements can be true at once.
