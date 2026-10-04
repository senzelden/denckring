# 54. Syllable counts read every listed pronunciation

## Context

ADR 0014 made metre a satisfiability question: a line scans when *some* combination of
the pronunciations CMUdict lists fits. Rhyme followed: two words rhyme when any pair of
their keys matches. Syllable counting did not. `syllable_count` read the first
pronunciation only, so the line-count rows (`haiku`, `tanka`, `syllable_count`,
`cinquain` and the rest) judged a line by the one reading CMUdict happens to list
first.

denckring-bench found the cost (audit A3). `every family sings` fails a haiku's first
line as seven syllables. CMUdict lists `every` as three syllables and as two, and
`family` likewise, and the five-syllable reading is how the line is spoken. The report
said `estimated_words: 0`, which was true: both words were looked up. So the signal a
caller uses to leave a guessed verdict unscored could not catch it. A dictionary answer
was wrong because only part of the dictionary was read. Of the 3,966 words in English's
everyday band 10, 92 have listed readings that differ in syllable count (`every`,
`family`, `different`, `actually`, `fire`, `hour`). Across CMUdict the figure is 1,592
of 117,493 alphabetic headwords.

A second, smaller disagreement belongs here too (U3 review M3). `describe()` called the
two `definitional_*` rows `exact`, yet their reports could be `estimated`: a source
word that no gloss resolves is left out of the score and counted in
`estimated_words`. Two published surfaces disagreed about the same row.

## Decision

**A line meets a syllable count when some combination of its words' listed readings
does.** This is ADR 0014's reading, applied to counting. Packs gain two methods.
`syllable_counts(word)` returns every count the listed pronunciations give, and whether
the word was looked up. `line_syllable_counts(line)` returns every total some choice
gives. The second is a set of small integers, not a product of choices, so a line of
many ambiguous words costs nothing extra. Neither method is on the `LanguagePack`
protocol, which is `runtime_checkable`. The procedures read both with `getattr`, so a
third-party pack without them keeps its one count. `syllable_count` is unchanged and
still answers with the first form, and its answer is always a member of
`syllable_counts`.

