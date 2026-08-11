# 2. `check` mandatory, `apply` optional

## Context

Every procedure in this library is a pair of generator and validator. The usual rule
for agentic development — give the agent a check it can run so the loop closes without
a human as verifier — normally requires inventing a test. Here it does not: a lipogram
either contains the forbidden letter or it does not.

## Decision

`check` is required for registration. `apply` is optional and meaningful only when
`kind` is `constructive` or `both`. A procedure without a working checker is not
registered.

## Consequences

The acceptance criterion is intrinsic to every registered procedure, so the codebase is
unusually well suited to unattended agent work. Restrictive procedures — the whole of
Batch 1 — are complete with `check` alone. The cost is that `apply` cannot be relied on
by callers without consulting `meta.kind` first, which the CLI does on their behalf.
