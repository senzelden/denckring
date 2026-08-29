# denckring — the anagram spine

**Date:** 2026-08-29
**Status:** draft
**Scope:** the lexicon the anagram search needs, the surface that carries its ranking, and the test net both land on
**Branch point:** `9386816` (154 catalogued · 128 implementable · 119 implemented · 119 validated · 26 not mechanically checkable)

This is **Spec A of chapter 3**. Spec B — dictionary selectability for `n_plus_7` and
`s_plus_7`, anagram strictness variants, `lang` as a procedure capability, and N+7's
`satisfied` verdict — is separate work resting on what lands here, and gets its own spec.

## Purpose

`apply anagram "astronomer"` raises `DegenerateOutput`. So does `dormitory`. `listen`
escapes to `tinsel`, which is the only reason the row has ever looked like it worked.

The reported cause — the generator searches `pack.nouns()`, so a source word that is
itself a noun is the longest cover of its own letters — is true and is one line. It is
not the whole defect, and fixing only that line would ship something worse than the
current failure.

## The constraint that shapes everything

Search is free. Ranking is the entire problem, and ranking is a property of the lexicon.

Measured against the shipped `known_words()` oracle, exhaustive two-word cover
enumeration, on this branch:

```
dormitory    170 words fit    65 covers    first returned: "morty dior"
astronomer   992 words fit  2355 covers    first returned: "manos retro"
listen       155 words fit   280 covers    first returned: "ts neil"
```

Each under 0.5s. `room dirty` is in `dormitory`'s 65. So is `morty dior`, and the oracle
cannot tell them apart: `dority`, `romito`, `stinel` and `sutphen` are all words to it.
ADR 0015 wrote this down before the caller existed — the membership oracle is
"deliberately broad, and broad in a way callers inherit", answering *could this be a word*
rather than *is this a word*. The anagram generator is the caller that inherits it
hardest.

Restricting to nouns is not the escape. `dirty` and `silent` are not nouns; filtering to
nouns removes the good answers and leaves `dory timor` and `dirt roomy`.

**What is needed is a commonness-graded, part-of-speech-agnostic word list.** That is a
resource this project does not ship, and acquiring it is the chapter.

## A defect found while confirming the above

The catalogue row declares `apply_requires: [lexicon.words]`. The docstring at
`anagram.py:95` explains that choice at length, and explains it well — `lexicon.words` on
`apply_requires` rather than `requires`, because ADR 0002 makes `apply` the optional half.
The reasoning is right. The code underneath calls `pack.nouns()`.

So the row declares a capability it never uses, uses one it never declares, and carries a
comment asserting otherwise. By this project's house style a comment that has become false
is a defect rather than a nit. It is fixed in W2, not separately, because the capability it
should declare does not exist yet.

## What already exists, and was built for this

Chapter 2 laid groundwork on purpose, and the spec should not re-derive it:

- `ApplyParams.max_results` already defaults to 10, and its docstring already cites
  `dormitory`'s thirty-two two-word covers as the reason it is not 1.
- `Production.truncated` already exists, and the spine already computes it from what
  `_produce` returned.
- `_produce(...) -> list[str]` is already the single primitive across all 27 generators,
  ordered best-first, with order as the contract.

Three of the four things the search needs are already here. The fourth — a per-candidate
score — is W1.

## Decisions

**The lexicon is SCOWL, and it folds into `denckring-en-data`.** Not a fourth
distribution. ADR 0013's quarantine rationale is about *incompatible* licences; it
reserves a place for "a future copyleft lexicon". SCOWL is MIT-like and compatible with
what already ships there, so a fourth distribution would buy no quarantine and would add a
third package to the release lockstep ADR 0013 already admits as a cost. `LICENSE-SCOWL`
sits beside `LICENSE-CMUDICT`, which is exactly the pattern that ADR established.

