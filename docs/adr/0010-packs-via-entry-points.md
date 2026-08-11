# 10. Language packs are discovered through an entry-point group

## Context

The repo seed put German behind `pip install denckring[de]`, on the assumption that a
German pack means German lexicons. For Batch 1 it does not: the twelve lexicon-free
procedures need no word list, no hyphenation and no data of any kind. An extra that
gates nothing is a promise with nothing behind it.

Separately, the seed's claim that third parties can supply their own pack had never been
exercised. A pack registered by hand in a module-level dict proves nothing about the
path an external distribution would take.

## Decision

Packs are discovered through the `denckring.lang` entry-point group. German ships inside
the core wheel and registers through that group like any third-party pack would. English
is seeded directly into the registry rather than through the group.

## Consequences

The extension path is exercised by a real pack on every test run, so it cannot rot
unnoticed. Seeding English directly means core never depends on its own installed
metadata being readable in order to find its own language — a broken or unusual install
surfaces as a missing *additional* language, not as a library that cannot check anything.

When German acquires a lexicon, it is the *data* that moves behind an extra, not this
module, and the licensing rule in ADR 0006 applies to that data alone. `denckring[de]`
remains available as the name for that future extra.
