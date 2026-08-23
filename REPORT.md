# Rewriting the Poesie-Automat lexicon for a letter board

The 360 German fillers in `src/denckring/data/devices/poesieautomat_2000.yaml` were
replaced in place. Nothing else about the row changed: still six lines of six modules of
ten flaps, still `10**36`, same six line schemas, same three grammaticality rules, same
copyright position — the fillers were written **without reference to** Enzensberger's
lists, and word-for-word non-overlap with a list nobody here has read is neither
checkable nor claimed.

This is the third pass. Review found one contradiction of exactly the kind the new rule
exists to forbid, a meta-test that did not pin what its name claimed, and four wrong or
stale statements in my own report. All are addressed below, and every number here was
re-measured on the file as it now stands.

## The width, measured

```
fillers 360 distinct 360 longest 11 | 10^36: True | mean 8.98
hist {5: 3, 6: 20, 7: 42, 8: 58, 9: 94, 10: 78, 11: 65}
line 1: widest 67   line 2: widest 69   line 3: widest 70
line 4: widest 68   line 5: widest 69   line 6: widest 71
widest assembled line: 71
```

**Longest alternative: 11 characters**, sixty-five of the 360 at the cap. **Widest
assembled line: 71 columns**, reached only by line 6 — 16.7 px per cell at the showcase's
1184 px. Every filler is in NFC, so `len` is the cell count and `ä ö ü ß` cost one each.
Both figures are derived from the shipped file by `test_no_flap_is_wider_than_the_board`,
per-flap and per-line separately, because neither implies the other.

## The review items

### 1. `ab morgen` beside `ab Dienstag` — fixed, and the rule now covers the role

Zeile 6 could show two start-points, `ab morgen` in module 2 and `ab Dienstag` in module
5, and it was printed in my own report's uniform k = 6 sample. `ab X` is the same
semantic role as `seit X` pointing the other way, and two of them fix the same event
twice. My families were **lexical** — clock times, `seit`, `im <Monat>` — so `ab` was
never looked at.

Fixed by a clean swap: `ab morgen` and `auf Probe` exchange modules, so both `ab` flaps
sit in module 5 where alternatives can never co-occur. The seeds review cited:

```
seed  52  line 6: Abends der Nachbar auf Probe ohne Uhr jüngst ab Dienstag
seed 503  line 6: Seit Wochen die Kammer auf Probe nach Wunsch vormals ab Dienstag
```

Taking your weaker relative as well, for consistency rather than because you required
it: `vor Jahren` × `vor Tagen` in Zeile 4 is the same shape — one preposition, one role,
two quantities — and it is the exact parallel of `Seit Jahren` × `seit Tagen`, which I
had already fixed in the previous pass. `mit Kies` and `vor Tagen` exchange modules, so
both retrospective `vor` flaps now sit in module 1.

```
seed  92  line 4: Das Archiv vor Jahren längst mit Kies vor Beginn über Bord
```

`test_no_line_can_show_two_incompatible_time_anchors` now carries five families, framed
as **semantic roles** rather than prepositions that look alike: when on the clock, since
when (`seit`), from when (`ab`), how long ago (`vor Jahren`, `vor Tagen` — not `vor
Beginn`, which orders one event against another), and which month. Confinement holds
across the board:

```
line 1: clock[0] seit[0] ab[5] im-monat[0]        line 4: clock[3] seit[1] ab[5] vor-ago[1]
line 2: clock[2] seit[1] ab[5]                    line 5: clock[4] seit[3] ab[4]
line 3: clock[5] seit[4] ab[5]                    line 6: clock[0] seit[0] ab[5] im-monat[0]
```

The boundary is unchanged where you judged it correct, and the docstring now names what
stays permitted: `um acht` beside `gegen Abend`, `ab Mai` beside `Im November`, `seit X`
beside `ab Y`, `Freitags` beside `ab Dienstag`.

Both fixes were mutation-checked as clean swaps, so the family rule is what fires rather
than the duplicate-flap rule:

```
swap auf Probe <-> ab morgen : RED — test_no_line_can_show_two_incompatible_time_anchors
swap mit Kies  <-> vor Tagen : RED — test_no_line_can_show_two_incompatible_time_anchors
```

### 2. The meta-test now pins all eight endings

You were right that it left six of eight unchecked, and right about why that matters: with
`stem` reduced to `casefold` the detector stays green, because the fixed lexicon has no
exact-form echo either. The meta-test is the *entire* guard on the stemmer.

It now asserts one stemming outcome per ending, with the two longest checked against the
shorter ending they must be tried before. Dropping each entry from `_ENDINGS` in turn:

```
drop -ern : RED (pinned)     drop -em : RED (pinned)
drop -en  : RED (pinned)     drop -e   : RED (pinned)
drop -er  : RED (pinned)     drop -n   : RED (pinned)
drop -es  : RED (pinned)     drop -s   : RED (pinned)
```

`stem("Bahn") == "bah"` is one of the eight, and it pins a wart rather than a virtue —
the crudeness a one-strip list buys. Pinning it is the honest option.

### 3. Report corrections

**"109 seeds passed the first filter" was stale, not merely wrong.** It was measured
before the last three lexicon changes of the previous pass and never re-run. Measured now,
with the committed `stem()` and `_FUNCTION_WORDS`, over seeds 0–599:

```
seeds 0-599: filter 1 (no repeated stem) = 251; both filters = 111
first fully disjoint pair passing both filters: (5, 82)
```

Your 246 / 115 was the pre-move file; 251 / 111 is true of what ships. The outcome is
unchanged and independently re-derived: seeds 5 and 82 are still the first disjoint pair.

**"Sixteen fillers changed" was misleading.** Counted properly, per pass:

```
second-pass: 8 strings replaced in, 8 replaced out, 16 flap positions across 13 modules
   moved between modules (same string, new home): ab Freitag, ab Montag, auf Probe,
       um acht, um drei, um elf, um fünf, von Norden
   genuinely new strings: auf Antrag, aus Blei, aus Draht, aus Eisen, aus Stahl,
       aus Ton, bei Frost, per Zufall
third-pass:  0 strings replaced in, 0 replaced out, 4 flap positions across 4 modules
   moved: ab morgen, auf Probe, mit Kies, vor Tagen
   genuinely new strings: none
```

So the previous pass replaced **eight** strings and relocated eight more; this pass
introduced no new string at all and moved four flaps.

**"`ab Montag` beside `über Tage` remains reachable" was false**, and I asserted it twice.
My own clock reshuffle had moved `ab Montag` into Zeile 2 module 5, where `über Tage`
already lived:

```
ab Montag  x über Tage  : SAME module (line 2 m5) — cannot co-occur
```

**"a native reviewer has now cleared the bare-noun PPs" was over-attributed.** What
happened: a second reader gave a German-reader verdict on them, and on `per Zufall`.
Nobody established that reader's nativeness, and I should not have implied it.

### 4. The compound class the detector does not split

Correcting my previous disclosure, which named two examples as if they were the whole of
it. The class is **compounds whose head is also a free word elsewhere in the line** —
`-tag`, `-lauf`, `-mittag`. Verified reachable on the shipped file:

```
im Umlauf    x mit Vorlauf  : reachable together, line 5 m4 + m5
vor Mittag   x über Tage    : reachable together, line 2 m4 + m5
vor Mittag   x ab Montag    : reachable together, line 2 m4 + m5
vor Tagen    x ab Freitag   : reachable together, line 4 m1 + m5
tagsüber     x über Mittag  : reachable together, line 5 m2 + m4
tagsüber     x vor Sonntag  : reachable together, line 5 m2 + m4
Freitags     x ab Dienstag  : reachable together, line 6 m0 + m5
Freitags     x vor Montag   : reachable together, line 6 m0 + m5
```

Not decompounding stays the call — none of these reads as repetition, and a
decompounding rule would report many more that are worth even less.

### 5. Materials stack, and that was bought deliberately

The five `aus + Nomen` fillers that replaced the surplus `seit` anchors make more than one
material reachable in a line — `Die Fähre im Regen aus Beton teilweise aus Ton aus Blech`
(Zeile 2, seed 1484). That is on the permitted side: materials genuinely stack, the way a
fragment stacks any two adjuncts. It is what the `seit` → `aus` swap bought, and it was
seen rather than missed.

### 6. Preposition repetition, re-measured

The four flap moves shifted it slightly, so the figures are re-run, again exhaustively
over each line's 10⁶ readings:

```
surface form as printed: per line 7.0 / 16.3 / 10.8 / 25.5 / 15.4 / 26.1 % | whole poem 67.7 %
contractions folded:     per line 10.4 / 20.4 / 14.2 / 29.8 / 17.2 / 33.6 % | whole poem 76.4 %
```

**67.7 %** of all 10³⁶ poems repeat a preposition inside a line, counting surface forms as
the board prints them. Inherent in every PP module drawing on the same preposition series;
acceptable in my judgement, as the machine's metre.

## Five poems in full

**Seed 5** — the first golden positive:

```
Am Ersten schrumpft das Amt mit Bedacht immer laut Ansage
Der Asphalt im Regen über Land vermutlich auf Dauer laut Akte
Hinter Glas altert die Kantine bekanntlich vor der Tür per Zufall
Die Fabrik auf Antrag monatelang trotz Wind unter Last ab sofort
Das Blech kreist anderswo vor Nässe vor Sonntag bei Hitze
Freitags das Gerüst am Fenster im Abseits unentwegt aus Zement
```

