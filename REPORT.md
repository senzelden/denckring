# Rewriting the Poesie-Automat lexicon for a letter board

The 360 German fillers in `src/denckring/data/devices/poesieautomat_2000.yaml` were
replaced in place. Nothing else about the row changed: still six lines of six modules of
ten flaps, still `10**36`, same six line schemas, same three grammaticality rules, same
copyright position. The device file's header keeps the two corrections it was reviewed
for — the ADV rule states the prohibition and then *describes* the classes actually
shipped rather than claiming an exhaustive "only", and the copyright note still says the
fillers were written **without reference to** Enzensberger's lists and does not claim
word-for-word non-overlap with a list nobody here has read.

## The width, measured

Every number below is the output of a command run against the file as committed, not an
arithmetic prediction.

```
fillers: 360 distinct (case-folded): 360
length histogram: {5: 3, 6: 20, 7: 42, 8: 57, 9: 91, 10: 80, 11: 67}
longest alternative: 11 characters
mean length: 9.0
  line 1: widest 67 cols, narrowest 43 cols
  line 2: widest 69 cols, narrowest 49 cols
  line 3: widest 70 cols, narrowest 46 cols
  line 4: widest 68 cols, narrowest 46 cols
  line 5: widest 69 cols, narrowest 50 cols
  line 6: widest 71 cols, narrowest 46 cols
widest assembled line over the whole board: 71 columns
1184 px / 71 cols = 16.7 px per cell
```

**Longest alternative: 11 characters.** Sixty-seven of the 360 sit at the cap;
`überwiegend`, `hierzulande`, `minutenlang`, `stundenlang`, `bekanntlich` and
`anscheinend` are the longest single words among them. `ä ö ü ß` were confirmed to count as one character each: every filler was checked
to be already in NFC (no combining marks), so Python's `len` is the cell count.

**Widest assembled line: 71 columns**, reached only by line 6, whose six modules each top
out at 11. Lines 1–5 top out at 67, 69, 70, 68 and 69. No line the board can show exceeds
71, which is the width the showcase is built for.

Both figures are pinned by `test_no_flap_is_wider_than_the_board`, which derives them
from the shipped file rather than restating them: the per-flap maximum against a cap of
11, and each line's widest assembly against 71. They are separate assertions because
neither implies the other — six flaps that each fit could still overrun the line if the
cap were ever raised for one module.

## Five poems in full

Spun off the board with `apply`. The first two are the golden fixture's positive cases.

**Seed 0** — also `eine-anzeige-die-der-automat-zeigen-kann`:

```
Um sieben gefriert der Wind gegen bar neuerdings laut Ansage
Der Kies gegen Nässe laut Liste anscheinend vor Mittag aus Blech
Im Schacht knistert das Gleis seitdem ohne Halt vor Gericht
Der Hafen mit Kies zuweilen über Eck gegen Rost in Serie
Die Straße gedeiht fortan mit Ansage in Reserve auf Umwegen
Um sechs das Gelände vor dem Amt nach Wunsch vormals im Moor
```

**Seed 8** — `eine-zweite-anzeige-die-keine-klappe-wiederholt`; all thirty-six of its
modules show a flap different from seed 0's:

```
Im Winter dröhnt die Halle unter Strom überall am Rand
Die Brücke unter Eis aus Beton seither nach Frost ab Ostern
Am Kanal rauscht das Moos vorerst seit Juni laut Gesetz
Die Anzeige nach Antrag monatelang in Ketten bei Tag aus Glas
Der Regen wartet scheinbar seit Herbst im Umlauf seit Beginn
Nachts die Wache in Trümmern ohne Uhr hierzulande vor Montag
```

**Seed 137**:

