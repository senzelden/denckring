# 39. Mutation testing is a worklist, not a gate

## Context

The suite is 4,772 tests and CI enforces a 97% coverage floor. Coverage says a
line ran. It does not say a test would have noticed the line being *wrong*, and
for a library of checkers that is the question that matters: an off-by-one in a
comparison, a boundary read as `<` instead of `<=`, a normalisation applied on
one side of an equality, all change a verdict while every statement still
executes.

This repository has evidence that the gap is real rather than theoretical. The
defects found in the MCP sweep of 2026-09-02 were in the *best-covered* rows, at
parameter values no fixture supplied. And on 2026-09-07 a checker was found
returning opposite verdicts for the same word in NFC and NFD — 532 golden cases
and a 97% floor, and the reason none of them caught it is that every fixture is
NFC.

## Decision

**D1. mutmut, configured, and deliberately outside the four-command gate.** A
full run over the catalogue is hours. A gate that slow is a gate people stop
running, and CLAUDE.md's four commands are meant to be run before every commit.
The score is measured on purpose and recorded, not asserted on every push.

**D2. `source_paths` is the whole package; a run is narrowed by naming mutants.**
`mutmut` copies the mutated tree into `mutants/` and runs pytest from there, so
naming a single file produces a partial package that shadows the installed one
and every import of a sibling fails with `ModuleNotFoundError`. Narrow with
`uv run mutmut run "denckring.core.text.*"` instead.

**D3. Surviving mutants are a worklist requiring judgement, never a failure
count.** This is not a hedge; it was established by the first run.

`core/text.py` produced 8 survivors. The most promising —
`line.rstrip("\r\n")` becoming `line.rstrip(None)` in `paragraph_spans`, which
strips all trailing whitespace rather than only line endings — looked like a
plain test gap, and reading the function's first twenty lines supported that.

It is an **equivalent mutant**. `paragraph_spans` calls `block.strip()` on the
group before returning it, so whatever `rstrip` leaves is removed downstream.
Verified by applying the mutation to the real file and comparing both versions
over 9,757 distinct generated inputs: **zero behavioural differences.**

The first reading of it was wrong because it was made against a paraphrase of
the function rather than the function. That is this repository's own standing
lesson about plausible figures, arriving from a new direction: a survivor is a
question, and answering it means running the mutation against the real code.

**D4. No score is published yet.** The first run was cut short by its own
timeout, so the 8 survivors and 6 no-tests entries are a partial reading of one
file, not a baseline for anything. A number stated now would be quoted later.
Widening to the rest of `core/` and then to `procedures/` is the next step, and
each widening records its own measured cost.

## Consequences

**Two blockers had to be fixed before it ran at all, and one was a real defect
in this repository rather than in the tool.**

`mutmut` leaves 5.6 MB in `mutants/`. It is untracked, and `uv build` reads the
working tree rather than the index, so **312 of its files landed in the source
distribution** and pushed it from 0.9 MB to 1.2 MB. `test_the_sdist_stays_small`
is what noticed. This is the fourth time in this repository that a new untracked
directory has had to be told apart from an absent one, after `superpowers/`,
`stage_mockups/` and `feedback/`. `mutants/` is now in `.gitignore` and in the
sdist exclusions, and the exclusion was verified with a 6.1 MB `mutants/` present
rather than after deleting it.

The second was the test selection. The suite contains tests that build a source
distribution, render the documentation site, and import from `scripts/` — none of
which survive being copied into `mutants/`, and none of which say anything about
whether a mutant in `text.py` was caught.

**The cost is judgement per survivor.** Equivalent mutants are not a defect in
the tool; they are inherent, and they mean the output can never be read as a
defect count. That is the whole content of D3.

**The score is not comparable across runs that change the test selection**, so
the selection is config rather than a habit, and a widening is a decision with a
recorded reason.