**SCOWL carries UKACD's verbatim-notice obligation, and we discharge it rather than dodge
it.** `docs/expansion_ideas/anagram-generation-research.md` lists UKACD's "text of this
document must be included verbatim" as friction that choosing SCOWL avoids. It does not:
SCOWL is derived from UKACD among other sources and inherits the term. This is cheap to
satisfy — ship SCOWL's `Copyright` file verbatim — but the research doc is wrong on the
point and the correction belongs in the record.

**`lexicon.graded_words` is a new capability, not a reuse of `lexicon.words`.** ADR 0015's
rule is one capability per question the lexicon is asked. "Is this a word" and "give me
the words, with how common each is" are different questions with different answers, and a
pack can honestly have the first and not the second. German is exactly that pack:
Wikidata's word list is flat, so `denckring-de-data` will not claim this capability. The
anagram row is already `languages: [en]`, so nothing regresses.

**A node budget, not `timeout_seconds`.** The prior art uses a wall-clock timeout, and
that is the honest primitive for a service. It is the wrong one here: the row is
`deterministic: true`, and a wall-clock budget makes the result set depend on the machine,
so CI and a laptop would disagree about what the procedure produces. A deterministic node
budget gives the identical "I stopped early" signal, is reproducible, and is testable. The
cost is that the budget no longer bounds wall-clock time on a pathological input, and
`MAX_LETTERS` remains the only thing that does.

**`max_size` defaults to 60, and that number is sourced rather than invented.** SCOWL's
own documentation calls 60 "the largest size that I am fairly confident does not contain
any misspellings or invalid words". This is the `fold_diacritics` shape from ADR 0009: an
editorial decision carried as a parameter, with a named authority behind its default,
rather than a threshold chosen because it looked about right.

## Components

### W0. The test net, first

Both blind spots recorded in the chapter-2 spec's out-of-scope section, closed before the
search that will rely on them is written.

`tests/test_round_trip.py::test_apply_output_satisfies_check` is not derandomized, so a
generator/checker disagreement surfaces only when Hypothesis happens to draw the input
that exposes it. All four properties call `_apply_args(procedure_id, 0)`, pinning `seed=0`
on every example, in every property, on every run — so the ten drawing rows are exercised
at exactly one draw per input text.

W0 derandomizes the property and widens `_apply_args` to draw the seed rather than pin it.

**This is expected to fail, and that is the point.** Widening `TEXT`'s alphabet surfaced
two latent disagreements, one per chapter-2 task (`cent_mille_milliards`,
`recombination`), each blocking until fixed. Widening the seed is the same kind of
widening on a different axis and should be budgeted as such: the workstream is not "make
the change", it is "make the change and fix what it finds". Any generator this uncovers
gets fixed in W0, not deferred.

The paragraph-shaped Hypothesis strategy is **not** in W0. It is named in the chapter-2
out-of-scope section alongside these two, but it addresses a different problem —
`max_examples=1000` reaching `fold_in` and `mathews_algorithm` by luck rather than by
construction — and it is not a prerequisite for the search. It moves to Spec B.

### W1. `Production` carries candidates

ADR 0026 made `_produce(...) -> list[str]` the single primitive across all 27 generators,
and rejected two primitives in writing: "two would make every consumer ask which a given
procedure implements."

That rules out the cheap version of this workstream. Leaving `_produce` alone and adding a
`_produce_scored` overlay that only `anagram` implements would reintroduce precisely the
condition ADR 0026 named, one day after it was decided.

So the single primitive changes shape:

```python
class Candidate(BaseModel):
    text: str
    metrics: dict[str, float] = Field(default_factory=dict)

class Produced(BaseModel):
    candidates: list[Candidate]
    truncated: bool = False

def _produce(self, text: str, pack: LanguagePack, params: A) -> Produced: ...
```

