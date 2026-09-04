# denckring — the calculator word

Date: 2026-09-04
Status: approved, not implemented

## Purpose

Add one catalogue row, `calculator_word`: a word that a seven-segment display can
write, entered as digits and read by turning the machine over. German folklore
gives the clearest example — `7353`, flipped, is `ESEL`.

The row is worth adding for three reasons beyond the joke. It is the first row
whose constraint is a property of a *machine* rather than of an orthography or a
lexicon, so it tests whether the catalogue can hold one honestly. It runs in all
three languages without new data, which no other row added since chapter 6 has
managed. And its generator inverts the usual direction: the digits are the source
material and the words are produced from them, which the apply spine (ADR 0025)
supports but nothing yet exercises from a non-linguistic input.

## The measurements that chose the design

Every figure below was measured on 2026-09-04 against the installed packs, not
reasoned about. The reproduction script is in Testing.

### Corpus yield, by mapping table

The letter alphabet is what sets corpus size; a digit that maps to a letter
already in the set adds nothing.

| Table | en | de | fr |
|---|---|---|---|
| BEGHILOS (`0 1 3 4 5 6 7 8`, and `9`) | 304 | 216 | 207 |
| + `2→Z` | 321 | 275 | 250 |
| + `2→Z`, `2→R` | 643 | 652 | 631 |

The folk extension doubles the corpus on its least defensible entry. See D2.

### Diacritic folding

| | en | de | fr |
|---|---|---|---|
| strict spelling | 304 | 216 | 207 |
| accents and `ß` folded | 304 | **242** | **356** |

Folding gains German 26 words (`Geheiß`, `Geiß`, `Blöße`, `Bö`, …) and French 149
(`blessé`, `biglé`, `bilobée`, …). English is unaffected — it has no accented
words inside the alphabet. See D3.

### Enumerable sources per pack

| pack | `lexicon.graded_words` | `lexicon.nouns` | yield from each |
|---|---|---|---|
| en | yes (77,078) | yes (56,468) | 304 / 289 |
| de | **no** | yes (184,040) | — / 216 |
| fr | yes (125,343) | yes (44,746) | 207 / 164 |

German has no `graded_words`: SCOWL ships in `denckring-en-data` only (ADR 0028),
and French gained its own in chapter 6. `lexicon.words` is membership
(`is_word`) and cannot be enumerated. See D5.

### The ambiguity `9→G` introduces

`6` and `9` both land on G, so a word containing G has more than one digit
spelling.

| pack | words containing G | of |
|---|---|---|
| en | 108 | 304 |
| de | 100 | 216 |
| fr | 58 | 207 |

Roughly a third of every corpus. See D4.

### Provenance actually verified

Verified: Michael Quinion, *World Wide Words*, "Beghilos" (2009); and Dalzell &
Victor, *The Concise New Partridge Dictionary of Slang and Unconventional
English* (2014, ISBN 978-1-317-62511-7, p. 2060), cited by Wikipedia's
`Calculator spelling`. Both place the practice in the 1970s with the arrival of
consumer LED calculators.

**Not verified, and therefore not cited:** a *Word Ways* article, "The Word
Calculator", exists in Butler University's archive but returned HTTP 403. The
Leibniz item in the backlog is blocked for exactly this reason — an unverified
citation is worth less than nothing here — and this spec follows the same rule.

Four attested decodings independently confirm the table this spec adopts:
`07734` = `hELLO`, `5318008` = `BOOBIES`, `53177187714` = `hILLBILLIES`, and
`378193771` = `ILLEGIBLE`, the last of which uses `9→g`. All four were verified
against the table by decoding them, not by reading them off a web page.

## Decisions

### D1. The table is a module constant, not a pack capability

`prisoners_constraint` reads its forbidden set from the pack's `letter_shapes`
capability, because ascenders and descenders genuinely differ by orthography.
Seven-segment geometry does not: the display is the same machine in Nuremberg,
Boston and Lyon. The table therefore lives beside the checker as a constant, the
way `chronogram.VALUES` holds the Roman numerals, and `letter_shapes` is **not**
in `requires`.

Cost: a reader who has internalised `prisoners_constraint` will expect the pack
to own this and has to be told otherwise. The `notes` field says so.

### D2. `2` maps to nothing; the table is fixed, with no widening parameter

Rotating a seven-segment glyph by 180° swaps `a↔d`, `b↔e`, `c↔f` and fixes `g`.
Under that transform:

