# 46. The chimera's three donors are not three sources

## Context

ADR 0045 built two of the three `pos` rows and declined the third in writing:
`chimera` "is `kind: constructive` over *three* source texts, which is a
genuinely new parameter shape and deserves its own record rather than being
carried in on the back of this one". Issue #22 says the same thing earlier and
more plainly — the row is blocked because "`SourceParams` carries one source and
chimera needs three". This is the record ADR 0045 asked for, and its first
finding is that both statements are false.

`SourceParams` does not mean *a text this procedure reads*. It means **the text
this one was made from** — `homoconsonantism`'s original, `n_plus_7`'s original,
`homosyntaxism`'s original. A chimera is made from its **frame**: the text whose
word order, function words and punctuation survive the operation. The frame is
the source, `SourceParams` already carries it, and `parse_apply_params` already
supplies it from `apply`'s own text argument, so a caller who passes `source` to
`apply` is refused as they are for every other source row.

The three donors are not sources in that sense at all. Nothing of a donor's
structure reaches the output; what reaches the output is words. A donor is
lexical stock — a word list that happens to be written as a text, and read as
one only because the tagger needs sentences to tag. Two texts made from the same
frame with different donors are the same operation on the same original; two
texts made from different frames are not.

So the question the issue framed — how does one procedure take three sources? —
does not arise. The real question is what to call three word lists beside an
inherited source, and that is an ordinary parameter question.

## Decision

`ChimeraParams(SourceParams)` adds three plain string fields: `nouns_from`,
`verbs_from`, `adjectives_from`. **`core/base.py` is untouched.** No mixin, no
`SourcesParams`, no change to the spine, and nothing about this row is reflected
in a shared shape.

Two alternatives were considered and rejected.

**An ordered `sources: list[str]`.** Position would encode which donor fills
which word class, and `params_schema()` — the surface every non-Python caller
reads, and the only documentation an MCP or CLI caller gets — cannot say that.
A caller would have to learn from prose that element 1 is the verbs, and a
caller who got the order wrong would get a plausible wrong answer rather than an
error. Role-keyed names say it in the schema, and the test
`test_a_content_word_from_the_wrong_donor_is_a_violation` pins the distinction:
`river` is a noun sitting in `verbs_from`, and a checker treating the donors as
one bag of words accepts the text that one rejects.

**A `SourcesParams` mixin in `core/base.py`.** It would generalise a shape with
exactly one caller, and it would generalise the wrong thing — a list of
*sources* is not what this row has, per the whole of the Context above. Naming
it in core would make the false framing permanent and invite the next row to
inherit it. `source_compare`'s docstring already records the house rule: extract
from real callers rather than ahead of them.

The premise being wrong is itself the decision's content, so it is recorded in
the row's `notes:` and in the module docstring as well as here. Issue #22's
grouping of "the eight `checkability: source` rows" behind one parameter
contract was already contradicted once, by ADR 0045's finding that the other six
are gated on capabilities rather than on a contract. This is the second half of
the same correction: the one row that looked like it *did* need the contract did
not either.

## Consequences

**Nine catalogued rows minus three: `pos` unblocked all three of its rows, and
no parameter-shape work was needed for any of them.** What issue #22 recorded as
a shared contract problem was, in the end, one capability and no contract.

**A row may take several texts without them being sources.** That is now
demonstrated rather than asserted, and the next row wanting a word list as a
parameter has a precedent that does not reach into core. What it must do instead
is say in each field's `description` what the field is for, because the schema is
the only place a non-Python caller reads it.

**The caller-facing caveats live in the definition, not only in `notes:`.**
`describe()` returns the definition, the prompt hints and the param schemas; it
returns `notes:` only under `scholarly=True`, a flag the MCP tool's own
docstring describes as being for "the form's source, attribution and history",
and which the CLI's human-readable output ignores entirely — `denckring
describe chimera --scholarly` prints exactly what `denckring describe chimera`
prints. So by default no caller sees a row's caveats, and a caller who wanted
them would have no reason to look under provenance.
The first draft of this row put four rulings, an estimate caveat and the fact
that `apply` can refuse entirely in `notes:` and the module docstring, and left a
definition that overclaimed twice: it said the content words are "replaced by"
the donors' (ruling 2 permits a drawn word to equal the one it replaced, so a
frame whose content words all appear in its donors satisfies itself) and it said
"three different source texts" (nothing requires or checks that the donors
differ). The definition now says what is true, following `iambic_pentameter`,
which carries its own caveat — "the checker verifies strict stress" — in the
definition for the same reason. That `describe()` omits `notes:` at all is a
cross-cutting gap, shared with `homosyntaxism`, and is filed separately rather
than fixed here.

**`seed` does less than the parameter list suggests, and each candidate says how
much less.** A donor pool is the tagger's reading of the donor, and a word that
reads as its class in the donor need not read as that class where it is drawn.
Measured: pools of four NOUN, two VERB and one ADJ over *The quick boy opened
the door.* give fourteen distinct outputs over twenty seeds, with the adjective
`bright` in all twenty. `Candidate.metrics` therefore carries
`target_positions` and `forced_positions`, the second counting the positions of
that output where exactly one donor word survives tagging — the
`undecided_words` / `PosTag.known` / `Production.truncated` idiom applied to
choice rather than to confidence. Only the sentence a position falls in is
re-tagged per trial, which on a 680-word frame is 0.34 s against 21.1 s for
whole-text re-tagging, for the identical count.

## Known remaining

**`apply`'s search is greedy and incomplete, and a refusal is not a proof of
unsatisfiability.** `_produce` draws a word per position, re-tags its own output
and redraws only the positions whose class did not survive, from the words not
yet tried there. That is coordinate descent: a redrawn position keeps every
other position's word, and a word once tried at a position is never tried there
again. Because a word's class is a fact about its context, a filling that this
walk cannot reach may still exist.

Measured, not supposed. Frame *The old lighthouse kept a steady light. Sailors
watched the dark water and counted every slow turn.* with `nouns_from` *A grocer
weighed salt.*, `verbs_from` *They carried the ladder, painted the shutters and
left.* and `adjectives_from` *A thin mist hung over the green fields.* — `apply`
at seed 0 raises `NoCandidateWord`, and *The thin grocer carried a thin salt.
Grocer carried the thin salt and carried every green grocer.* satisfies the same
parameters with score 1.0. A sweep of 400 random (frame, donors) pairs gave 21
refusals of which at least 8 were false, so the false share is 38% or more.

**Not fixed, and the ruling is that it should not be.** A complete search over
three pools is exponential and this row does not need one; an incomplete search
that says so is honest, and a backtracking search with a budget would be a
second thing to explain and would still refuse satisfiable cases. What was wrong
was the claim. The `NoCandidateWord` message now says that this greedy search
found no word and that a filling it cannot reach may still exist, the module
docstring says the search is incomplete, and
`test_apply_refuses_when_its_greedy_search_runs_out_at_a_position` holds the
refusal and the satisfying filling side by side. `docs/audit/chimera.md` records
the measurement. If a caller ever needs the refusal to mean unsatisfiable, that
is a new decision and a different search.

**A third check/apply asymmetry, from ruling 2.** Where every pool collapses to
the word already standing in its position — frame *The cold wind blows.* with
pools `{wind}`, `{blows}`, `{cold}` — `_produce` has nothing else to draw,
returns the frame, and the spine raises `DegenerateOutput`, while `check` reports
that same text satisfied. Both are right: the text does satisfy the constraint,
and `allow_identity` is how a caller asks for the degenerate case. Documented in
ruling 2 and tested, rather than made to disagree quietly.
