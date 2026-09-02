# denckring — letter classification and the folding seam

**Date:** 2026-09-02
**Status:** designed, not started
**Scope:** the three jobs `pack.vowels()` is doing at once, the parameter side of the diacritic fold, and the `slenderizing` generator that fails its own checker
**Branch point:** `9472ff0` (155 catalogued · 130 implementable · 121 implemented · 121 validated · 25 not mechanically checkable · 0 instruments)

This answers Findings 1 and 2 of the MCP language sweep
(`docs/superpowers/plans/2026-09-02-mcp-language-sweep.md`), which are one cause. It is
the first chapter since chapter 3 to answer a defect report rather than a coverage metric,
and the report is this project's own.

## Purpose

Six rows misbehave under **default** parameters in German or French, and one of them
breaks the project's thesis. `fold_diacritics` defaults to `true`; the text side folds and
the parameter side does not.

| Row | Default-params failure | Language |
|---|---|---|
| `supervocalic` | unsatisfiable — folded text can never contain `ä ö ü` | de, fr |
| `univocalic` | `vowel: "ä"` unsatisfiable; `found: "a"` against `expected: "ä"` | de |
| `bivocalic` | `vowels: "äö"` unsatisfiable, same shape | de |
| `monoconsonantal` | `consonant: "ß"` unsatisfiable | de |
| `acrostic` / `telestich` / `double_acrostic` | a `ß` target is unsatisfiable; `expected: "ss"` against a one-character `got` | de |
| `slenderizing` | **`apply` output fails its own checker** | de |

All six declare `languages: ["en"]` — `univocalic` adds `de` — and reach the other
languages only through computed `runs_in` (ADR 0029). That does not excuse a wrong verdict,
but it bounds what the fix may claim: **no editorial `languages` value changes here.**

`kangaroo_word` appears in the sweep's Finding 1 table and is **not** in scope. It points
at Finding 3, French elision, and belongs with `s_plus_7`.

The sweep also reports French `monoconsonantal("yoyo")` as a defect. **It is not one**,
and establishing why is the substance of D2: these rows are defined on letters, and a
letter's phonetic function is a reading they do not declare.

## The measurements that chose the design

Reproduced on the branch point, not argued:

```
de supervocalic "Faust bewegt hier Idole."  → satisfied=False, missing ä ö ü
fr monoconsonantal "yoyo"                   → satisfied=True, consonants: 0
en monoconsonantal "yoyo"                   → satisfied=True, consonants: 2
```

**Folding the vowel set repairs German for free and does not repair French.**

| pack | `vowels()` | folded |
|---|---|---|
| en | `aeiou` | `aeiou` |
| de | `aeiouäöü` | `aeiou` |
| fr | `aeiouyàâäéèêëîïôöùûüÿ` | `aeiou` **`y`** |

German's eight fold to exactly the five the definition publishes. French folds to six,
because `y` is a French vowel letter — so consistent folding alone leaves `supervocalic`
demanding six against a published *"each of the five vowels exactly once"*.

**The French `yoyo` result is a convention difference, not a bug — but the phonetics
behind it are real, and they are far wider than `y`.** Both `y` in `yoyo` are /j/,
consonants. A flat `frozenset` cannot express a letter whose class depends on position,
and every one of the three languages has such letters:

| | vowel letters doing consonant work | consonant letters doing vowel work |
|---|---|---|
| en | `y w u i` (+ `o`): `yes`/`myth`, `wet`/`cwm`, `quick`, `onion`, `one` | `l m n r` syllabic: `bottle`, `rhythm`, `button`, `bird` |
| de | `y i`: `Yacht`/`Physik`, `Familie`, `Nation` | `l n r`: `Vogel`, `laufen`, `Vater` |
| fr | `y i u ou`: `yeux`/`stylo`, `pied`, `huit`, `oui` | — mute `e` carries the syllable |

`rhythm` has two syllables and no vowel letter at all. French `ou` is a **digraph**, which
is the one item here that does not fit a per-character model.

The candidate rule — **a vowel letter before another vowel letter is a consonant** —
scored **30 of 34** on those cases:

| word | classes | |
|---|---|---|
| `yoyo` | `CVCV` | both `y` consonants — where the flat set says none |
| `myth` | `CVCC` | `y` a vowel — where English's flat set says none |
| `gym` | `CVC` | " |
| `happy` | `CVCCV` | " |
| `stylo` | `CCVCV` | French /stilo/ |
| `pays` | `CVVC` | French /pɛi/ |
| `yeux` | `CVVC` | |
| `crayon` | `CCVCVC` | the one approximation: `y` does double duty in /kʁɛjɔ̃/ |

Three of the four misses were probe error — it indexed the first occurrence, so it tested
the wrong `i` in `million`, `Familie` and `Linie`. The genuine miss is German `Quelle`,
where `qu` is /kv/.

**But applying that rule to the letter-play rows is measurably wrong**, and this is what
decided D2:

```
en onion    vowel letters oio  → oo   UNIVOCALIC in o
en quick    vowel letters ui   → i    UNIVOCALIC in i
en million  vowel letters iio  → o    UNIVOCALIC in o
fr oui      vowel letters oui  → i    UNIVOCALIC in i
fr huit / lui / nuit           → i    UNIVOCALIC in i
```

