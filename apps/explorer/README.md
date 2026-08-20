# denckring explorer

A local browser for the catalogue, and a bench for trying the procedures on your own
text. It is a development tool, not part of the distribution — nothing here is
published, and the package does not depend on it.

```console
cp apps/explorer/.env.example apps/explorer/.env   # optional; see below
uv run --project apps/explorer explorer
```

Then open <http://127.0.0.1:8412>. Use `--port` if that one is taken.

## Configuration

Everything optional. `.env.example` documents each variable; copy it to `.env`
and fill in what you want. `.env` is gitignored, real environment variables win
over it, and the CLI flags win over both.

`DENCKRING_CORPORA` points at a directory of corpus JSON files (default
`~/corpora`), which the `ideenwuerfeln` bench offers as a picker. The corpus is
read on the server and never posted back through the form — a 28,000-entry
corpus is 5.8MB, which the HTTP field-size limit refuses outright.

`ANTHROPIC_API_KEY` enables *Find the Witz* under a generated throw: a model
reads the collision and says what, if anything, the excerpts share. It is a
reading and not a verdict — no `Report`, no score, and nothing in the package
consults it. `ideenwuerfeln` says the Witz is the step no program does, and that
stays true; this is a reader at the bench, kept here precisely so the library's
acceptance criteria stay intrinsic. Leave the key unset and the button does not
appear.

## What it shows

**The case** lays the whole catalogue out the way a compositor lays out type: one
compartment per procedure, filled where a checker exists, ruled through where no
program could ever judge the form. Coverage is the picture rather than a number.

**What's missing** splits the absences in two. Most are waiting on a capability nobody
has written — the page groups them by which one. The rest can never be written, and
are counted separately so the figure never promises a gap that cannot close.

**A procedure page** runs the real checker. The parameter form is generated from that
procedure's `params_schema()`, so it always matches what the code accepts; the recorded
examples are the golden fixtures CI enforces, so they behave here exactly as they do
there; and the result marks the offending characters inline using the offsets every
`Violation` has carried since the first release.

## The board and the stage

`/board` lays out every golden case in the catalogue and runs each one live, so
it is slow by design — that is the coverage picture, run for real rather than
cached. `/stage` holds five recordable demo scenes at a fixed size for
screen capture. Neither needs a corpus except the Ideenwürfeln scene, which
explains itself in the page when `DENCKRING_CORPORA` is unset.

The Python suite executes no JavaScript. What is guarded by tests is the markup,
the routes and the procedures behind them; the scenes' actual behaviour in a
browser — the discs spinning and landing, the reduced-motion paths, the layout
fitting 1280×720 — is verified by hand and by no test at all. That gap is worth
naming plainly: checking scenes by eye in this stage caught three real bugs a
Python test could not have seen, including four of five discs painted over one
another and a deadlock that left the whole scene dead until reload.

## What it is not

It reads the installed `denckring` at request time and copies nothing, so it cannot
drift from the library. It also has no state, no database and no authentication: it
binds to localhost and is meant for one person on one machine.
