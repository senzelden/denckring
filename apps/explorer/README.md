# denckring explorer

A local browser for the catalogue, and a bench for trying the procedures on your own
text. It is a development tool, not part of the distribution — nothing here is
published, and the package does not depend on it.

```console
uv run --project apps/explorer explorer
```

Then open <http://127.0.0.1:8412>. Use `--port` if that one is taken.

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

## What it is not

It reads the installed `denckring` at request time and copies nothing, so it cannot
drift from the library. It also has no state, no database and no authentication: it
binds to localhost and is meant for one person on one machine.