**A structure and not a bare `list[Candidate]`, because this spec asks for two
things a list cannot both carry.** W3 requires the generator to report truncation
the spine cannot see: the spine derives `truncated` from `len(found) > limit`, and
node-budget exhaustion means the search found *fewer* results, not more, so that
derivation can never express it. Returning a list would have forced a second
channel for the flag — an instance attribute, a re-entrant hook, or a sentinel key
in the first candidate's metrics — and every one of those is the two-primitive
condition ADR 0026 rejected, wearing a different hat. One structure carries both,
and `plain()` keeps the twenty-six unscored generators to a single call.

`Production.candidates` is the new field. `Production.texts` survives as a derived
property, so `apply()` stays `produce(...).texts[0]`, and the MCP surface and `apply
--json` keep working unchanged. The guard against output that misrepresents what ran, and
`truncated`, both continue to operate on the same list.

Twenty-six generators change by wrapping their return value. One — `anagram`, in W3 —
changes meaningfully. `paragram` already computes a ranking it currently discards and is
the obvious second candidate for real metrics, but it is **not** converted here: it has a
score, not a *sourced* score, and inventing a metric name for it is a different argument.
W1 wraps it like the other twenty-five.

This needs an ADR amending 0026, in the register 0026 itself used.

**The cost, admitted:** this is churn across 27 files to serve one row's ranking, on a
surface stabilised the day before. The alternative was a contradiction in the ADR record,
which is worse, but this is not free and the ADR should say so rather than present the
change as obviously correct.

### W2. SCOWL into `denckring-en-data`

`packages/denckring-de-data/scripts/build_lexicon.py` is the model — a build step that
turns an upstream release into a shipped artefact, run by hand, with the output vendored.
ADR 0013 requires that neither installation nor use touches the network.

Produces `data/graded_words.txt.gz`: word and size band, filtered to purely alphabetic
entries. The restriction matches the one ADR 0015 already applies to `nouns()`, and for a
related reason — a cover made of `cat's-paw` cannot survive the tokenizer that reads the
result back.

The pack gains:

```python
def graded_words(self) -> Mapping[str, int]: ...   # word -> SCOWL size band
```

A `Mapping`, not a `Sequence`. `nouns()` is a sequence because N+7 indexes into it
positionally; nothing indexes into this. The search needs band *lookup* and builds its own
letter-keyed index, so a mapping is the shape that matches the question.

Also in W2, because they are the same edit: the catalogue row's `apply_requires` becomes
`lexicon.graded_words`, and the false docstring at `anagram.py:95` is corrected to
describe the capability the code actually uses.

Licensing artefacts: `LICENSE-SCOWL` reproducing SCOWL's `Copyright` file verbatim
(which discharges the inherited UKACD term), `NOTICE` updated, and the `pyproject.toml`
licence expression widened. **The upstream licence text is confirmed against the shipped
release before the data is committed, not against this spec** — the research doc's licence
readings are explicitly not legal advice, and this spec's are not either.

One documented discrepancy to resolve while building: the research doc records band 95 as
archaic. Upstream v2 describes 85 as archaic and does not ship 95 at all; 95 was v1's
"insane" tier. Verify against the release actually vendored and record which it is.

### W3. The anagram search

Replace the greedy walk with recursive multi-cover search over `graded_words()`, keyed by
sorted letters — the canonical index, and the algorithm every piece of prior art agrees
on. Depth-bounded, band-filtered, node-budgeted.

Parameters, on `AnagramApplyParams`:

| parameter | default | why |
|---|---|---|
| `max_words` | 3 | bounds recursion; `dormitory`'s famous answer needs 2 |
| `min_word_length` | 2 | the direct answer to orphan letters passing as words |
| `max_size` | 60 | SCOWL's own recommended cutoff (see Decisions) |
| `max_nodes` | 200_000 | deterministic truncation signal (see Decisions) |

`max_results` already exists and is not re-declared.

