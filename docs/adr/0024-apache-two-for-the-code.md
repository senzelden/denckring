# 24. Apache-2.0 for the code, amending ADR 0006

## Context

ADR 0006 chose MIT for the code and CC BY 4.0 for the catalogue, and the second half
of that decision has held up: the catalogue's value is its sourcing, and CC BY is the
licence that makes credit a condition of reuse rather than a courtesy.

The first half was chosen for adoption alone. Two things it does not do turn out to
matter. MIT requires that the copyright notice be retained and says nothing further, so
a fork that keeps a line in a file has satisfied it while presenting the work as its
own; and MIT is silent on both patents and trade marks, so the project's name — the one
asset a fork cannot take without renaming — has no licence-level protection at all.

This is decided now because the cost of deciding it later is not symmetric. Before the
first release the copyright holder is one person. After it, relicensing needs the
consent of everyone who has contributed since.

## Decision

The code is Apache-2.0. A `NOTICE` file carries the attribution, and section 4(d) of
the licence requires every derivative distribution to carry it too. Section 6 grants no
trade mark rights, so the name stays with the project. The patent grant and its
termination clause come along, which MIT has no equivalent of.

The catalogue stays CC BY 4.0. Nothing in ADR 0006's data rule changes: language data
is still audited before it lands, anything copyleft still stays behind an extra, and
every data source still needs an ADR of its own.

Per-file Apache headers are deliberately not used. They are a convention of the licence,
not a requirement of it, and 118 procedure modules whose docstrings carry the reasoning
behind each checker would be worse documents with eleven lines of boilerplate on top.
LICENSE and NOTICE carry the terms; the distributions carry both.

Because the licence expression must describe what a distribution actually contains and
not only what its author wrote, the three published distributions declare compound SPDX
expressions: `Apache-2.0 AND CC-BY-4.0` for `denckring`, which ships the catalogue;
`Apache-2.0 AND CC-BY-4.0 AND BSD-2-Clause` for `denckring-en-data`, which ships Open
English WordNet and the CMU Pronouncing Dictionary; and `Apache-2.0 AND CC0-1.0` for
`denckring-de-data`, which ships Wikidata Lexemes.

## Consequences

A fork must carry the NOTICE, must rename to publish, and gains no claim on the name.
None of that prevents a fork, and no licence does — what it prevents is a fork that
presents itself as the original.

The obligation ADR 0006 created is now paid rather than merely stated: the wheel that
ships `catalogue.yaml` also ships `LICENSE-DATA`, so the CC BY terms reach the people
who install the package and never see the repository.

Apache-2.0 is incompatible with GPLv2-only code, which MIT was not. No dependency here
is GPLv2-only, and a Python library acquiring one is unlikely, but a future dependency
audit has one more question to ask than it did.
