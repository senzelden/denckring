# 20. A corpus is supplied by the reader, never by the package

## Context

Devices and figures are finite and closed: Harsdörffer's rings and Llull's nine letters
are the procedure, so they ship with it (ADR 0017). A corpus is neither. It is external,
open-ended, and — this is the part that decides the question — usually somebody else's
work.

Jean Paul's excerpt books are the case. The manuscripts are public domain: he died in
1825. The transcriptions that make 100,000 entries usable are a scholarly edition from
the Arbeitsstelle Jean-Paul-Edition at Würzburg, with named transcribers and their own
rights. Freely readable is not freely redistributable.

## Decision

The package carries the loader; the reader supplies the reading. `Corpus`, `Entry` and a
parser live in core; no corpus does. A corpus reaches a procedure through the existing
`source` parameter as text — JSON or one excerpt per line — so nothing new was needed to
carry it, and the CLI's `--source FILE` already works.

Test fixtures are synthetic throughout. The Würzburg sample this chapter was designed
against sits outside the repository entirely.

## Consequences

`ideenwuerfeln` works against whatever a reader has, which is the honest arrangement for
a procedure whose whole point is drawing on a collection somebody assembled by hand.

Reading the parameter as text rather than a path also means the library never opens a
file the caller did not hand it, which keeps the capability surface where it was.

`apply` may now refuse: a corpus of one line is not three excerpts. The round-trip suite
had to learn that a generator declining unusable input is not a failure of the property
— what the property asserts is that whatever `apply` *produces* passes `check`.

The reconstruction question is recorded separately. Jean Paul named the notebook but
never wrote the rule down, so `ideenwuerfeln` carries `attested: reconstruction` — the
first row to do so, and the reason ADR 0018 added the field.
