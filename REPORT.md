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

    seeds 0-399, 2400 lines, my wider list of 43 (the 15 plus Gitter, Deckung,
    Kammer, Sirene, brennt, and 23 words of the family that were never in the file:
    Stachel, Baracke, Appell, Transport, Selektion, Krieg, Front, Waffe, Schuss,
    Asche, Rauch, Gas, Ofen, Grube, Zelle, Riegel, Schranke, Wachturm, Kolonne,
    Marsch, Flucht, Verhör, Haft)
      BEFORE   lines carrying two or more:  156
      AFTER    lines carrying two or more:    0
      AFTER    lines carrying even one:       0

The wider sweep is what caught my own first attempt: I had put `der Ofen` into line 1 as a
foundry furnace, and the sweep reported 28 lines carrying it. A furnace is a furnace, but
`Ofen` has one unmistakable camp reading and the whole point of the rule is not to have to
adjudicate that per poem. It became `der Bagger`. I replaced `in Arbeit` with `in Pacht` on
the same reasoning, before any sweep flagged it — that one is judgement, not measurement.

## The twenty-four replacements

Nineteen from the brief's counted scope, five found by sweeping. Every module keeps exactly ten
alternatives; nothing was deleted.

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
administration, also named as permitted; `ohne Zeugen` is the closest call of these and I
kept it because with the camp scaffolding gone it reads as a contract, not a killing.
`ohne Dach`, `zerfällt`, `verwittert`, `bröckelt`, `der Rost`, `das Moos` — decay is the
lexicon's entire aesthetic and cannot be removed without destroying it; the brief's "ruins"
means *Trümmer*, which is gone. `der Ruß`, `unter Strom`, `aus Blei`, `in Reserve`,
`das Gerüst`, `das Gelände`, `der Dienst`, `das Tor` — each has one industrial reading and
nothing left in the lexicon can turn it.

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

## The machine is unchanged, measured

    combinations == 10**36            True
    fillers 360, distinct case-folded 360
    longest flap                      'Im November', 11 characters
    widest assembled line             1: 67   2: 69   3: 70   4: 68   5: 69   6: 71
    the same, before the change       1: 67   2: 69   3: 70   4: 68   5: 69   6: 71

Line 6 sat at exactly 71 before and sits at exactly 71 now; no line's budget rose. (A first
pass had line 1 at 66 because `die Sirene` is longer than `die Rinne`; `der Bagger` put it
back to 67.)

## The golden fixture

The second positive fixture spun three replaced flaps — `am Zaun`, `das Gleis`,
`auf Posten`. Because every replacement is in place, seed 82 still turns the same flap
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
constraint explicitly marked as the one no test can hold, because it is a judgement about
register and not a property of the strings. It records the rule, names the words as
examples of why the isolated word is the wrong unit, and states the `im Kessel` decision.
The CHANGELOG gets a `### Changed` entry — this is published data changing.

## Gates

    ruff check                 All checks passed!                    exit 0
    ruff format --check        439 files already formatted           exit 0
    mypy --strict src tests    no issues found in 408 source files   exit 0
    pytest (root)              3503 passed, 33 skipped               exit 0
    denckring eval --all       119 procedures · 353 passed · 0 failed exit 0

Baseline before any edit, same command: **3503 passed, 33 skipped**. Note that both figures
need `uv run --all-extras`; a bare `uv run pytest` in this worktree fails 380 tests because
the workspace data packages are not synced, which is an environment fact and not a
regression. `--extra mcp` cannot be combined with `--all-extras` — `uv` rejects it — so
mypy ran under `--all-extras`, which is a superset.

Catalogue: `154 catalogued · 128 implementable · 119 implemented · 119 validated · 26 not
mechanically checkable`. `src/denckring/data/catalogue.yaml` is not in the diff.

`apps/explorer` untouched.