| digit | segments | rotated | reads as |
|---|---|---|---|
| 0 | a b c d e f | a b c d e f | O |
| 1 | b c | e f | I |
| 2 | a b d e g | a b d e g | **itself — no letter** |
| 3 | a b c d g | a d e f g | E |
| 4 | b c f g | c e f g | H |
| 5 | a c d f g | a c d f g | S |
| 6 | a c d e f g | a b c d f g | G |
| 7 | a b c | d e f | L |
| 8 | all | all | B |
| 9 | a b c d f g | a c d e f g | G |

`2` is rotationally symmetric. `2→Z` is a visual pun on the printed digit, not a
property of the display, and `2→R` is weaker still — a mapping in which one digit
yields two different letters is not a function, and `7222` would have four
readings. Both are refused.

Cost, stated plainly: this is the expensive decision. It forgoes roughly half the
reachable corpus in every language (en 643→304, de 652→216, fr 631→207) to keep
the row's claim about the machine true. A future maintainer who wants the folk
table should reopen this decision rather than quietly add a parameter, because a
parameter would let the row publish a geometry it does not have.

### D3. `fold_diacritics` defaults to **false**, inverting the project default

Every other row defaults to folding. This one must not, because the display is
the artefact: a calculator cannot write `Geheiß` — it writes `GEHEISS` — and it
cannot write `blessé`. Under folding both are accepted as calculator words, which
is false about the machine.

Cost: de 242→216 and fr 356→207, and one row out of 156 whose fold default reads
backwards to anyone scanning the catalogue. The parameter remains, so the lenient
reading stays reachable for a caller who wants "displayable up to accents"; the
default states which reading the row means.

This makes the row a `fold_diacritics` declarer, so ADR 0035's structural guard
in `tests/test_round_trip.py` applies: golden cases in a second language are
required. This spec provides all three.

### D4. G has two digit spellings; `check` accepts both, `apply` emits `6`

`6` and `9` both rotate onto G, and the display has no case, so `IGEL` is `7361`
and `7391` alike. The checker accepts either. The generator emits `6`, because
the practice's own name — *beghilos* — encodes g from 6.

Cost: `apply` is not the exact inverse of `check` for any word containing G, which
is a third of every corpus. `test_round_trip.py` still passes, because it asserts
that a generator's output satisfies its own checker, not that the digits round-trip
byte-for-byte. A test pins the asymmetry so it cannot be mistaken for a defect.

The attested `ILLEGIBLE` is the sharpest illustration and is used as a golden case
for exactly that reason: the form in circulation is `378193771`, with `9` for the
`g`, while this row's generator emits `378163771`. Both decode to `illegible`, and
a reader who assumes one canonical spelling will read the other as a bug.

### D5. `apply_requires` floors on `lexicon.nouns`; the generator prefers `graded_words`

German cannot enumerate anything but nouns. Declaring `lexicon.graded_words`
would make German `apply` fail — and emit exactly the misleading
`missing_capability` remedy that this session's item 2 exists to fix. Declaring
`lexicon.nouns` and using only nouns everywhere would be symmetric but would cost
English 304→289 and French 207→164.

So: `apply_requires: [lexicon.nouns]`, the floor every pack meets and the honest
published claim, while `_produce` prefers `graded_words` where the pack declares
it. The row degrades rather than refusing.

Cost: the generator's corpus differs by language for a reason the published
capability list does not state. `notes` states it, and so does the ADR.

### D6. `layer: verfahren`

The calculator is tempting as the first `instrument` row (ADR 0033), and its
address space is real — radix 10, one digit per position. But D5 of ADR 0033
refuses a provenance meaning "contemporary, with no source", and a 1970s consumer
device is exactly that. The row is a writing procedure whose checker takes text;
it goes in the layer that holds writing procedures.

### D7. `id: calculator_word`

English id, because the practice and the term *beghilos* are Anglophone in
origin, even though the sharpest example is German. The `names` field carries
`Calculator word` / `Taschenrechnerwort` / `Mot de calculatrice`.

## Components

### L0. The test net, first

Before any behaviour: the reproduction script for the tables above, pinned as a
test so the figures cannot drift silently. It asserts the per-language yields and
that German declares no `lexicon.graded_words` — the fact D5 rests on.

### L1. `core/calculator.py` — the display

The table from D2 and two pure functions over it, with no language in sight:

- `to_digits(word) -> str | None` — the digit string, or `None` if any letter is
  undisplayable. Emits `6` for G per D4.
- `from_digits(digits) -> str` — the letters, reversed.

Separate module rather than living in the procedure, because the stage scene (L5)
needs the same table and a scene must not import a procedure's internals.

### L2. `procedures/calculator_word.py` — the checker

`CalculatorWordParams(DiacriticParams)` with `fold_diacritics` defaulted to
`False` (D3), `digits: str` (validated: digits only, non-empty), `words: int = 1`,
and `require_words: bool = True`.

