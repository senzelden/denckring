# 1. English API, multilingual content

## Context

An earlier sketch of this library used German identifiers — `pruefe`, `Befund`,
`wende_an`. The package is intended for PyPI and a public repository, and its
audience is international: Oulipo scholars, computational poetics researchers, and
developers building writing tools.

## Decision

Identifiers, docstrings, error messages and the CLI are English. German and French
appear only as data: catalogue names, definitions and prompt hints, and the internals
of language packs.

## Consequences

The API reads the same as any other Python package, which removes an adoption barrier
that has nothing to do with the library's subject. Multilingualism becomes a property
of the content and the language packs rather than of the surface, which is where it
actually belongs — a French lipogram differs from an English one in its diacritic
handling, not in what the function is called.
