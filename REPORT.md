# Rewriting the Poesie-Automat lexicon for a letter board

The 360 German fillers in `src/denckring/data/devices/poesieautomat_2000.yaml` were
replaced in place. Nothing else about the row changed: still six lines of six modules of
ten flaps, still `10**36`, same six line schemas, same three grammaticality rules, same
copyright position — the fillers were written **without reference to** Enzensberger's
lists, and word-for-word non-overlap with a list nobody here has read is neither
checkable nor claimed.

This is the second pass. The first was reviewed; six things came back, and all six are
addressed below. Sixteen fillers changed between the two passes, and everything measured
here was re-measured on the file as it now stands.

## The width, measured

Every number is the output of a command run against the committed file.

```
fillers 360 distinct(casefold) 360 longest 11 | 10^36: True | mean 8.98
hist {5: 3, 6: 20, 7: 42, 8: 58, 9: 94, 10: 78, 11: 65}
  line 1: widest 67   line 2: widest 69   line 3: widest 70
  line 4: widest 68   line 5: widest 69   line 6: widest 71
widest assembled line: 71
```

**Longest alternative: 11 characters**, sixty-five of the 360 at the cap; the longest
single words among them are `überwiegend`, `hierzulande`, `minutenlang`, `stundenlang`,
`bekanntlich`, `anscheinend`. Every filler was checked to be in NFC, so Python's `len` is
the cell count and `ä ö ü ß` cost one cell each.

**Widest assembled line: 71 columns**, reached only by line 6. At the showcase's 1184 px
that is 16.7 px per cell. Both figures are derived from the shipped file by
`test_no_flap_is_wider_than_the_board`, per-flap and per-line separately, because neither
implies the other.

## The six review items

### 1. The echo that survived, and the detector that was not in the repo

`"vor Tagen"` and `"bei Tag"` were both reachable in Zeile 4. My first-pass detector
compared exact word forms and reported nothing; `Tagen` and `Tag` are one word. Fixed by
`bei Tag` → **`bei Frost`**.

The detector is now **in the repo and runs on every test run**, as
`test_no_line_can_show_one_word_twice` in `tests/test_poesie_automat.py`, with the
matching made inflection-insensitive: umlauts folded, at most one of `-ern -en -er -es
-em -e -n -s` stripped, stopping before the stem falls under three characters. It
deliberately does **not** decompound, so `Montag`/`Tage` and `Umlauf`/`Vorlauf` stay
distinct — a decompounding rule would report pairs no reader hears as repetition. The
stemmer has its own test, `test_the_stemmer_folds_the_endings_it_claims_to`, so it cannot
pass by quietly folding nothing.

It reports zero for all six lines, and I re-ran it at one and at two stripping rounds to
check the result is not an artefact of the depth.

The three weaker relatives you listed are unchanged and deliberate: `ab Freitag`/`bei
Tag` is gone with `bei Tag`; `im Umlauf`/`mit Vorlauf` and `ab Montag`/`über Tage` are
different lemmas that happen to share a syllable, and I judge them below the line.

### 2. Two strings a German reader would write differently

- `nach Antrag` → **`auf Antrag`**. You were right and my first report was wrong to
  single it out for praise.
- `aus Zufall` → **`per Zufall`**. `durch Zufall` is the form you named, and I tried it:
  it is twelve characters and does not fit the board. `aus Versehen`, my second try, is
  also twelve. `per Zufall` is ten, is a live collocation, and keeps the word.

### 3. The fixture's showcase case

Reseeded. The first positive case is now **seed 5**, the second **seed 82**. The pair was
not picked by eye: I searched seeds 0–599 for poems where no word stem repeats *anywhere
in the poem* — cross-line, which the module-level rule cannot reach — and where no
preposition heads more than three of the thirty-six flaps, then took the first fully
disjoint pair among them. 109 seeds passed the first filter.

The cross-line property is now also enforced, by
`test_the_positive_fixtures_show_no_word_twice`, which re-derives it from the golden file
rather than trusting the `source` prose. Disjointness is still re-derived by
`test_the_two_positive_fixtures_share_no_flap`.

### 4. Ruling on the clock times — done, and extended

Ten clock times, six lines, at most one per line: the resolution is that alternatives
*within* one module can never co-occur, so the times cluster into a single module per
line. All ten survive.

