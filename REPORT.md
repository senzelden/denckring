# Taking the camp register out of the shipped Poesie-Automat lexicon

Branch `lexicon-register`, worktree `/home/claudeuser/denckring-purge`, base `84cf6af`.

Everything numbered below is read off a command's output. Where I judged rather than
measured, the sentence says so.

## What was wrong, measured

`src/denckring/data/devices/poesieautomat_2000.yaml` ships in the published package under
CC BY 4.0 and carried a set of fillers which, assembled by a board that emits 10^36 German
poems, read as camp and confinement imagery.

The brief's figure — 116 of 2400 lines over 400 seeds — reproduces exactly when the sweep
matches on the **bare noun** (`Lager`, `Draht`, `Zaun`, …) rather than on the whole filler
string. Matching whole filler strings from the brief's list of seventeen gives 103 instead.
I mention this because the two methods differ on `Das Lager` and `Der Draht`, which the
brief's list of seventeen does not name but its count silently includes — so the sweep that
produced 116 already had a wider scope than the list, and I have taken the wider one.

    seeds 0-399, 2400 lines, bare-noun match on the brief's 15 nouns
      BEFORE   lines carrying two or more:  116
      AFTER    lines carrying two or more:    0
      AFTER    lines carrying even one:       0

**Superseded by an exhaustive count.** Sampling seeds was the wrong instrument and I should
have reached for this one first. A line is six modules of ten, so there are 10^6 lines per
line-number and 6,000,000 in all, and the per-module counts of flagged flaps convolve into
the exact distribution of how many flagged words a line carries. No sampling, no seeds, and
it is milliseconds. On the brief's nineteen-filler scope:

                                  BEFORE                    AFTER
      assemblable lines           6,000,000                 6,000,000
      carrying at least one       1,633,120   (27.22%)      0   (0.00%)
      carrying two or more          244,620    (4.08%)      0   (0.00%)
      share of all 10^36 poems
      with such a line               22.686%                 0.000%

More than one poem in five, over the whole space, not over a draw. I wrote the convolution
myself rather than copy the figures handed to me, and it reproduces them to the digit. I
validated the harness the same way the reviewer did — planting `ventil`, a word that *is* in
the final file, as live fire: the sweep reports exactly **100,000** lines carrying it, which
is 1 flap of 10 in one module of line 2 times 10^5 for the rest, so the instrument finds
what is there and is not merely returning zero.

My wider list — the same nineteen plus `Gitter`, `Deckung`, `Kammer`, `Sirene`, `brennt`,
and 24 words of the family that were never in the file at all — over the same 6,000,000
lines: **2,023,020 (33.72%) → 0** carrying at least one, **344,920 (5.75%) → 0** carrying two
or more.

One discrepancy I could not close, flagged rather than smoothed over: the wider-family figure
relayed to me was 1,885,410 / 289,760, and mine is 2,023,020 / 344,920. I verified that only
the five extras fire on the old file — none of the 24 never-present words match anything — so
our flag sets are equivalent, and our nineteen-filler figures agree to the digit, which says
the convolution itself is sound. I tried the obvious variants (the brief's seventeen whole
filler strings with and without the five extras, and each extra added singly) and none
produces 1,885,410. I am reporting my own number and noting that theirs does not reproduce
here. Nothing in the change turns on it — both go to 0 — and the CHANGELOG carries only the
nineteen-filler figures, which are the ones that agree.

The wider sweep is what caught my own first attempt: I had put `der Ofen` into line 1 as a
foundry furnace, and the sweep reported 28 lines carrying it. A furnace is a furnace, but
`Ofen` has one unmistakable camp reading and the whole point of the rule is not to have to
adjudicate that per poem. It became `der Bagger`. I replaced `in Arbeit` with `in Pacht` on
the same reasoning, before any sweep flagged it — that one is judgement, not measurement.

## The twenty-five replacements

Nineteen from the brief's counted scope, five found by sweeping, and one — `ohne Zeugen` —
added at review on a neighbouring ground. Every module keeps exactly ten alternatives;
nothing was deleted.

