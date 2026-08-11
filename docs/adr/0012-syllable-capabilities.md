# 12. Two syllable capabilities, with the weaker one as the floor

## Context

Syllable counting can be done from spelling, cheaply and approximately, or from a
pronouncing dictionary, exactly and at the cost of shipping 3.6 MB of data. ADR 0004
forbids silent approximation across languages; the same argument applies within one.

A capability that no procedure requires is decoration, so declaring
`syllables.dictionary` and having everything require it would leave
`syllables.heuristic` inert — and a core-only install unable to check a haiku at all.

## Decision

Both capabilities exist. Procedures declare `syllables.heuristic`, the weaker one,
which every English pack satisfies. A pack that also declares `syllables.dictionary`
answers the same calls more accurately; nothing branches on which is installed.

`syllable_count` returns `(count, exact)`, and every syllabic report carries
`metrics["estimated_words"]`.

## Consequences

The capability is a floor rather than a switch: installing `denckring[en]` improves
existing procedures instead of enabling different ones. On Bashō's frog-pond haiku,
core alone reports 13 estimated words; with the data package it reports zero.

This is not a silent fallback, because the estimate count is on every result. A caller
needing certainty asserts it is zero, and a future procedure that cannot tolerate
estimates may require `syllables.dictionary` outright, at which point a core-only
install correctly raises `MissingCapability`.

The heuristic's agreement with the dictionary is measured by a test — currently 83.8%
on a sample of 631 words — with an enforced floor, so a change that makes it worse
fails the build rather than degrading quietly.
