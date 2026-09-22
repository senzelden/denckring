# chimera

*Audited 2026-09-21, on the row being added. The 2026-08-31 pass's source text is not preserved in the repository; this pass uses a freshly chosen ordinary text, as the 2026-09-19 and 2026-09-20 files do. Unlike those, the probe had to be run by hand: the row needs three donor texts, which the harness cannot invent, so it sits under "Rows not exercised" in the index for the same reason `slenderizing` and `pasigraphy` do.*

| | |
|---|---|
| kind | `constructive` |
| family | `word` |
| checkability | `source` |
| generator | yes |
| requires | `pos`, `tokens` |
| declares | en |
| runs in | en |

**Verdict: one real defect, found by this probe and fixed in the same change.**

The texts used throughout:

- frame: *The old lighthouse kept a steady light. Sailors watched the dark water and counted every slow turn.*
- `nouns_from`: *A grocer weighed the apples. The market held bread, salt and coffee in wooden crates.*
- `verbs_from`: *She hurried, stumbled and laughed. They carried the ladder, painted the shutters and left.*
- `adjectives_from`: *The morning was bright and cold. A thin mist hung over the green fields, quiet and wide.*

## Checked against an ordinary text

The identity probe every `checkability: source` row in this pass gets — the text handed to the row as its own source — with the three donors above.

- **en** — satisfied: `False`, score `0.2941`, violations: twelve, all `not_from_donor`

Metrics: `tokens` 17, `undecided_words` 1.

**Not a defect, and the same shape as `homosyntaxism`'s identity probe.** A text is not a chimera of itself unless its own content words happen to appear in the donors: the five function-word positions pass, and all twelve content words fail for coming from nowhere the parameters name. The row joins `homosyntaxism` as a source-decidable row that does *not* accept a text as its own source, and for the sharper reason — there, the identity fails the novelty clause; here it fails the donor clause, which is the whole of the definition.

## Generated from it

`apply` was run over seeds 0–19 and its output checked against the frame each time: **20 of 20 satisfied**. Seed 0 gives *The green crates carried a bright market. Coffee carried the green crates and laughed every green market.* — the punctuation, the sentence break and both determiners are the frame's, and `Coffee` shows the inherited capitalisation of ruling 3.

## Findings

**The defect this probe found.** On the first run, seed 0 produced *… Salt carried the green crates …* and its own checker rejected it with `wrong_pos` at `Salt`: the word is a NOUN in the donor and in most positions, and the tagger reads it as PROPN at the head of a sentence. A word's class is a fact about its position, not about the word, so a generator that draws from a pool of the right class and stops there produces text its own checker refuses — which is the `slenderizing` failure exactly, and the property `test_round_trip.py` cannot see here because the row is `PARAMETER_GATED` out of it.

Fixed by making `_produce` re-tag its own output and redraw only the positions whose class did not survive, from the words not yet tried there. `test_chimera.py::test_a_draw_whose_word_class_does_not_survive_is_redrawn` pins it on this very text and seed, so the defect cannot return silently; `test_what_the_generator_makes_satisfies_its_own_checker` is the row's substitute for the round-trip property.

**A measured limitation: `apply` refuses cases it could have filled.** The
redraw loop is greedy coordinate descent — a position that is redrawn keeps
every other position's word, and a word once tried at a position is never tried
there again — so "this position has tried every word in its pool" is not "no
word can stand here", because a word's class depends on the context the other
positions supply. Brute-forced counterexample, with a smaller set of donors than
the ones above:

- frame: *The old lighthouse kept a steady light. Sailors watched the dark water and counted every slow turn.*
- `nouns_from`: *A grocer weighed salt.*
- `verbs_from`: *They carried the ladder, painted the shutters and left.*
- `adjectives_from`: *A thin mist hung over the green fields.*

`apply(seed=0)` raises `NoCandidateWord`: *this greedy search found no NOUN in
nouns_from that still reads as NOUN where 'Sailors' stands …*. But the frame and
these donors are satisfiable — *The thin grocer carried a thin salt. Grocer
carried the thin salt and carried every green grocer.* checks as **satisfied,
score 1.0, no violations**.

How often: a sweep of 400 random (frame, donors) draws built from fifteen
ordinary English sentences produced **21 refusals, of which at least 8 were
false** — a satisfying filling was found by drawing each position uniformly from
its pool, up to 4,000 attempts. That is a floor rather than a rate: a refusal
this sampling could not fill is not thereby genuine, so the true share is 38% or
more.

**Not fixed, and deliberately not.** A complete search over three pools is
exponential, and no row here needs one. What was wrong was the claim, not the
search: the refusal message said no word could stand there, and now says that
this greedy search did not find one and that a filling it cannot reach may still
exist. `test_apply_refuses_when_its_greedy_search_runs_out_at_a_position` pins
both the refusal and the satisfying filling above, so the two cannot drift apart.
Recorded as a known limitation in ADR 0046.

**The seed does less than the schema suggests, and each candidate now says how
much less.** For donors whose surviving NOUN/VERB/ADJ pools are 4/2/1, twenty
seeds over *The quick boy opened the door.* give fourteen distinct outputs and
the adjective is `bright` in all twenty — one candidate survives tagging in that
slot, so `seed` is a documented parameter doing nothing there. `Candidate.metrics`
carries `target_positions` and `forced_positions`, the second counting the
positions of that output where exactly one donor word survives, so a caller can
tell a forced draw from a free one instead of inferring choice from the size of
the donor text. The count is sentence-local: measured on a 680-word frame with
pools of 13/6/8, re-tagging the whole text per trial cost 21.1 s against 0.34 s
for the same count.

**What the row still does not verify**, recorded here as well as in the module docstring so the definition does not overclaim: that a content word was *taken* from the donor rather than arrived at independently — membership is all a text can witness — that the donors were drawn on evenly, or that the result reads as English. Seed 1's *Bread carried the green coffee and carried every cold grocer.* is satisfied and is not prose.
