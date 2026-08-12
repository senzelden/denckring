# Security policy

## Supported versions

The most recent release is supported. This project is pre-1.0; older versions receive
no fixes.

## Reporting a vulnerability

Report privately through GitHub's [security advisory
form](https://github.com/senzelden/denckring/security/advisories/new), not as a public
issue. Expect an acknowledgement within a week.

## Scope

denckring reads text and data files and makes no network calls at runtime. The
plausible risks are therefore narrow, and worth stating so a reporter knows what counts:

- **Untrusted input to a checker.** Procedures accept arbitrary text and parameters. A
  crash, a hang, or unbounded memory use on adversarial input is a valid report — the
  test suite exercises arbitrary Unicode, but not adversarially.
- **Language pack loading.** Packs are discovered through the `denckring.lang`
  entry-point group, so an installed package can register one. That is by design and is
  the same trust boundary as any Python dependency; a way to load a pack *without* it
  being installed would be a vulnerability.
- **Catalogue and fixture parsing.** YAML is read with `yaml.safe_load`. A path by which
  it is not would be a valid report.

Out of scope: a procedure disagreeing with a literary authority about what a form
requires. That is a correctness bug — please open an issue.