The rows that read it are `syllable_count`, `haiku`, `tanka`, `senryu`, `cinquain`,
`englyn`, `hendecasyllable`, `alexandrine`, `renga`, `haibun` and `arca_musarithmica`.
Each accepts a line when any of its totals meets the count. `monosyllabic_prose` accepts
a word when one of its readings is a monosyllable. `double_dactyl` accepts the
double-dactylic word when six is one of its counts. A word that English reads through
its stem (0.3.2's `awakes` from `awake`) takes every form of the stem, and stays an
estimate: `amblings` is two syllables or three, as `ambling` is.

**German keeps its first transcription.** German Wiktionary's pronunciation list for a
headword also carries the transcriptions of its inflected forms. `du` lists eight,
including `ˈdaɪ̯nɐ` (*deiner*), so reading every form would count `du` as two
syllables. The English list is CMUdict's variants of one word, and the German list is
not, so the reading applies only where the list means the same thing.

**French returns its one line total.** French counts a line and not its words (ADR
0034), so it overrides `line_syllable_counts` exactly as it overrides `line_syllables`.
A test requires any pack that overrides the second to override the first.

**`Evidence.basis` gains `ambiguous`**: the dictionary lists more than one reading of the
word, and the checker accepted any of them. It applies to syllable, stress and rhyme
evidence alike, so the value means one thing throughout: `every` as `2 or 3 syllables`,
and `bog` rhyming on `AA1 G/AO1 G`. A metre word marked this way is one the scan was
free to read another way, and its `value` is the form the scan fitted (`every` as `10`),
or every form it tried when the line does not scan. Above `MAX_COMBINATIONS` the scan
reads first forms only, and the evidence then says `dictionary`. `ambiguous` is not an estimate, so it does not make
`Report.estimated` true. `dictionary` now means the word was read one way.
`SCHEMA_VERSION` moves to 1.2. A parser that holds 1.1's closed set of two values would
refuse the third. The schema guard therefore records the basis values for each version
as well as the keys.

**`lexicon.glosses` joins the capabilities that make a row `heuristic`.** A gloss lookup
guesses nothing, but it can leave words unjudged, and `Report.estimated` already counts
that. `multiple_constraint` reads `heuristic` too: its `requires` cover only its own
logic, and its entries may name any row, so a description of the row cannot know whether
a call composes one that estimates (`BaseProcedure.requires_from_params`, ruling R-F5).
The rule now has no exceptions: a row that `describe` calls `exact` never reports
`estimated`.

## Consequences

The syllabic rows are more lenient, and that is the cost. A line accepts every total
some choice of readings gives, rather than one: each ambiguous word can add a total per
extra reading, and the set never reaches beyond the span between the line's lowest and
highest readings. `actually` alone gives three (2, 3 or 4). A writer who meant the three-syllable
`every` in a line one syllable long passes as surely as one who meant two. The checker
cannot know which reading the writer meant, which is the same position ADR 0014 took
for stress.

Each dimension is satisfied on its own, so a word may count on one reading and rhyme or
scan on another. In `englyn`, which judges syllables and rhyme in one checker, `fire`
can make a six-syllable line as one syllable while rhyming with `higher` on its
two-syllable key. ADR 0014 already let metre and rhyme choose separately, and a
composite already mixed readings across its constraints; `englyn` is the one row where
this change brings the mix inside a single checker. Coupling one reading per word
across dimensions would be a new design, not a fix. Within one dimension the readings
agree: on all 117,493 alphabetic CMUdict headwords, the set of syllable counts equals
the set of stress-pattern lengths exactly. In CMUdict, 1,508 of the 1,592 ambiguous words differ by one syllable. The
other 84 differ by two to five, mostly abbreviations and names that CMUdict also
spells out letter by letter. Some of those are ordinary words, so a line now passes
with `cod` read as three syllables (C.O.D.), `ins` as three, or `rep` as five. The
English words among them, `actually` (2, 3 or 4) and `politically` (3 or 5), are
readings a speaker uses.

**No verdict in the golden corpus moved.** Re-measured over all 687 cases, every
`satisfied` and every `score` is unchanged. The golden texts were written to pass, or to
fail for a named reason, under the first reading, and none of them turns on an ambiguous
count. What moved is evidence: 61 entries in 31 cases go from `dictionary` to
`ambiguous`. All of them are stress or rhyme evidence on the sonnet, stanza and rhyme
rows, in English and in German. Five of those entries also change `value`, the metre
form now being the one the scan read: `temperate` in Sonnet 18 is `100/10` (was
`100`), since that line does not scan and both forms were tried. None of the syllable
rows' cases contains an ambiguous word. The verdicts that move are outside the corpus, on texts like the audit's.

A violation that no reading meets now names every reading: `found` says
`4, 5 or 6 syllables` where it said `6 syllables`. This is the format `line_metre` uses
when it widens a length message. A caller that parsed one integer out of `found`
breaks. `found` was never under the stability promise.

German stress and rhyme read every Wiktionary transcription when this ADR was written,
inflected forms included. That is why the German sonnet and ballade cases showed
`ambiguous` evidence, and it let a German metre scan on a reading that belongs to
another form of the word. ADR 0057 ended the asymmetry: German stress and rhyme now
read the first transcription only, as syllable counts do, and German evidence is never
`ambiguous`.

`arca_musarithmica`'s generator still sets each phrase at its first reading's length.
It refuses a phrase whose first reading the tablet cannot set, even when another reading
could be set and the checker would accept it. A generator that does less than its
checker accepts is the safe direction, and the round-trip harness stays green.

The two `definitional_*` rows and `multiple_constraint` now read `heuristic` in
`describe`, which moves the published split from 87 exact and 46 heuristic to 84 and 49.
A caller that routed on `exact` to skip uncertainty handling will now handle those three
rows, which is the point. A composite of exact rows is described more cautiously than it
runs; its report's `estimated` stays false.