No *Word Ways* editor accepts `onion` as an o-univocalic.

**`en.py` already carries both readings, and already keeps them apart:**

```
en.py:19  _VOWELS      = frozenset("aeiou")        # letter-play
en.py:22  _VOWEL_GROUP = re.compile(r"[aeiouy]+")  # syllable counting
```

The phonetic reading lives in the syllable path, where `_SYLLABIC_LE` already encodes the
syllabic-consonant class. The flat set is the orthographic reading, and its exclusion of
`y` is a choice rather than an oversight.

## Decisions

**D1. `vowels()` is split three ways, not two.** The sweep says `pack.vowels()` does two
jobs. Reading the seven call sites says three, and only one of them is a classification
question at all:

| method | kind | returns | consumers |
|---|---|---|---|
| `vowels()` | unchanged | every character *written* as a vowel, accented forms included | `word_ladder:93` alphabet widening; the classifier's default |
| `vowel_inventory()` | new | the base vowel letters the language names — `aeiou` in all three packs | `supervocalic` only |
| *ambiguous letters* | new | the letters `letter_classes` decides contextually: `y`, and French's `ÿ` | the two methods above |
| `letter_classes(word)` | new | one `"vowel"`/`"consonant"` per alphabetic character, **phonetically** | `spoonerism` only |

`word_ladder` is the reason `vowels()` keeps both its name and its meaning: it widens an
alphabet with diacritic variants and asks no question about vowelhood at all. Renaming it
would make that call site read as a classification it is not.

`univocalic`, `bivocalic`, `monoconsonantal` and `source_compare`'s two rows
(`homoconsonantism`, `homovocalism`) keep the flat `vowels()` reading — see D2.

**D2. The contextual rule is licensed by `phonemes`, so it goes to `spoonerism` alone.**
The split is by row, not by language.

`univocalic`, `bivocalic`, `monoconsonantal` and `supervocalic` are `family: letter`,
sourced to Bombaugh (1867) and *Word Ways*, and declare
`requires: [tokens, alphabet, fold_diacritics]` — **no `phonemes`**. `homoconsonantism`
and `homovocalism`, the two `source_compare` rows, declare the same. A glide rule in any
of them is a row making a pronunciation judgement while advertising that it works on
letters alone: the defect class ADR 0030 fixed twice in one day. The measurement above
is what it costs — `onion`, `quick`, `million`, `oui`, `huit`, `lui` and `nuit` all become
univocalics.

`spoonerism` is the one consumer that declares `phonemes`, and `_letter_onset` already
calls itself "a written stand-in for the phonetic boundary it cannot reconstruct" and
already labels itself an approximation. The rule belongs there, where it is both correct
and licensed, and it should carry the **whole** glide inventory rather than `y` alone:
en `y w u i o`, de `y i`, fr `y i u ou`.

*The cost, stated plainly:* French `monoconsonantal("yoyo")` keeps reporting
`consonants: 0`. Under French orthographic convention `y` is a vowel letter, so that is
the consistent answer for a row defined on letters — but it is consistent, not obviously
right, and a caller who reads `yoyo` as /jojo/ will disagree. It also leaves en and fr
answering differently for the same text, which is a convention difference this design
declines to erase. Whether a text with zero consonants should satisfy `monoconsonantal`
at all is a separate verdict question, deliberately not settled here.

*Rejected:* one rule in `BasePack` for all three languages. It measured correct
linguistically and flipped zero golden cases, but zero flips is evidence rather than
proof, and correctness for the phonetics is not licence for rows defined on orthography.

**D3. The parameter side folds the way the text side folds.** A `fold_letter` helper in
`core/text.py`, applied at every site comparing a parameter against `letter_spans` output.
This is the whole of Finding 1 outside the vowel question, and `fold_diacritics: false`
stops being the workaround it is today.

**D4. A single-letter parameter that folds to several characters is refused, by name.**
`ß` folds to `ss`, `œ` to `oe`. `invalid_params`, saying which letter and why, and naming
`fold_diacritics: false` as the way to use it as one letter. This replaces
`slenderizing`'s current `degenerate_output` advising `allow_identity=true`, which points
at the wrong cause and would return the untouched text as a slenderizing.

Matching the folded *sequence* instead was rejected: it turns a per-letter comparison into
a per-sequence one in four checkers, and makes `found` and `expected` differ in length in
every violation they emit.

**D5. `letter_classes` takes a word, not a text.** Context is orthographic and does not
cross a word boundary. Classification runs on the **unfolded** word — `ß` is a consonant
whether or not it has become `ss` — and a character folding to several letters gives its
class to each of them.

French `ou` is a **digraph**: /w/ in `oui`, `ouest`, `Louis` is carried by two letters. A
per-character return cannot say "these two are jointly one glide", so `FrenchPack` marks
**both** characters consonant in that position. That is an approximation, and it is the
same kind `_letter_onset` already declares — acceptable only because `spoonerism` is the
sole consumer and wants a boundary, not a count.

