# denckring — letter classification and the folding seam

**Date:** 2026-09-02
**Status:** designed, not started
**Scope:** the two jobs `pack.vowels()` is doing at once, the parameter side of the diacritic fold, and the `slenderizing` generator that fails its own checker
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
| `monoconsonantal` | `consonant: "ß"` unsatisfiable; `y` misclassified in French | de, fr |
| `acrostic` / `telestich` / `double_acrostic` | a `ß` target is unsatisfiable; `expected: "ss"` against a one-character `got` | de |
| `slenderizing` | **`apply` output fails its own checker** | de |

All six declare `languages: ["en"]` — `univocalic` adds `de` — and reach the other
languages only through computed `runs_in` (ADR 0029). That does not excuse a wrong verdict,
but it bounds what the fix may claim: **no editorial `languages` value changes here.**

`kangaroo_word` appears in the sweep's Finding 1 table and is **not** in scope. It points
at Finding 3, French elision, and belongs with `s_plus_7`.

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

**The French `yoyo` result is not a vacuity bug.** Both `y` in `yoyo` are /j/ —
consonants. The defect is that a flat `frozenset` cannot express a letter whose class
depends on where it sits, and `y` is that letter in all three languages. The candidate
rule — **`y` is a consonant before a vowel letter and a vowel otherwise** — was measured
per position and is correct, identically, in en, de and fr:

| word | classes | |
|---|---|---|
| `yoyo` | `CVCV` | both `y` consonants — the French defect |
| `myth` | `CVCC` | `y` a vowel — the **English** defect, same cause |
| `gym` | `CVC` | " |
| `happy` | `CVCCV` | " |
| `stylo` | `CCVCV` | French /stilo/ |
| `pays` | `CVVC` | French /pɛi/ |
| `yeux` | `CVVC` | |
| `crayon` | `CCVCVC` | the one approximation: `y` does double duty in /kʁɛjɔ̃/ |

**The rule flips zero existing golden cases.** The only fixture text among the affected
rows containing a `y` is `univocalic`'s `"Persever, ye perfect men, ever keep these
precepts ten."`, where `ye`'s `y` precedes a vowel and is classed a consonant — exactly
as today.

## Decisions

**D1. `vowels()` is split three ways, not two.** The sweep says `pack.vowels()` does two
jobs. Reading the seven call sites says three, and only one of them is a classification
question at all:

| method | kind | returns | consumers |
|---|---|---|---|
| `vowels()` | unchanged | every character *written* as a vowel, accented forms included | `word_ladder:93` alphabet widening; the classifier's default |
| `vowel_inventory()` | new | the base vowel letters the language names — `aeiou` in all three packs | `supervocalic` only |
| *ambiguous letters* | new | the letters `letter_classes` decides contextually: `y`, and French's `ÿ` | the two methods above |
| `letter_classes(word)` | new | one `"vowel"`/`"consonant"` per alphabetic character of the unfolded word | `univocalic`, `bivocalic`, `monoconsonantal`, `source_compare`, `spoonerism` |

`word_ladder` is the reason `vowels()` keeps both its name and its meaning: it widens an
alphabet with diacritic variants and asks no question about vowelhood at all. Renaming it
would make that call site read as a classification it is not.

**D2. The contextual `y` rule lives in `BasePack`, and it changes English.** One rule for
three languages, because it measured identical in all three. English today treats `y` as
never a vowel, so `myth`, `gym` and `happy` gain a vowel under this rule.

*The cost, stated plainly:* this is a verdict change in English on texts no fixture
covers, in the most-covered language, and the sweep's own lesson is that golden fixtures
cannot see the parameter space around them. Zero measured flips is evidence, not proof.
The alternative — French-only, the ADR 0034 `line_syllables` pattern that changes nothing
by construction — was rejected because it would knowingly leave `myth` with no vowels in
English while fixing the identical defect in French, and this project treats a
half-applied rule as a defect rather than a caution.

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

Under `fold_diacritics: false` the inventory stays `aeiou` while `ä` remains a vowel by
`letter_classes` — so an unfolded German text carrying `ä` and all five base vowels
satisfies the row, and the `ä` is neither required nor counted against it. That is the
intended reading of a definition that says five.

### L3. `letter_classes(word)`

`LanguagePack`, `BasePack` with the D2 rule, and a `core/text.py` helper zipping it
against folded `letter_spans` per D5. Five consumers move onto it. French
`monoconsonantal("yoyo")` reports two consonants, for the right reason.

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

One ADR, recording D1, D2 and D4 — the three that change a published contract. D2's cost
belongs in Consequences and is stated in full above.