| line | module | was | is | why the replacement |
|---|---|---|---|---|
| 1 | Subjekt | `der Zaun` | `der Bagger` | construction |
| 1 | Subjekt | `die Sirene` | `die Rinne` | swept: an alarm at night is a war term; a gutter is water |
| 2 | Subjekt | `Das Gitter` | `Das Ventil` | swept: *hinter Gittern* is the German for imprisonment |
| 2 | Adjunkt 1 | `mit Draht` | `mit Kalk` | concrete |
| 2 | Adjunkt 2 | `am Zaun` | `am Silo` | rail freight |
| 2 | Adjunkt 4 | `in Deckung` | `in Ordnung` | swept: *in Deckung gehen* is military; administration instead |
| 3 | Subjekt | `das Gleis` | `das Rohr` | workshop |
| 4 | Subjekt | `Die Mauer` | `Die Werft` | harbour |
| 4 | Subjekt | `Das Lager` | `Das Becken` | water — the one the brief's list omits and its count included |
| 4 | Adjunkt 1 | `unter Zwang` | `unter Deck` | harbour |
| 4 | Adjunkt 2 | `in Ketten` | `in Fahrt` | rail freight |
| 4 | Adjunkt 3 | `aus Draht` | `aus Kupfer` | foundry |
| 4 | Adjunkt 4 | `im Graben` | `im Rohbau` | concrete |
| 5 | Subjekt | `Die Sperre` | `Die Weiche` | rail freight |
| 5 | Subjekt | `Der Draht` | `Der Hebel` | workshop |
| 5 | Verb | `brennt` | `kippt` | swept: fire is named in the family; tipping is not |
| 5 | Adjunkt 3 | `im Lager` | `im Getriebe` | workshop |
| 6 | Subjekt | `die Kammer` | `die Waage` | swept: *Kammer* in this register is the gas chamber |
| 6 | Subjekt | `die Wache` | `die Zufahrt` | rail freight |
| 6 | Subjekt | `die Rampe` | `die Halde` | mining |
| 6 | Adjunkt 1 | `in Trümmern` | `in Pacht` | administration |
| 6 | Adjunkt 1 | `auf Posten` | `auf Achse` | freight |
| 6 | Adjunkt 3 | `in Flammen` | `in Wartung` | workshop |
| 6 | Adjunkt 3 | `im Moor` | `im Schilf` | water — *Moor* carries *Die Moorsoldaten* and the Emsland camps |
| 4 | Adjunkt 1 | `ohne Zeugen` | `ohne Strom` | denunciation beside `Die Anzeige`; see below |

Two intermediate choices of my own that the sweep or second thought rejected, recorded so
the reasoning is auditable: `der Ofen` → `der Bagger`, `in Arbeit` → `in Pacht`.

### `im Kessel`

The brief asks me to decide about `im Kessel`. **The word is not in this file.** `grep -rn
"Kessel" src/ tests/` exits 1, and so does the same grep for `Ventil` and `im Rohr` — the
boiler neighbours the brief names it against belong to the other cartridge, not this one.
So the decision is not whether to keep it but whether to introduce it, and I did not. In a
war register `Kessel` is an encirclement, and a word whose safety depends on which other
flaps happen to turn is exactly what this change exists to remove. `Das Ventil` and
`das Rohr` carry the boiler world instead, and neither has a second reading.

### What I judged and deliberately kept

These are within a step of the family and I left them; this is my judgement, not a
measurement. `Am Bahndamm`, `der Bahnhof`, `Die Bahn`, `Das Depot` — the brief names rail
freight as a permitted world, so rail infrastructure as such stays. `laut Liste`,
`laut Akte`, `laut Gesetz`, `vor Gericht`, `ohne Zeugen`, `auf Antrag`, `Das Archiv` —
administration, also named as permitted. (`ohne Zeugen` was on that list until review took it
off; see below.)
`ohne Dach`, `zerfällt`, `verwittert`, `bröckelt`, `der Rost`, `das Moos` — decay is the
lexicon's entire aesthetic and cannot be removed without destroying it; the brief's "ruins"
means *Trümmer*, which is gone. `der Ruß`, `unter Strom`, `aus Blei`, `in Reserve`,
`das Gerüst`, `das Gelände`, `der Dienst`, `das Tor` — each has one industrial reading and
nothing left in the lexicon can turn it.

`mit Kalk`, one of my own replacements, belongs on this list and I did not name it the first
time. *Kalk* is building lime nine times in ten and the register places it there, next to
`Unter Putz`, `aus Zement` and `der Estrich` — but *ungelöschter Kalk* is a real association
in German mass-killing literature, so it is a considered keep and not an oversight. It passes
the same test `unter Strom` passes: the file contains no `Grube`, no `Grab`, no `Erde` and no
`Leiche` for it to meet, so nothing can turn it. It is now named in the header so the next
editor knows it was weighed.