`_check` walks `word_spans`, maps each word through L1, and reports:

| violation | when |
|---|---|
| `undisplayable_letter` | a letter outside the alphabet, with its offset |
| `wrong_digits` | the mapped reading is not `digits` |
| `wrong_word_count` | the text's word count is not `words` |
| `not_a_word` | `require_words` and `pack.is_word` says no |

`require_words=False` is the "combinations" mode: the mapping must hold and the
lexicon is not consulted. Following the `kangaroo_word` fix in ADR 0036,
membership is checked on the word **as written**, never on a folded form.

### L3. The generator

`_produce` partitions `digits` into `words` segments, decodes each, and keeps the
partitions whose every segment is a real word. Ranked by total frequency where
the pack supplies grades, else alphabetically. Returns `Produced` with candidates
and the truncation flag (ADR 0027), since a partition walk abandoned on budget
makes the result set smaller and `len(found) > limit` cannot see it.

Corpus per D5. The search is over partitions, not over the corpus per candidate:
decode first, then ask the lexicon, so the cost is in the digit string's length
rather than in the word list's size.

### L4. The catalogue row

```yaml
id: calculator_word
family: letter
kind: both
checkability: self
attribution: reference
attested: codified
source: >-
  Michael Quinion, World Wide Words, "Beghilos" (2009); the practice dates to
  pocket LED calculators of the 1970s
languages: [en, de, fr]
requires: [tokens, lexicon.words, fold_diacritics]
apply_requires: [lexicon.nouns]
deterministic: true
```

Plus `names`, `definitions` and `prompt_hints` in all three languages —
`prompt_hints` deliberately, since only 4 of 155 rows carry a German one and none
carry French, which is one of the disclosure gaps item 1 is about.

`notes` records D1, D4 and D5: where the table lives, why G has two spellings, and
why the generator's corpus differs by language.

### L5. The stage scene

A ninth scene, `calculator_word`: a seven-segment display, digits typed in, the
machine turned over. Same 1280×720 frame and the same `Scene` dataclass as the
existing eight; the route reads from `stage.py` and hands the result to a
template, touching no HTTP in the preparation.

Note the known wrinkle recorded in CLAUDE.md: `apps/explorer`'s family drawers
iterate `catalogue.load()` unfiltered. This row is a `verfahren` with a checker,
so it appears correctly; no drawer change is needed.

### L6. Golden cases

At least four per language. English `hello`/`07734` and `illegible`/`378193771`
(pinning `9→G` on an attested example, against the generator's own
`378163771` — D4); German `Esel`/`7353` and a two-word partition; French
`soleil`/`713705`. Negatives per language: an undisplayable
letter, a wrong digit string, and — per the chapter 6 trap — each negative's
**violation list** compared against the case name, not merely its boolean.

## Testing

Beyond the four-command gate and `eval --all`:

- **The measurement script is a test.** Yields per language, and German's absent
  `graded_words`.
- **Non-ASCII fixtures are proved red.** CLAUDE.md's trap: a test using ASCII to
  verify a diacritic fix cannot fail for its own reason, and one branch shipped
  three such tests. The fold cases use `Geheiß` and `blessé`, and each new guard
  is checked out against pre-fix code to confirm it fails there.
- **`test_round_trip.py`** — the row is constructive, so it enters the standard
  net. If it needs `PARAMETER_GATED` (the harness cannot supply a `digits` value
  that decodes), that is recorded with the reason, and ADR 0035's guard then
  requires the second-language golden case, which L6 supplies.
- **The G asymmetry is pinned**, so `apply` not inverting `check` byte-for-byte
  reads as a decision rather than a bug.
- **`apps/explorer`'s own gate** (`344 passed` before this row) after the scene
  lands, per the standing instruction to run it after any catalogue change.

## Out of scope

State before this chapter, and left as it was:

- **The folk table.** `2→Z` and `2→R` are refused by D2, not deferred.
- **A `mapping` parameter.** D2 refuses it on the same grounds.
- **The instrument layer.** D6 keeps this a `verfahren`; the catalogue still has
  0 instruments, and the first one still needs an early-modern source.
- **German `lexicon.graded_words`.** D5 works around its absence; supplying it is
  a data chapter, not this row.
- **Any MCP or explorer model work.** Workstream C has its own spec.
- **Multi-word partitions beyond `words`.** The generator honours the count it is
  given; it does not search for the best count.

## ADR

ADR 0037, recording D2, D3 and D4 — the refused folk table, the inverted fold
default, and G's two spellings. D1, D5, D6 and D7 are consequences stated in the
same record. Consequences admit costs rather than advertising benefits, per
`docs/adr/0015-lexicon-capabilities.md`.