```
Mittags zerfällt die Halle auf Abruf überall aus Not
Die Fähre auf Sand am Zaun vielerorts mit Stempel zu Ostern
Im Keller versickert das Moos seitdem seit Juni um neun
Das Lager auf Halde abermals vor Tagen im Dunkeln über Bord
Die Fracht gedeiht anderswo auf Rädern aus Sorge bei Hitze
Um sechs das Gelände auf Posten im Abseits hierzulande auf Abstand
```

**Uniform pass, k = 0** — every module showing its first flap:

```
Morgens schweigt der Wind im Nebel immer am Rand
Der Nebel im Regen am Zaun wieder im Schnee am Hang
Am Kanal bröckelt der Kran weiterhin im Frost am Kai
Die Fabrik im Beton abermals am Deich im Dunkeln am Steg
Der Regen brennt erneut im Tunnel am Tresen im Lager
Abends der Bahnhof am Fenster im Abseits nochmals am Damm
```

**De-correlated family, k = 3** — `index = (k + 3·line + 7·module) mod 10`:

```
Im Winter schweigt der Ruß gegen bar angeblich um die Ecke
Der Kies nach Regen am Zaun jahrelang gegen Abend in Deckung
Am Ufer altert der Estrich weiterhin bei Nebel trotz Eis
Das Archiv vor Jahren monatelang aus Stein im Dunkeln im Graben
Das Signal zittert neulich seit Herbst aus Sorge im Lager
Im August das Gelände über Wasser vor dem Bau hierzulande aus Zement
```

## Grammaticality

**This is my own judgement, not a measurement.** No parser was run; I read the lines.

Sample sizes, all read in full against the lexicon as committed:

| pass | poems | lines | coverage |
| --- | --- | --- | --- |
| seed-drawn, seeds 90–299 | 210 | 1260 | random |
| uniform, k = 0…9 | 10 | 60 | all 360 fillers exactly once |
| de-correlated, `(k + 3·line + 7·module) mod 10` | 10 | 60 | all 360 fillers exactly once |
| **total** | **230** | **1380** | |

Coverage of the two structured passes was verified mechanically, not assumed: each was
counted and each filler appears exactly once per pass.

**Lines I judged ungrammatical: 0 of 1380.** Many are semantically absurd — `Der Frost
gedeiht`, `gefriert das Eis` — which is what the machine is for; none is broken German.

A further 90 seed-drawn poems (seeds 0–89, 540 lines) were read against a near-final
draft. That reading is what caught the defects listed below; the final lexicon differs
from that draft in sixteen fillers, so I am not counting those 90 towards the total.

What the reading changed, all of it stylistic rather than grammatical:

- Fifteen **same-line word echoes**, where two modules of one line could both show the
  same content word: `Der Hafen … am Hafen`, `Das Wasser … zu Wasser`, `Unter Putz … der
  Putz`, `trotz Wind … bei Wind`, and eleven more. I wrote a detector that enumerates the
  content words reachable in each line and reports any word reachable from two different
  modules of it; it now reports none for all six lines.
- One **verb/subject collision**, `rostet der Rost` (seed 53). The subject flap became
  `der Ruß`.

Neither was a grammar defect. I fixed them because a combinatorial machine produces its
collisions at scale and they read as flaws in the lexicon rather than as jokes.

## Register

The bureaucratic phrases went out by arithmetic. What eleven characters admits is short
concrete nouns and plain verbs, which is what the board can hold: `der Wind`, `das Eis`,
`der Ruß`, `im Nebel`, `am Kai`, `bei Ebbe`, `schweigt`, `rostet`, `knirscht`, `vormals`.
Enough of the civic vocabulary survives to keep the tone — `das Amt`, `ohne Antrag`,
`laut Gesetz`, `vor Gericht`, `nach Aktenlage` would not fit but `nach Antrag` does. The
mean filler is 9.0 characters.

## The three rules, still true of the design

1. **Article folded into the noun.** All sixty subject flaps are `Artikel + Nomen`
   (`der Wind`, `die Uhr`, `das Eis`), so no agreement is ever computed across modules.