## Five poems, in full

Seed 6:

    Am Ersten wächst der Ruß gegen bar immer am Rand
    Das Wasser vor Ablauf laut Liste anscheinend auf Dauer am Hang
    Unter Putz rauscht der Estrich tagelang mit Mühe um neun
    Der Kanal auf Antrag zuweilen um zehn gegen Rost vor Schluss
    Die Straße hallt reichlich ohne Frist auf Reisen aus Eisen
    Im Februar die Halde in Pacht nach Wunsch demnächst in Wartung

Seed 8:

    Im Winter dröhnt die Halle unter Strom überall am Rand
    Die Brücke unter Eis aus Beton seither nach Frost ab Ostern
    Am Kanal rauscht das Moos vorerst seit Juni laut Gesetz
    Die Anzeige auf Antrag monatelang in Fahrt bei Frost aus Glas
    Der Regen wartet scheinbar seit Herbst im Umlauf aus Eisen
    Nachts die Zufahrt in Pacht ohne Uhr hierzulande vor Montag

Seed 15:

    Im Winter schweigt das Werk im Nebel inzwischen aus Not
    Der Nebel im Regen über Land anscheinend nach Frost in Ordnung
    Am Bahndamm rauscht die Pumpe regelmäßig seit Juni trotz Eis
    Das Ufer auf Antrag ringsum um drei auf Vorrat aus Glas
    Die Weiche wuchert tagsüber nach Bedarf vor Sonntag bei Hitze
    Um sechs die Halde in Pacht bei Sturm jüngst auf Abstand

Seed 25:

    Um sieben schweigt die Uhr gegen bar wochenlang am Rand
    Die Ampel im Regen trotz Rost teilweise aus Ton in Ordnung
    Am Ufer tropft der Schnee nebenan mit Mühe vor Gericht
    Das Ufer unter Deck durchweg um drei mit Blech im Rohbau
    Das Fenster kreist mutmaßlich vor Nässe vor Sonntag auf Umwegen
    Um sechs das Gelände aus Holz unter Sand jüngst im Schilf

Seed 82 — the second golden fixture, rebuilt:

    Montags vergilbt das Werk gegen bar inzwischen über Nacht
    Die Ampel unter Eis am Silo vielerorts bei Wind von Süden
    Im Depot schimmelt das Rohr zumeist unter Null in Sicht
    Der Turm ohne Zeugen sicherlich um drei bei Frost in Serie
    Die Fracht zittert erneut nach Bedarf auf Reisen gegen Hitze
    Abends das Tor auf Achse mit Glas mitunter ab Dienstag

The first three are the seeds the brief quoted as its worst samples — 6, 8 and 15 were
`die Rampe in Trümmern … in Flammen`, `die Wache in Trümmern`, `die Rampe in Trümmern`.

## Reading

I read **160 poems in full** — seeds 0-149 plus 1000, 2500, 4242, 7777, 9001, 12345, 31337,
65535, 99999, 123456 — and a separate pass showing each of the twenty-four final
replacements in three different assembled lines. All of that is my own judgement and none
of it is a measurement: every line I read was grammatical German, every subject was an
article-folded nominative singular of the right gender, every replacement PP was a genuine
prepositional phrase with its case inside it, `kippt` is third-person singular present and
intransitive, and no replacement landed in an adverb module, so the ADV rule is untouched.
Strangeness survives — `Der Regen kippt`, `Die Weiche gedeiht`, `Das Wasser mit Kalk` — and
that is the machine being allowed to be strange, which the file's own header defends.

`ohne Strom` went through the same pass after review. The line that prompted the change now
reads `Die Anzeige ohne Strom durchweg um drei mit Blech trotz Kälte` — a display without
power, which is what `Die Anzeige` should mean on a flap-board and is the sense the first
golden fixture is named for. Also read: `Das Archiv ohne Strom ständig aus Stein im Dunkeln
trotz Kälte`, `Die Werft ohne Strom durchweg trotz Wind auf Vorrat ab sofort`, `Die Bahn
ohne Strom sicherlich mit Kies vor Beginn ab sofort`, and five more. The denunciation
reading is gone and nothing replaced it.

