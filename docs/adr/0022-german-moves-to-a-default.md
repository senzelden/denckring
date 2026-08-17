# 22. German is a built-in default, not an entry point

## Context

ADR 0010 registered the German pack through the `denckring.lang` entry-point group so
that a pack shipping inside the core wheel would take the same path a third-party pack
takes. That demonstration worked, and it stopped working the moment a German *data*
distribution became possible.

`lang._install` raises `DuplicatePack` when two entry points claim one language —
deliberately, because silently choosing would make answers depend on installation order.
Core claims `de` by entry point, so `pip install denckring[de]` would have raised on the
first `get_pack("de")` call.

English never had this problem: the core English pack is a built-in default, which is
precisely what lets `denckring-en-data` override it.

## Decision

German moves into `_DEFAULTS` beside English, and core declares no entry points at all.

## Consequences

`de` now behaves exactly like `en`: core provides the floor, a data distribution
upgrades it, and precedence resolves without a collision.

The demonstration ADR 0010 wanted is not lost but improved. The entry-point path is now
exercised by two genuinely external distributions, `denckring-en-data` and
`denckring-de-data`, rather than by core against itself — which is a stronger
demonstration than the one removed, because a same-wheel pack could never have proved
that precedence works.