**D6. `slenderizing`'s `_produce` goes through the same letter model as `_check`.** Today
it compares `pack.fold_diacritics(ch).lower()` against an unfolded parameter and ignores
`params.fold_diacritics` entirely, which is why `ß` always survives a deletion the checker
then requires. This is D3 applied to a generator, and it is what restores the thesis.

## Components

### L0. The test net, first

`slenderizing` is in `PARAMETER_GATED` (`tests/test_round_trip.py:160`) *and* its golden
file pins `lang: en` at file level — unexercised twice over, which is why the row that
broke is the row excluded from the safety net. Close that before touching the checkers, so
the net **sees** `slenderizing` fail. Search for the *combination* rather than the row:
any `PARAMETER_GATED` id whose golden file sets a file-level `lang`.

`test_the_named_coverage_gap_is_the_whole_coverage_gap` is the assertion that keeps this
closed.

### L1. `fold_letter` and the parameter side

The helper, plus every parameter site, plus D4's refusal. No pack changes. On its own this
fixes `univocalic`, `bivocalic`, the acrostic family and German `monoconsonantal`.

**The acrostic family is three rows, not the two the sweep names.** `telestich` inherits
from `Acrostic`, so it is carried; `double_acrostic` has its own `letter_spans` use and
must be fixed and fixtured separately.

### L2. `vowel_inventory()`

`LanguagePack`, `BasePack` and the three packs. **The default folds first, then removes
the ambiguous letters** — measured, because removing them without folding answers eight
for German and nineteen for French:

```
                       minus-ambiguous        folded, minus-ambiguous
en                     aeiou                  aeiou
de                     aeiouäöü               aeiou
fr                     aeiouàâäèéêëîïôöùûü    aeiou
```

So all three packs inherit `aeiou` and none overrides. `supervocalic` is the only
consumer, and German `supervocalic` becomes satisfiable.

Under `fold_diacritics: false` the inventory stays `aeiou` while `ä` is still a member of
`vowels()` — so an unfolded German text carrying `ä` and all five base vowels satisfies
the row, and the `ä` is neither required nor counted against it. That is the intended
reading of a definition that says five.

### L3. `letter_classes(word)` — `spoonerism` only

`LanguagePack`, a `BasePack` default, and per-pack glide inventories: en `y w u i o`,
de `y i`, fr `y i u ou`. **One consumer**, `_letter_onset`, which today splits on flat
`vowels()` membership and so takes `yoyo`'s onset as empty. It is the only site licensed
for this, per D2, and the only one whose row declares `phonemes`.

The German inventory is the smallest and is loanword-bound (`Yacht`, `Physik`) apart from
`i` before a vowel (`Familie`, `Nation`). `Quelle` is the measured miss — `qu` is /kv/,
not a glide — so `GermanPack` excludes `u` after `q` explicitly rather than by rule.

This layer is **independent of L1 and L2** and can ship separately; it fixes no row in the
Purpose table and is an improvement to an approximation, not a defect fix. If it slips,
nothing in L0–L2 or L4 waits on it.

### L4. `slenderizing`

D6, and the `degenerate_output` message replaced per D4.

### L5. Golden cases

German and French cases for each repaired row, at **default** parameters — the values no
fixture supplies today, which is the sweep's finding about the fixtures. `ß` and an
accented parameter each get a case asserting the D4 refusal.

## Testing

The four-command gate, plus `eval --all` and `status`, plus `apps/explorer`'s own gate if
any catalogue row moves. None is expected to.

Two properties carry the weight:

- **Round-trip.** `slenderizing` leaves `PARAMETER_GATED` (L0) and the existing property
  asserts `apply` output satisfies its own checker, in German, under defaults.
- **Fold symmetry.** A new property: for every affected row, a verdict under
  `fold_diacritics: true` on folded input agrees with the verdict under
  `fold_diacritics: false` on the equivalent unfolded input. This is the invariant the
  seam violates, stated once rather than per row.

A regression test pins D2's boundary directly: `onion`, `quick`, `million`, `oui`, `huit`
and `nuit` must **not** be univocalics. Those are the words a later glide rule leaking
into the orthographic rows would silently reclassify, and the test names why.

Compare the **violation list** against each case name, not just `satisfied` — chapter 6's
trap 2, where a French `kangaroo_word` negative passed for the wrong rule.

## Out of scope

`kangaroo_word` and the French elision seam (Finding 3, with `s_plus_7`/`n_plus_7`).
Findings 4 through 7 — the French capitalisation trade, `missing_capability`'s remedy,
the published-contract disagreements, localisation fallback. The `apply_params.source`
contract from the English run. No editorial `languages` value and no catalogue definition
changes here; if `supervocalic` should claim `de` now that it can be satisfied, that is a
separate editorial decision.

## ADR

One ADR, recording D1, D2 and D4 — the three that change a published contract. D2 is the
substantial one: it decides that a row's `requires` list licenses which reading of a
letter it may take, and that orthography and phonetics are separate readings the packs
must keep apart. Its Consequences carry the `yoyo` cost and the en/fr divergence stated
in full above.