2. **Everything after the subject is an adjunct.** All 180 PP flaps are preposition +
   phrase with the case inside; no module can contribute an argument.
3. **Every verb third person singular present and intransitive.** All thirty: `schweigt`,
   `rostet`, `bröckelt`, `versickert`, `erlischt`, `klirrt` and the rest. No separable
   verb, so no particle has to land where the board cannot reach.

Directional and manner-flavoured PPs were deliberately kept out of the four modules that
sit in verbless lines, since a fragment has no motion verb for them to attach to.

## Downstream

- `src/denckring/eval/fixtures/golden/poesie_automat.yaml` rebuilt from the new lexicon.
  Seeds 0 and 8 again turn out to be the disjoint pair — I searched for one rather than
  assuming, and `test_the_two_positive_fixtures_share_no_flap` re-derives the claim from
  the file on every run. The fixture's `source` no longer carries the note about seed 11,
  which was a fact about the old lexicon and would have been misleading here.
- `tests/test_poesie_automat.py`: two tests added, none removed.
  `test_no_flap_is_wider_than_the_board` pins the cap and the assembled width.
  `test_a_spun_poem_reads_back_as_the_flaps_it_was_spun_from` checks over 64 seeds that
  `segment` recovers the flaps that were actually turned — module boundaries within a
  line are unambiguous, which is a property of the strings and so belongs in a test on
  them rather than in the schema.
- `CHANGELOG.md`: the row's Unreleased entry gained a sentence on the width constraint.
  The row has never shipped, so this is an amendment rather than a `Changed` entry.
- Grepped for the old fillers across the repository. Outside the device file and the
  fixture the only hits were in `BRIEF.md`. `apps/explorer` was not touched.

## Checks

| check | result |
| --- | --- |
| `uv run pytest` (root) | **3478 passed, 33 skipped** in 318.84s |
| `uv run denckring eval --all` | 119 procedures · **353 passed · 0 failed** |
| `uv run mypy --strict src tests packages/…` | **Success: no issues found in 409 source files**, exit 0 |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 438 files already formatted |

The root suite was 3476 passed / 33 skipped at the base commit; the two added tests
account for the difference exactly. Catalogue counts are unchanged — `154 catalogued ·
128 implementable · 119 implemented · 119 validated · 26 not mechanically checkable` —
and `catalogue.yaml` is not in the diff.

mypy's exit status was read directly from `$?` on its own command, not through a pipe.
It needs `--extra en --extra de --extra mcp` synced, which is what CI does; with only
`--extra mcp` it reports four unrelated import errors in the language-pack tests.

## Concerns

1. **Grammaticality is my reading, not a proof.** 1380 lines is 1380 of 10^36. The
   guarantee rests on the module design, and the sampling is evidence that the design
   holds, not a demonstration that it does. Two of the six lines' schemas are verbless,
   and every judgement about them is a judgement about whether a German fragment is
   well-formed, where opinions can reasonably differ. A native reviewer would be worth
   more than another thousand samples.
2. **Some bare-noun PPs are journalistic rather than neutral.** `trotz Flut`, `trotz
   Rost`, `gegen Nässe`, `gegen Rost` drop the article the way a headline or a weather
   report does. I judge them grammatical; someone might judge them clipped.
3. **71 columns is exactly the budget, with nothing spare.** Line 6 reaches it. Any future
   filler at 12 characters breaks the board, which is why the test pins the assembled
   width and not only the per-flap cap.
4. **The uniform pass repeats a preposition down a line** — `auf Abruf … auf Dauer … auf
   Zeit … auf Halde … auf Rädern … auf Posten`. Grammatical, and it is an artefact of
   the flaps being ordered by preposition within each module, which is also what makes
   the de-correlated family read as varied as it does. I left it: any fix would either
   scramble the modules' internal order for no gain or reduce the prepositional variety.