## The machine is unchanged, measured

    combinations == 10**36            True
    fillers 360, distinct case-folded 360
    longest flap                      'Im November', 11 characters
    widest assembled line             1: 67   2: 69   3: 70   4: 67   5: 69   6: 71
    the same, before the change       1: 67   2: 69   3: 70   4: 68   5: 69   6: 71

Line 6 sat at exactly 71 before and sits at exactly 71 now; no line's budget rose anywhere.
Line 4 fell by one, because `ohne Zeugen` was that module's 11-character maximum and
`ohne Strom` is 10. (A first pass had line 1 at 66 because `die Sirene` is longer than
`die Rinne`; `der Bagger` put it back to 67.)

## The golden fixture

The second positive fixture spun four replaced flaps — `am Zaun`, `das Gleis`, `auf Posten`
and, after review, `ohne Zeugen`. Because every replacement is in place, seed 82 still turns the same flap
indices, so I rewrote the fixture text to that seed's new reading rather than hunting a new
seed. Both properties its `source` claims stay true and are still re-derived from the file
on every run: `test_the_two_positive_fixtures_share_no_flap` and
`test_the_positive_fixtures_show_no_word_twice` both pass. Fixture 1 (seed 5) uses no
replaced filler and is byte-identical.

## One test file touched, and why it is not a weakening

`test_the_stemmer_folds_the_endings_it_claims_to` illustrated the -e/-en fold with
`stem("Wachen") == stem("Wache")`. `Wache` is no longer a word this lexicon contains, so the
example now reads `stem("Waagen") == stem("Waage")` — the same ending pair, the same
assertion shape, a word the lexicon does carry. Verified directly: both sides are `waag`.
No guard was relaxed anywhere; no test threshold, family or cap was changed.

## Documentation

The device header had **no** section called "what is deliberately absent" — the closest
thing was the fourth rule's prohibition on manner adverbs. I added one, as a seventh
constraint. It records the rule, names the words as examples of why the isolated word is the
wrong unit, states the `im Kessel` and `ohne Zeugen` decisions, names `unter Strom`,
`mit Kalk` and `der Bagger` as considered keeps, and carries the exhaustive figures.

**A documentation error of my own, caught at review and corrected.** My first version said
this was "the one constraint no test can hold. The other six are properties of the strings
and are checked." That is false, and it was false in published data. The fourth rule — no
manner adverb, no bare negation — has no test in this repository either: I confirmed it
directly, `grep -rni "manner|negation|adverb" tests/*.py` returns nothing and none of the 26
tests in `test_poesie_automat.py` touches the ADV modules. Two of the seven rules rest on
judgement, not one. The header now says so and names which. I asserted a property of the
test suite from the header's own prose instead of checking the suite, which is the same
error the report contract warns about, in a place I did not think to look.

The header also now records that `kippt`, which replaced `brennt`, is the only one of the
thirty verbs that is ambitransitive. Rule 3 holds for all 10^36 readings regardless — no
schema offers a verb an object, so the intransitive reading is the only one the board can
assemble — but it is the cost of the removal and it is written down rather than left to be
discovered.

The CHANGELOG gets a `### Changed` entry — this is published data changing — and now carries
the exhaustive figures rather than my 116-of-2400 sample.

## Gates

    ruff check                 All checks passed!                    exit 0
    ruff format --check        440 files already formatted           exit 0
    mypy --strict src tests    no issues found in 408 source files   exit 0
    pytest (root)              3503 passed, 33 skipped               exit 0
    denckring eval --all       119 procedures · 353 passed · 0 failed exit 0

Baseline before any edit, same command: **3503 passed, 33 skipped**. `--extra mcp` cannot be
combined with `--all-extras` — `uv` rejects it — so mypy ran under `--all-extras`, which is a
superset.

An earlier draft of this report said a bare `uv run pytest` fails 380 tests here for want of
the synced workspace data packages. That was true when I measured it, against a cold venv,
and it is not true now: re-run at review time it gives **3503 passed, 33 skipped, exit 0**,
identical to `--all-extras`. It was a transient of my first sync and should never have been
written down as a standing fact about the repository. Withdrawn.

Catalogue: `154 catalogued · 128 implementable · 119 implemented · 119 validated · 26 not
mechanically checkable`. `src/denckring/data/catalogue.yaml` is not in the diff.

`apps/explorer` untouched.