```
  line 1: clock [0] | seit [0] | widest 67      line 4: clock [3] | seit [1] | widest 68
  line 2: clock [2] | seit [1] | widest 69      line 5: clock [4] | seit [3] | widest 69
  line 3: clock [5] | seit [4] | widest 70      line 6: clock [0] | seit [0] | widest 71
clock fillers: 10 | widest line: 71
```

Reading the result showed I had traded one contradiction for another: my first attempt
moved `im August` into a line-6 PP module, and the de-correlated pass at k = 9 promptly
produced *Im Februar die Kammer im August …*. Two months is the same defect as two clock times. So months stayed
where they always were — confined to the Zeitangabe module — and the two homeless clock
times went to the clock modules of lines 2 and 4 instead.

Having found that, I looked for the rest of the family and found three more pairs of
mutually exclusive **calendar `seit` anchors** — `seit Mai`/`seit April` in line 2, `seit
März`/`seit Juli` in line 4, `Seit Ostern`/`seit heute` in line 6 — plus `Seit
Jahren`/`seit Tagen` in line 1 and `seit Herbst`/`seit Beginn` in line 5. Five fillers
became material PPs: **`aus Ton`, `aus Draht`, `aus Blei`, `aus Stahl`, `aus Eisen`**.
Each line now has exactly one `seit`-bearing module.

`test_no_line_can_show_two_incompatible_time_anchors` holds all three families. Where I
drew the line, and did not go further: `um acht` beside `gegen Abend`, or `Seit Jahren`
beside `über Nacht`, differ in granularity and stack the way a reader stacks them; `ab
Mai` names a start rather than a when and does not contradict a month. Those are strange,
not broken, and `Der Frost gedeiht` is kept for the same reason.

### 5. Report corrections

- The sentence about directional and manner PPs being kept out of "the four modules that
  sit in verbless lines" was **false** and is gone. Verbless lines 2, 4 and 6 hold eleven
  PP modules, and directionals do sit in them — `über Bord`, `von Norden`, `von Süden`,
  `über Land`. What is true and all I now claim: `nach Norden` is confined to verbed
  Zeile 3, and I avoided motion-goal PPs in the verbless modules where a fragment gives
  them nothing to attach to. That is a tendency in the drafting, not a property of the
  design.
- Concern 4 was mis-scoped and is rewritten. The rate that matters is a preposition
  repeated **within** one line, and I have now measured it exhaustively over each line's
  10⁶ readings rather than pointing at a pass:

```
surface form as printed:
  per line 7.0 / 16.3 / 10.8 / 26.1 / 15.4 / 27.1 % | whole poem 68.3 %
contractions folded (im=in, am=an, zur=zu):
  per line 10.4 / 20.4 / 14.2 / 30.3 / 17.2 / 34.6 % | whole poem 76.9 %
```

  So **68.3 %** of all 10³⁶ poems repeat a preposition inside a line, counting surface
  forms as the board prints them, and 76.9 % if `im`/`in` and `am`/`an` are counted as
  one. The cause is that every PP module draws on the same preposition series, not the
  ordering inside the modules — reordering would hide it from a uniform pass without
  moving the rate. I judge it acceptable: it reads as the machine's metre.
- `ruff format --check` reports **439** files, not 438.

### 6. Structural closure

Your second reader checked the closure rather than the sample, and that is the stronger
argument. I re-ran the same checks after the sixteen changes: all thirty verbs still
third-person-singular present intransitive with no separable particles; all sixty
subjects still article-folded nominative singular; all 180 PPs still self-contained; the
sixty adverbs still free of negations and manner adverbs; every verbless line's ADV slot
still followed by a PP to scope over. The five fillers I introduced are all `aus + Nomen`
material PPs, which touch none of those.

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

**Seed 367**:

```
Morgens stockt der Ruß im Nebel offenbar aus Not
Der Nebel gegen Nässe um acht jahrelang vor Mittag am Hang
Am Kanal schimmelt der Kran vorerst gegen Regen laut Gesetz
Die Anzeige gegen Ende ständig aus Stein aus Draht über Bord
Das Blech wartet tagsüber ohne Frist in Reserve unter Wert
Im Sommer die Kammer von Norden vor dem Bau nochmals aus Zement
```

