# 13. Linguistic data ships as separate distributions

## Context

ADR 0010 put the German pack in core because it needed no data, and recorded the
trigger for splitting data out: the first lexicon. The CMU Pronouncing Dictionary is
that lexicon — 135,166 entries, 3.6 MB, BSD-2-Clause.

## Decision

`denckring-en-data` is a separate distribution, a workspace member of this repository,
installed by `pip install denckring[en]`. It registers through the same
`denckring.lang` entry-point group as any third-party pack, and subclasses the core
English pack rather than replacing it.

Pack precedence became: explicitly registered, then entry point, then built-in
default. Without that last change the seeded core pack shadowed the data package
entirely.

## Consequences

The core wheel stays small and free of data, so a user who wants lipograms does not
download a pronouncing dictionary. Data licences are quarantined per distribution:
CMUdict's attribution requirement lives in `LICENSE-CMUDICT` beside the data it
covers, and a future copyleft lexicon has an established place to go without touching
the permissive core — which is what ADR 0006 requires.

The dictionary is vendored rather than downloaded, so neither installation nor use
touches the network.

The cost is a uv workspace and a second `pyproject.toml`, and the fact that two
distributions must now be released together when the pack interface changes.