**Seed 82** — the second, sharing no flap with it:

```
Montags vergilbt das Werk gegen bar inzwischen über Nacht
Die Ampel unter Eis am Zaun vielerorts bei Wind von Süden
Im Depot schimmelt das Gleis zumeist unter Null in Sicht
Der Turm ohne Zeugen sicherlich um drei bei Frost in Serie
Die Fracht zittert erneut nach Bedarf auf Reisen gegen Hitze
Abends das Tor auf Posten mit Glas mitunter ab Dienstag
```

**Seed 503** — the seed review cited for the `ab` clash, now clean in line 6:

```
Montags zerfällt das Amt nach Plan allmählich trotz Sturm
Das Wasser im Regen am Zaun vielerorts ohne Licht am Hang
Am Kanal versickert das Moos tagelang im Frost in Sicht
Das Lager auf Halde künftig mit Kies aus Draht im Graben
Die Sperre hallt zeitweilig bei Nacht über Mittag gegen Hitze
Seit Wochen die Kammer auf Probe nach Wunsch vormals ab Dienstag
```

**Uniform pass, k = 6** — the sample that carried the defect last time, now with one `ab`
in line 6 instead of two:

```
Um sieben gefriert die Halle aus Stahl allmählich ab Mai
Der Kies seit Mai um acht vielerorts aus Ton ab Ostern
Im Keller altert der Staub tagelang seit Juni ab Herbst
Die Mauer seit März monatelang um elf aus Draht ab sofort
Der Draht hallt tagsüber seit Herbst ab Mittwoch aus Eisen
Um sechs der Aushang auf Probe aus Blei hierzulande ab Dienstag
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

**My own reading. No parser was run.** Read in full against the lexicon as committed:

| pass | poems | lines | coverage |
| --- | --- | --- | --- |
| seed-drawn, seeds 500–599 | 100 | 600 | random, and it reaches Zeile 6 100 times |
| uniform, k = 0…9 | 10 | 60 | all 360 fillers exactly once |
| de-correlated, `(k + 3·line + 7·module) mod 10` | 10 | 60 | all 360 fillers exactly once |
| targeted: seeds 52, 92, 503, 84, 38, 1484, 1936 | 7 lines | 7 | the cases review named |
| **total on the final file** | **120 poems + 7 single lines** | **727** | |

Each of the four moved flaps appears in both structured passes, so each was read in
context at least twice. **Lines I judged ungrammatical: 0 of 727.**

Earlier readings, not counted because the lexicon changed after them: 140 poems against
the second-pass file, 210 against the first-pass file, 90 against a draft before that.

## Checks

| check | result |
| --- | --- |
| `uv run pytest` (root) | **3482 passed, 33 skipped** in 273.18s |
| `uv run denckring eval --all` | 119 procedures · **353 passed · 0 failed** |
| `uv run mypy --strict src tests packages/…` | **Success: no issues found in 409 source files**, exit 0 |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 439 files already formatted |

Baseline was 3482 / 33 and the count is unchanged: this pass added no test, it widened two
existing ones. Catalogue counts unmoved — `154 catalogued · 128 implementable · 119
implemented · 119 validated · 26 not mechanically checkable` — and `catalogue.yaml` is not
in the diff. mypy's exit status was read directly from `$?` on its own command, with
`--extra en --extra de --extra mcp` synced as CI does.

Re-verified after the flap moves: 360 fillers, 360 distinct case-folded, longest 11,
widest line 71, `combinations == 10**36`, both fixture texts unchanged and still sharing
no flap and repeating no stem.

## Concerns

1. **Grammaticality is my reading, not a proof.** 727 lines is 727 of 10³⁶. The guarantee
   is the closure your reader checked; the sampling is evidence that it holds. Three of
   the six schemas are verbless, and judgements about those are judgements about German
   fragments, where readers can differ.
2. **The contradiction rule is a judgement about where strange becomes broken.** This pass
   moved it once already, from lexical families to semantic roles, because `ab` was
   invisible to the lexical version. A sixth role could exist that none of us has named
   yet; the test makes adding one a two-line change, which is the best defence I have.
3. **The detector does not decompound**, so the eight pairs listed in §4 stay reachable and
   invisible to it. That is the call, not an oversight.
4. **67.7 % of poems repeat a preposition inside a line**, measured. Not a defect in my
   judgement.
5. **71 columns is the whole budget.** Line 6 reaches it; one twelve-character filler
   breaks the board, which is why the assembled width is pinned separately and why
   `durch Zufall` and `aus Versehen` were both rejected.
