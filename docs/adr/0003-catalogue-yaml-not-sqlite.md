# 3. Catalogue in YAML, not SQLite

## Context

The catalogue holds several hundred procedure descriptions and is read once per
process. The original repo seed proposed `data/catalogue.yaml` compiled into SQLite.

## Decision

The catalogue is a single YAML file, parsed and cached at first use. No SQLite, no
build step, no compiled artifact.

## Consequences

The catalogue stays diffable, reviewable in a pull request, and directly publishable as
CC BY open data — which is the point of keeping it separate from the code at all. A few
hundred rows parse in milliseconds, so the database would buy nothing but a second
source of truth. Revisit at more than a thousand entries, or when the documentation
gallery needs to query rather than iterate.
