# 6. Dual licence: MIT code, CC BY catalogue

> **Amended by [ADR 0024](0024-apache-two-for-the-code.md).** The code moved from
> MIT to Apache-2.0 before the first release. The catalogue half of this decision,
> and the data rule in it, still stand.

## Context

The catalogue is a contribution in its own right. The field is littered with one-off
toys and unlicensed word lists, and a clean, sourced catalogue of several hundred
procedures is useful independently of the code that checks them.

## Decision

Code is MIT. The catalogue is CC BY 4.0 with per-entry source attribution. Language
data must be audited separately before it lands: Wiktionary-derived data is CC BY-SA
and share-alike attaches; pyphen is GPL/LGPL/MPL tri-licensed. Anything copyleft stays
behind an extra so the core remains permissive.

## Consequences

The catalogue can be cited and reused by people who will never install the package.
Core stays permissively licensed no matter what a `[de]` or `[fr]` extra later carries.
The obligation this creates is real: no lexicon may be added to core, ever, without
first recording its licence in an ADR of its own.
