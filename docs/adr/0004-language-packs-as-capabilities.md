# 4. Language packs as capability-declaring plugins

## Context

Multilingualism here is not a translation layer. Procedures behave differently per
language in ways that touch the algorithm: whether `é` counts as `e` for a lipogram,
whether N+7 can handle German compounds, which glyphs have ascenders in a given
orthography.

## Decision

Each pack declares a `capabilities` set. Each procedure declares `requires`. Calling a
procedure with a pack that lacks a capability raises `MissingCapability`, naming the
procedure, the language and the missing capability. A pack implements every protocol
method, but a method whose capability it has not declared raises rather than returning
an approximation.

## Consequences

A caller can never receive a silently wrong result in a language the library does not
really support, which is the single rule that makes the package trustworthy across
languages. English ships in core; German and French are extras carrying their lexicons.
Third parties can register a pack, so the library is genuinely extensible rather than
merely trilingual.