`max_nodes`'s default is the one number here with no external authority behind it, and the
spec should not pretend otherwise. It is set by measurement: pick the smallest round value
that leaves the exhaustive depth-3 search over `astronomer` — the worst measured input, 992
fitting words — untruncated, then state the measured headroom in the comment. If the
implementer's measurement disagrees with 200,000, the measurement wins and the spec is
wrong.

Ranking, best first:

1. fewest words
2. lowest maximum band across the cover's words
3. alphabetical

Key 2 needs saying carefully, because SCOWL's numbering runs backwards from intuition:
**larger numbers mean less common**. So a cover is ranked by its *least* common word — its
maximum band — and lower is better. `room dirty` beats `morty dior` because its worst word
is commoner than the other's worst word, not because its average is better.

Keys 1 and 3 are Dewdney's ordering from *The Armchair Universe* (1988), "Anagrams and
Pangrams", which `ars-magna` follows; key 2 is what this project adds. **Verify the chapter
and pagination against the book before the catalogue cites it** — provenance rules apply,
and a citation carried across from a research note is not a verified one. If the book
cannot be checked, the row cites nothing rather than citing on trust.

Each candidate carries that maximum band in `Candidate.metrics`, which is the concrete use
W1 exists for.

The generator reports its own truncation when the node budget is exhausted, through
`Produced.truncated` — the case the chapter-2 spec named in advance, and the reason W1's
primitive returns a structure rather than a list. `Production.truncated` is then true when
either the budget stopped the search or `max_results` capped its results, which are
different events with the same honest meaning: what you were shown is not everything.

`MAX_LETTERS = 60` stays. Its comment, which justifies the cap in terms of the greedy
walk being replaced, does not, and is rewritten to justify the cap that will actually
exist.

## Testing

The gate is the four commands plus `eval --all` and `status`, as always.

Specific to this spec:

- W0's changes must be *observed to fail before they pass* on at least the seed axis. A
  seed-widening that goes green on the first run has probably not widened anything, and
  the workstream should not be believed until it has either found something or been shown
  to actually vary the draw.
- `test_the_named_coverage_gap_is_the_whole_coverage_gap` guards W1: `anagram` gaining
  required parameters would move it into the coverage gap silently. Every new parameter
  above has a default, so it must not — and that test is what proves it.
- The row-level assertion that makes this chapter true: `apply anagram "dormitory"`
  returns `room dirty` among its results, and ranks it above `morty dior`. That is the
  regression test for the whole chapter, and it is worth writing first.
- `apply anagram "astronomer"` no longer raises `DegenerateOutput`.
- Determinism: identical inputs and parameters produce an identical result set, including
  when the node budget truncates.

## Out of scope

- **Spelling variants (A/B/Z/C/D).** SCOWL codes American, British-ise, British-ize,
  Canadian and Australian, and the research doc is right that this is a second genuine
  editorial axis. The anagram search does not need it, and building an axis before a
  caller asks the question is the shape of mistake ADR 0015 exists to prevent. The build
  step should record which variant set it selected so the choice is at least legible.
- **German.** The anagram row is `languages: [en]`. The Wikidata/Leipzig join described in
  the research doc is a build step of its own and is not required by anything here.
- **`paragram` exposing its ranking.** It computes one and discards it, and W1 makes
  exposing it possible. It is not sourced the way a SCOWL band is, and naming a metric for
  it is an argument this spec does not need to win.
- **The paragraph-shaped Hypothesis strategy.** Moved to Spec B; see W0.
- **Everything in Spec B** — dictionary selectability for `n_plus_7` and `s_plus_7`,
  anagram strictness variants grounded in named authorities, `lang` as a procedure
  capability, N+7's `satisfied` verdict when the checker could not tell.
- **A wall-clock budget.** Rejected in Decisions, and worth naming here too: if a
  pathological input ever does make the search slow in a way `MAX_LETTERS` does not
  prevent, this decision is where to look, and reversing it means accepting that
  `deterministic: true` becomes false.
