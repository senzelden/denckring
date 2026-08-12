# 17. A device's own data ships with its procedure

## Context

ADR 0013 sends linguistic data to separate distributions, with size and licence as
the stated triggers. Harsdörffer's five rings meet neither: 2 KB of public-domain
17th-century morphology.

There is also a hard obstacle. Since ADR 0016 two packs claiming one language raise
`DuplicatePack`, and German already registers through the entry-point group from core.
A German data distribution would collide with the pack already there.

## Decision

The rings ship in core at `denckring/data/devices/harsdoerffer_1651.yaml`, beside the
catalogue. The distinction that makes this consistent rather than convenient: **a
lexicon describes a language, a device *is* a procedure.** A Denckring with different
rings is a different device, in the way a lipogram with a different forbidden letter is
still a lipogram. The rings are the procedure's definition, not data it consults.

The procedure takes the device by parameter, defaulting to the historical one, so the
mechanism is not welded to a single object.

## Consequences

`denckring` runs, which after ten chapters is the least it owed its own name. Being
constructive as well as checkable, it also exercises the round-trip property from both
sides: spinning the rings must produce a word the rings accept.

The round-trip suite had to learn that not every constructive procedure is
source-relative — `cut_up` needs the text it cut up, `denckring` needs nothing but its
own rings.

Provenance is recorded rather than tidied. The data is Harsdörffer's, transcribed by
Florian Cramer, whose digitisation appears to be the only machine-readable copy; a
faithful transcription of a public-domain text carries no new copyright, and the credit
is owed regardless. Where his counts depart from Harsdörffer's own — 49 prefixes against
a stated 48, 60 initials against 50, 23 suffixes against 24 — both are recorded and
neither is adjusted to agree with the other.

The catalogue row also records that the 97,209,600 combinations the literature repeats
cannot be right: the figure is not divisible by 144, so it cannot be a product of rings
of 12 and 120 at all.