**Uniform pass, k = 6** — every module showing its seventh flap, which is where most of
the new material PPs live:

```
Um sieben gefriert die Halle aus Stahl allmählich ab Mai
Der Kies seit Mai um acht vielerorts aus Ton ab Ostern
Im Keller altert der Staub tagelang seit Juni ab Herbst
Die Mauer seit März monatelang um elf aus Draht ab sofort
Der Draht hallt tagsüber seit Herbst ab Mittwoch aus Eisen
Um sechs der Aushang ab morgen aus Blei hierzulande ab Dienstag
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

**My own reading. No parser was run.**

Read in full against the lexicon as committed:

| pass | poems | lines | coverage |
| --- | --- | --- | --- |
| seed-drawn, seeds 300–419 | 120 | 720 | random |
| uniform, k = 0…9 | 10 | 60 | all 360 fillers exactly once |
| de-correlated, `(k + 3·line + 7·module) mod 10` | 10 | 60 | all 360 fillers exactly once |
| **total on the final file** | **140** | **840** | |

Coverage of the two structured passes was counted, not assumed. All sixteen changed
fillers appear in both structured passes, so each was read in context at least twice.

**Lines I judged ungrammatical: 0 of 840.**

Earlier readings, not counted in that total because the lexicon changed after them: 210
seed-drawn poems (seeds 90–299) and both structured passes against the first-pass
lexicon, and 90 poems against a draft before that. Those readings are what found the
fifteen first-pass echoes, `rostet der Rost`, and — in this pass — `Im Februar … im
August` at seed 419.

## Checks

| check | result |
| --- | --- |
| `uv run pytest` (root) | **3482 passed, 33 skipped** in 290.88s |
| `uv run denckring eval --all` | 119 procedures · **353 passed · 0 failed** |
| `uv run mypy --strict src tests packages/…` | **Success: no issues found in 409 source files**, exit 0 |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | **439 files already formatted** |

Baseline was 3478 / 33; the four tests added this pass — the stemmer, the echo detector,
the time-anchor rule, the fixture cross-line rule — account for the difference exactly.
Catalogue counts unmoved: `154 catalogued · 128 implementable · 119 implemented · 119
validated · 26 not mechanically checkable`, and `catalogue.yaml` is not in the diff.

mypy's exit status was read directly from `$?` on its own command. It needs `--extra en
--extra de --extra mcp` synced, as CI does; with only `--extra mcp` it reports four
unrelated import errors in the language-pack tests.

Re-verified after every change: 360 fillers, 360 distinct case-folded, longest 11, widest
line 71, `combinations == 10**36`, and the two positive fixtures sharing no flap.

## Concerns

1. **Grammaticality is my reading, not a proof.** 840 lines is 840 of 10³⁶. The guarantee
   is the closure your second reader checked; the sampling is evidence that the closure
   holds, not a substitute for it. Three of the six schemas are verbless, and every
   judgement about those is a judgement about whether a German fragment is well-formed,
   where opinions can differ. A native reviewer is worth more than another thousand
   samples, and one has now cleared the bare-noun PPs.
2. **The contradiction rule is a judgement about where strange becomes broken, not a
   measurement.** I drew it at mutual exclusivity within one granularity: two clock
   times, two months, two calendar `seit` anchors. `um acht` beside `gegen Abend` and
   `ab Mai` beside `Im November` are on the other side of that line, and someone could
   reasonably move it.
3. **The echo detector does not decompound**, by choice. `im Umlauf` beside `mit Vorlauf`
   and `ab Montag` beside `über Tage` remain reachable and are invisible to it. If a
   later reviewer wants those gone, the detector is in the repo and the rule is one
   regex away — but it will report pairs that are not worth changing.
4. **68.3 % of poems repeat a preposition inside a line**, measured exhaustively. Not a
   defect in my judgement — it reads as the machine's metre, and it is inherent in every
   PP module drawing on the same preposition series rather than in any orderable
   accident.
5. **71 columns is exactly the budget, with nothing spare.** Line 6 reaches it. One
   future twelve-character filler breaks the board, which is why the assembled width is
   pinned and not only the per-flap cap — and it is what caught both `aus Versehen` and
   `durch Zufall` this pass.
