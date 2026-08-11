# 7. One module per procedure

## Context

The catalogue is hundreds of small, independent procedures with no shared state and no
ordering dependencies. That structure invites parallel implementation — several agents
or contributors working on different procedures at once.

## Decision

Exactly one procedure per module, and the module name must equal the procedure id. This
is enforced at registration: `register` raises if they disagree. There are no collector
modules — no `__init__` importing procedures by name, no shared per-procedure test file.
The three registry-wide test suites iterate whatever autodiscovery finds.

## Consequences

Adding a procedure touches only files that are new, so parallel work never produces a
merge conflict. The cost is that discovery is dynamic rather than explicit, so a typo in
a module name shows up as a missing procedure rather than an import error — which the
invariant suite catches instead.
