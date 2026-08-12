# 21. Implement the transferable part, not the artefact

## Context

Kircher's *Arca musarithmica* sets text to four-part music. A library of writing
procedures has no representation for a four-part setting, no pitch, no rhythm, and no
business acquiring them. On a literal reading the Arca does not belong here at all.

But the machine underneath is not musical. It measures a phrase, looks up the tablet
indexed by that measure, and draws a column. The music is what Kircher put in the
columns.

## Decision

Implement the indexing and leave the columns opaque. `arca_musarithmica` counts a
phrase's syllables, finds the tablet for that length, and verifies the chosen pattern is
one that tablet offers. It never reads a pattern.

Put Kircher's pitch numbers in the table and you get his machine. Put stress patterns or
rhyme schemes in and the same bones carry those — which a test asserts, because a claim
about pluggability that nothing exercises is decoration.

## Consequences

The catalogue row says exactly this, so nobody expects music from it. The distinction it
draws is the same one `sestina` and `eodermdrome` draw: the entry names the form, the
definition names what the checker verifies, and the two are not allowed to drift apart.

No tablet ships. Kircher's own runs to many pages of *Musurgia Universalis* book VIII
and has not been transcribed into anything this project could verify — the same
arrangement as the corpus and the pasigraphic vocabulary, and for the same reason.

A phrase whose length the tablet does not cover is unsettable, and gets its own error
rather than a malformed-table one. Kircher's rods run to particular lengths; a text that
exceeds them cannot be set by that box, and that is a fact about the box, not a fault in
it.

The chapter also closed a gap in the invariant suite. `satisfied == (score == 1.0)` had
been asserted from the beginning, but nothing asserted that a satisfied report carries no
violations — so a violation the score never counted could produce a report saying the
text passed and then listing what was wrong with it. The Arca's tone check did exactly
that before it was fixed.
