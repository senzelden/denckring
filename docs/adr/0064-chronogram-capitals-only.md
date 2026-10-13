# 64. Chronograms read off their capitals, opt-in

## Context

`chronogram` counts every numeral letter in the text, capital or not, which is Hilton's
reading. Its authority is James Hilton, *Chronograms, 5000 and More in Number* (1882), and
the shipped external case `chronogram-my-day-closed` quotes his verdict on the line made
for the death of Queen Elizabeth I: "It really is a very bad one, for although it gives
the year 1603, it can also be made to give a variety of dates up to 4204 … The pretext it
has for appearing as a chronogram is that only the initial letters of the words are
counted" (p. 9). `Counting.every_occurrence` cites the same page.

Other compilers did not share that judgement. C. C. Bombaugh, *Gleanings for the Curious
from the Harvest-Fields of Literature* (enlarged ed., 1890), p. 58, prints the same line,
in his order "My Day Is Closed In Immortality.", as one that "commemorates the death of
Queen Elizabeth", dated 1603, with no objection. Read his way, only the capitals count:
M D I C I I, 1603. Under the row as it stood, his line fails, and nothing in the
parameters could say which reading a caller meant.

The maintainer decided on 2026-10-13 to model the reading Hilton rejects, as an option,
while keeping his as the default.

## Decision

**`ChronogramParams.capitals_only: bool = False`**, role `switch`. When set, a numeral
letter counts only if its character in the caller's text is a capital. Case is read from
the text as given, not from the letters the checker sums, which are lower-cased and,
under `fold_diacritics`, folded: `Ïx` totals 1 with folding on (a capital, folded to I)
and 0 with it off (a capital, but `ï` is not a numeral). A decomposed capital is read at
its base character's offset, so it counts as its composed form does. Letters set as
Unicode small capitals (`ᴍ`, `ɪ`) are not numerals under either setting; the golden
cases write a printed small capital as a lower-case letter, as they already did.

**`Reading.counting` names the switch.** `Counting.case_switch: str | None = None` is a
new field naming the parameter that makes case decide, following `folds`, which names the
parameter that decides folding. `chronogram` sets it to `"capitals_only"`.
`case_sensitive` keeps its meaning: what the default does, which is still `False`. The
field is optional with a default because `Counting` is promised (ADR 0060): a consumer
validating a 0.5.0 `Counting`, which has no such key, still parses it.

**`Counting.skipped` now says that German ä, ö, ü and ß are never numerals.** Folded they
become a, o, u and ss; unfolded they stay themselves; none is in the table either way, so
they add nothing to the total. That was true before and is now published; a test runs it
under all four combinations of the two switches.

**No `checker_version` bump** (ADR 0061 B1). A bump is owed by a change that can move a
verdict on some call, and no call valid in 0.5.0 can reach the new code: 0.5.0 refuses
any parameter a row's model does not name (`core.base.parse_into`, unchanged since), so
`check("chronogram", "LVX", year=65, capitals_only=True)` there raises `InvalidParams`
("unknown parameter(s) ['capitals_only']"). With the switch off, the numerals are filtered by nothing new. The
verdict fingerprint confirms it: refreshing the snapshot added the new cases' probes and
changed none of the existing ones. `checker-history.yaml` is unchanged.

**Two golden cases.** `bombaugh-my-day-is-closed-capitals` is Bombaugh's line,
`provenance: external`, satisfied under `capitals_only` at 1603; it stands beside
`chronogram-my-day-closed`, Hilton's order of the same words, which stays as it was and
still fails at 4204 under the default. `lowercase-numerals-do-not-count-under-capitals-only`
is a constructed counterexample: `Mild vixen` totals 1567 counting every numeral, and
1000 under the switch.

## Consequences

The row now models a reading its own authority rejects. Hilton's objection is that a line
read off its capitals carries "superfluous numeral letters" that can be made to give
other dates; under `capitals_only` the checker passes exactly such a line and says
nothing about the superfluous letters. A caller can pass a text Hilton would fail, and the
report will not tell them so. The description says "the reading Hilton calls a pretext",
which is the only warning the switch carries.

The switch's only external evidence is a compiler. Bombaugh collects curiosities across
every kind of literary trick; he is not a chronogram specialist, and he prints the line
without discussing how it is read. The one specialist the row cites argues against it.
The case is transcribed by script from the Project Gutenberg text, whose page marker puts
the line on p. 58; the page image was not checked. Bombaugh's word order ("Is Closed")
differs from Hilton's ("Closed Is"); the sum does not depend on it, but it means the two
cases are two printings, not one text read twice.

`Counting` gains a field. Adding one is allowed by the promise; a consumer that rejects
unknown keys when parsing would fail on a payload from the release that ships this, which is the cost the promise
already places on such a consumer. `case_switch` names one parameter; a row whose case
depended on two would need a different shape.

The external share of the golden corpus rises by one case, which is not a reason for the
switch and should not be read as one: the case evidences an option, not the row's default.
