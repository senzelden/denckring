# 65. Metrical licences, one switch each, opt-in

## Context

The stress-scanning rows read each word as the pronouncing dictionary stresses it and
ask whether some combination of its listed readings fits the line's pattern (ADR 0014,
ADR 0054). Canonical English verse does not scan that way, and the gap is not the
dictionary's fault. Poets take a small set of standard licences, and the checker
admitted none of them.

The public-domain sourcing pass for `petrarchan_sonnet` (ADR 0062) made this concrete.
It screened 97 fourteen-line blocks from Milton's poems in Beeching's edition (Project
Gutenberg #1745) and Wordsworth's *Poems in Two Volumes* (1807; #8774, #8824), and the
row rejected every one. Two of Milton's sonnets came closest. "When I consider how my
light is spent" failed on two words only. Line 10 opens "Either man's work", a reversed
first foot, which is the commonest licence in English pentameter. Line 13 reads "Ocean
*with*out rest", where the dictionary has only `01`. "Cyriack, whose Grandsire" failed on
`disapproves`, which the dictionary gives as `001` and the line wants as `101`, and on
`superfluous`. Every one of these is a reading a prosodist would accept, and the row was
left with no external case.

The maintainer decided on 2026-10-14 to model these licences as an opt-in, off by
default, with one switch per licence, a closed list for stress shift and a diaeresis rule
for the syllable licence.

## Decision

**Four `bool` parameters, each off by default:** `initial_inversion`, `secondary_stress`,
`stress_shift` and `diaeresis`. They sit on `LicenceParams`, and every row that scans an
iambic or trochaic line, which is every row that can raise `wrong_stress` except the five
named below, takes them. Eleven rows take `ScansionParams`, which is `MetreParams` plus
the four: `ballade`, `blank_verse`, `curtal_sonnet`, `heroic_couplet`,
`iambic_pentameter`, `ottava_rima`, `petrarchan_sonnet`, `rhyme_royal`,
`shakespearean_sonnet`, `sonnet` and `spenserian_stanza`. `ballade`, `heroic_couplet`,
`iambic_pentameter` and `petrarchan_sonnet` took no `MetreParams` before, so they also
gain `feminine_ending`. `trochaic_tetrameter` takes `LicenceParams` alone: its line
already closes on an unstressed syllable, and one more would be a dactylic close, which is
not what `feminine_ending` describes. `alexandrine` keeps plain `MetreParams`. It counts
syllables and scans no stress, so three of the four switches would be parameters that do
nothing there. The rows that scan dactylic or classical patterns (`alcaic_stanza`,
`sapphic_stanza`, `dactylic_hexameter`, `elegiac_couplet`, `double_dactyl`) take none of
these parameters and are unchanged. Their patterns are already sets of feet with
substitutions or an anceps, and a reversed first foot or a promoted syllable is not the
licence those forms take. `tests/test_metre_licences.py` finds the rows by behaviour: any
row whose rules include `wrong_stress` must take the four, unless it is one of these five,
listed there with its reason.

What each switch admits:

- **`initial_inversion`.** A line may also be read with the first two positions of its
  pattern swapped, when they differ: `01` read as `10` in an iambic line, `10` as `01` in
  a trochaic one. This applies to the first foot only, never to an anceps (`?`), and is
  added as an alternative pattern, the way `with_feminine` adds a feminine one.
- **`secondary_stress`.** In a word of three or more syllables, an unstressed syllable
  (`0`) that is not next to a `1` may take a beat, so `disapproves` (`001`) may also be
  `101`. Several such syllables may be promoted at once, provided no two of them are
  adjacent. Words of one or two syllables are unaffected.
- **`stress_shift`.** The words on a closed list may be read `10` or `01` whatever the
  dictionary says. The list is `prosody.SHIFTABLE`: without, within, upon, into, unto,
  beyond, before, toward, towards, across, among, beneath, below, above, about, against,
  along, around, behind, between, despite, throughout, therein, thereon, wherein. The
  brief that proposed it also named `whereon`. CMUdict does not carry that word, and an
  unknown word already takes any stress, so it was dropped. A test holds that every word
  on the list is a disyllable in the dictionary.
- **`diaeresis`.** A word may have one syllable more than the dictionary gives it. The
  new syllable is unstressed, and the vowel after it is free (`?`), as a monosyllable's
  is. Two rules decide where:
  - *Phones.* In the dictionary's first pronunciation, a `W` or `Y` counts when it
    follows a consonant other than `K` or `G` and precedes a vowel with stress `0` or `2`.
    For `Y`, that vowel must not be `UW` or `UH`. The word's spelling must also contain an
    `i` or `u` before another vowel letter. Under this rule `million`, `M IH1 L Y AH0 N`,
    may be `10?`.
  - *Spelling.* The rule applies to a word ending in `-ious`, `-uous`, `-ial(s)` or
    `-ian(s)` when none of its dictionary forms has as many syllables as the vowel-letter
    groups before the ending plus two. Each form that has one syllable fewer, and does not
    end on a stress, gains one. Under this rule `ambrosial`, `010`, may be `010?`.

**Scope.** `initial_inversion` reads no dictionary, so it applies in every language,
German included. The other three read CMUdict's stress or phones, or English spelling,
and they are stated for English only. With any of them on, a German or French text is
read exactly as with it off, and a test holds this for Goethe's *Iphigenie*. No rule has
been stated for another language's pack.

**A second pass, not a wider first one.** `line_metre` scans every option with the
dictionary's readings first, exactly as before. The licences are tried only when nothing
fits. A licensed reading of a word is offered after the word's own readings. So a line
that scans without a licence is never reported as needing one, and with every switch off
the scan is byte for byte what it was. Each switch derives its readings from the
dictionary's forms only, never from another switch's, so a switch admits its own licence
and no combination of two. A test checks the full four-by-four table.

**Evidence names the licence.** A word read through a licence shows it in its evidence
value, `10 (stress_shift)` or `10 (initial_inversion)`. A word licence tags the word whose
reading it supplied. A line licence tags every word with a syllable on the reversed foot,
and that does not mean the word's own reading changed: in "And disapproves that care",
read on the inverted pattern, `disapproves` shows `001 (initial_inversion)`, its
dictionary form, because its first syllable stands on the reversed foot. `basis` still
says where the word's own readings came from (`dictionary`, `ambiguous`, `estimated`).
Adding a fourth basis value would widen a closed set that every consumer of `Evidence`
matches on, to say something the value can say for itself.

**Licensed forms count towards `MAX_COMBINATIONS`.** The cap holds a line's combinations
of readings to 4,096 and, past it, scans only each later word's first form. A licensed
reading is one more combination, so in principle a line could be capped on the licensed
pass where the dictionary pass was not, and a switch could then lose a reading another
switch alone had found. It stays counted, because the cap exists to bound the work and the
licences are where the work grows. Measured on the 10,611 lines of Paradise Lost below and
on the same lines shuffled, no line is newly capped with all four on, and no line passes
with one switch and fails with all four.

**No `checker_version` bump** (ADR 0061). A parameter 0.5.0 would have rejected as
unknown cannot move a verdict 0.5.0 gave, and the verdict fingerprints are unchanged on
every existing probe.

## Consequences

`petrarchan_sonnet` has its first external case: Milton's Sonnet XVI, checked with
`initial_inversion` and `stress_shift` and passing under nothing less. It leaves the gap
registry. The re-screen of the same 97 blocks, measured on 2026-10-14:

| setting | blocks the checker admits |
|---|---|
| default | 0 |
| `feminine_ending` alone | 0 |
| each of the four alone | 0 |
| `initial_inversion` + `stress_shift` | 1 ("When I consider") |
| all four | 1 |
| all four + `feminine_ending` | 1 |

**The licences do not rescue "Cyriack, whose Grandsire".** `secondary_stress` reads
`disapproves` as Milton does. The line "That with superfluous burden loads the day" still
fails, because CMUdict puts the primary stress of `superfluous` on its first syllable
(`S UW1 P ER0 F L W AH2 S`, `10?`) where Milton's line has it on the second. That is a
dictionary stress, not a missing syllable. `diaeresis` gives the word a fourth syllable
(`100?`), which makes the line eleven syllables and leaves its stress where it was.
None of the four switches moves a primary stress, and that is deliberate.

**Every switch admits misfits, and the measured share is large.** The test is Paradise
Lost as Beeching prints it: 10,611 lines, extracted by script as the indented lines of
four words or more, so a few editorial lines may be among them. Each was scanned as
pentameter with or without a feminine ending. The same lines were then scanned with their
words shuffled (seed 0). Each shuffled line keeps its syllables but is metrical only by
accident.

| switch | real lines that now scan | shuffled lines that now scan |
|---|---|---|
| none (baseline) | 6,747 | 3,476 |
| `initial_inversion` | +515 | +615 |
| `secondary_stress` | +942 | +450 |
| `stress_shift` | +69 | +128 |
| `diaeresis` | +10 | +13 |
| all four | +1,614 | +1,286 |

`initial_inversion` admits more shuffled lines than real ones. A reversed first foot is
too common a shape to tell verse from a word salad. With all four on, the checker admits
about four shuffled lines for every five real ones it gains. A caller who switches the
licences on is asking a weaker question, and this table is how much weaker.

**The list is editorial.** `SHIFTABLE` encodes a judgement about which words verse moves
freely. Someone else's list would differ, and a word left off it fails where a reader
would let it pass. The list is closed so that the judgement is visible and can be
argued with, not so that it is right.

**The diaeresis rule has false positives, and the brief's simpler rule had many more.**
The sample was the 5,000 most frequent words that CMUdict carries. As first proposed,
the phones rule (any `W` or `Y` after a consonant and before a `0` or `2` vowel) fires on
135 of them. Most are not diaereses: `figure` and `regular` (the `y` of a `cu` or `gu`),
`equal` and `language` (the rounding of `qu` and `gu`), `value` and `continue` (the vowel
`u` itself), `forward` and `railway` (a `W` no vowel letter spells). Applied in that
order, the three exclusions above remove 53 (after `K` or `G`), 32 (`Y` before `UW` or
`UH`) and 23 (no `i` or `u` before a vowel letter). The rule as shipped, phones and
spelling together, fires on 56 of the 5,000. By the author's reading, 6 of those 56 are
false: `population`, `populations`, `reputation`, `ammunition`, `genuine` and
`genuinely`. The spelling check is made on the whole word, not at the glide, so in the
first four a `-tion` elsewhere in the word lets a `Y` through. In `genuine` the
dictionary's first reading already gives the `u` a syllable of its own after the `Y`.
The other 50 are the classical cases, such as `so-ci-al`, `re-li-gi-ous`, `mil-li-on` and
`un-i-on`. No reader would split all of them in one poem.

**The freed vowel is a choice, and it is measured.** In the brief's version the new
syllable was a `0` and every other mark stayed as the dictionary had it. Then the new
syllable nearly always stands next to another `0`, and no iambic or trochaic line fits:
on Paradise Lost that reading rescued no line, and on the 1,358 lines of the petrarchan
screen none either. With the vowel after the glide free, it rescues ten lines of Paradise
Lost (`celestial` three times, `Ambrosial`, `impetuous`, `Union`, `Communion`, `nuptial`,
`Pernicious`, `Religious`), each a diaeresis Milton's metre asks for. The cost is that
the freed vowel may also take a beat, which is a small promotion folded into this
licence. That is what Milton's `Re-li-gi-ous` does, and a caller who has `diaeresis` on
has accepted it.

**The phones rule reads the first pronunciation only.** `phonemes` is the pack's one
view of a word's phones, so a diaeresis in a second listed pronunciation is not found.

**Don Juan I, re-measured with every switch** (`ottava_rima`, the 222 stanzas of Canto I
in Coleridge's edition, extracted as for the existing cases). By default the checker
admits 3. With `feminine_ending` it admits 5. With all four licences it admits 5, and
with all four and `feminine_ending`, 18. That still rejects 204: 113 on stress, 148 on
rhyme and 115 on line length, and a stanza may fail on more than one. Rhyme is untouched
by any of this, and it is now the larger obstacle. No further stanzas are landed. The
licences were not written for Byron, and a Don Juan case passing only under all five
switches would be evidence about the switches, not about ottava rima.

**White's ballades (1887), re-measured with every switch.** The 77 poems the row's
screen selects (stated in the `tomson-ballade-of-asphodel` case) give:

| setting | admitted | rejected | of those, on stress |
|---|---|---|---|
| default | 1 | 76 | 49 |
| all four | 1 | 76 | 30 |
| all four + `feminine_ending` | 2 | 75 | 53 |
| `metre` `0101010101` | 0 | 77 | 31 |
| the same, all four + `feminine_ending` | 0 | 77 | 31 |
| `metre` `010101` | 1 | 76 | 4 |
| the same, all four + `feminine_ending` | 1 | 76 | 14 |

The one ballade the switches add is "Ballade of Might-Be", with all four and a feminine
ending. Nothing is landed from this: as with Byron, a case passing only under five
switches would be evidence about the switches. The stress count can rise with the
switches on, because `feminine_ending` admits eleven-syllable lines that were refused on
length and are now scanned for stress.
