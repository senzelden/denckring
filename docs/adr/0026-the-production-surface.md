# 26. `_produce -> list[str]` is the primitive; `apply` returns its first result

## Context

`check anagram text:"silent\ntinsel\nenlist" source:"listen"` scores 0.333, with
`surplus_letter` violations against everything past the first line. `check` reads
whatever `apply` returns as one text, so three anagrams joined by newlines are a
text with three times the letters — the checker is correct to reject it. The
string surface cannot carry several results without making this project's
central round-trip property conditional on which procedure produced the text.
`paragram` already had the shape this forces: `_apply` walked every word, every
position and every letter of the source, scored each candidate `(pronounced,
is_noun, length)`, and then kept the winner and discarded the other hundred.

## Decision

`_produce(text, pack, params) -> list[str]`, best first, replaces `_apply` as
the one abstract method a generator implements. One primitive rather than two —
a `str` shape beside a `list[str]` shape would make every consumer ask which a
given procedure implements, and `paragram`'s history shows a generator can move
from needing one to needing the other without its own logic changing at all.

`produce()` is the template method `apply()` used to be: it resolves the pack,
enforces both capability lists, validates parameters, and filters output that
misrepresents what ran, returning a `Production`. `apply()` is now defined on
top of it as `produce(...).texts[0]` — the one-text surface for a caller who
wants the best answer and not the search behind it, rather than a second path
through the pack, the capabilities and the guard that could drift from the
first.

The non-degeneracy guard now filters rather than refusing wholesale: each
candidate in the list is judged on its own, and what survives is returned.
For a single-result generator this changes nothing — one candidate judged
degenerate is exactly the whole list judged degenerate, so the guard still
raises. For a search like `paragram`'s it means a candidate that happens to
equal the input is dropped and the others are kept, rather than the entire
call failing because one candidate among many was degenerate.

An empty list from `_produce` is a separate case from a list every candidate
of which is filtered out, and it is checked first, before the filter runs at
all: `_produce` returning `[]` is not a candidate the procedure judged and
rejected, it is no candidate offered in the first place, and it raises
`DegenerateOutput` with `observed=NOTHING`. Unlike the other two shapes
(`IDENTICAL`, `EMPTY`), `NOTHING` is not waivable by `allow_identity` — that
flag exists for a caller who wants the degenerate-but-real result a procedure
found, and an empty list is not a result for it to want.

`ApplyParams.max_results` defaults to ten rather than one, because a caller
asking a procedure with many valid answers expects more than one of them, and
rather than unbounded because `dormitory` alone has thirty-two exact two-word
covers before any deeper search. `Production.truncated` is what keeps a capped
search from reading as an exhaustive one; without it there is no way to tell
"this is everything" from "this is the first ten of something larger."

`NotConstructive` replaces a dict literal the MCP server built by hand for
exactly this case, so asking to generate with a checker-only procedure raises
a `DenckringError` that can be caught with the others instead of returning a
value shaped like one.

## Consequences

`Production.texts` carries `min_length=1`: "never empty" was documented on the
field and enforced by nothing, and `apply`'s `texts[0]` would have raised a
bare `IndexError` on a `Production` built with an empty list. The field
constraint turns that into a validation error naming the field. It is not,
in practice, reachable through `produce()`: the empty-list case is caught
before a `Production` is ever constructed (see above), so the pydantic
`ValidationError` this constraint could otherwise raise — which is not a
`DenckringError` and would escape the MCP server's handler uncaught — has no
path to it from any generator that goes through the template method. It would
only fire if code outside `produce()` built a `Production` directly with an
empty list, which nothing in this package does.

`apply` now builds a whole `Production` to return one string. For every
generator but `paragram` that Production holds exactly the one text it always
held, so the cost is the object's construction, not repeated work — except for
`paragram` itself, which now scores and renders every candidate on every call
where it previously stopped at the first one it decided to keep. Both costs
are small against the search each generator already runs, and are stated here
rather than left for a profiler to find. On `"The cat is great."`, `paragram`
finds 101 candidate swaps and returns the best 10, `truncated` true; before
this chapter it found the same 101 and returned 1.

Two pre-existing generator bugs surfaced while writing the wider round-trip
test this chapter needed — every text in a `Production`, not only `apply`'s
first, must satisfy `check`. Both are the same class of defect: a generator
producing text its own checker would reject.

`cent_mille_milliards` silently dropped a sheet line offering no alternatives,
which drew one fewer line than the sheet has positions — exactly the shape its
own `missing_line` violation exists to catch. `apply('a|a\n|')` returned one
line where `check` required two. It now refuses such a sheet up front with
`InputTooShort`, naming the empty position.

`recombination` shuffled an unterminated trailing fragment into the draw along
with complete sentences. `" ".join` then merged it with whatever ended up as
its new neighbour — `'a'` next to a lone `'.'` becomes `'a .'` — and that
merged string re-splits into a different multiset than the one shuffled, which
is exactly what `check` compares against. It now pins the tail out of the
shuffle and permutes only the terminated parts.

Both bugs were made reachable by the previous chapter widening the round-trip
test's input alphabet to include `|` and `.`, and both surfaced only
intermittently, because `tests/test_round_trip.py::test_apply_output_satisfies_check`
runs `@settings(max_examples=50, deadline=None)` with no `derandomize=True` —
unlike its sibling three lines above, which does. That is worth stating
plainly rather than as an incidental detail: strengthening a property this
chapter needed found two real defects that a narrower property had been
passing over for as long as the wider input alphabet existed. That is the
argument for the strengthening, not merely its side effect, and it is also
the argument that the property is still not being run reliably — see the
design spec's Out of scope, carried forward.

The MCP `message` for `apply_procedure` on a non-constructive procedure
changed, from the hand-built `f"{procedure!r} only checks; it has no
generator."` to `NotConstructive`'s own wording, which additionally points a
caller at `constructive` in `describe_procedure`. `code` (`not_constructive`)
and `detail` (`{"procedure_id": ...}`) are unchanged, so a caller matching on
either is unaffected; one matching on `message` text is not.

Out of scope, and unchanged by this chapter: the anagram multi-cover search
(chapter 3), per-candidate scores or provenance on `Production.texts`, a
generator-side truncation signal for a search with its own internal budget,
and `lang` remaining a reserved signature keyword on `produce`.
