# 8. The catalogue lives inside the package

## Context

The repo seed sketched the catalogue at `data/catalogue.yaml` in the repository root,
alongside `src/`. But the loader reads it at import time, and it must therefore be
present in an installed wheel, not merely in a source checkout.

## Decision

The catalogue lives at `src/denckring/data/catalogue.yaml` and is read via
`importlib.resources`. The CC BY data release points at that path.

## Consequences

`pip install denckring` gives a working catalogue with no extra packaging
configuration, since hatchling includes package data by default. The deviation from the
seed's layout is cosmetic — the file is still a single, diffable, separately-licensed
YAML document, which is what the separation was for.
