# 35. A letter has two readings, and a row's `requires` says which one it gets

## Context

The 2026-09-02 MCP language sweep's Findings 1 and 2 are one cause with two faces.

`fold_diacritics` defaults to **true**. The text side folded and the parameter side did
not, so a parameter was compared against text it could never equal: `vowel="ä"` reported
`found: "a"` against `expected: "ä"` in German, `vowels="äö"` the same, `consonant="ß"`
compared a two-character `expected` against a one-character `got`, and a `ß` in an
acrostic target was a "letter" no unit could match. Six rows were wrong under **default**
parameters — the values no golden fixture supplies, which is what the sweep found out
about the fixtures rather than about the rows.

One of the six broke the project's thesis. `slenderizing._produce` kept a character when
`fold_diacritics(ch).lower() != params.deleted`; `ß` folds to `ss`, which never equals one
letter, so `ß` always survived a deletion `_check` then required. Measured: `apply` gave
`Die traße war groß.` and its own checker scored that **0.412 with seven violations**,
under defaults, in the one row the safety net could not reach — `slenderizing` is in
`PARAMETER_GATED` *and* its golden file pins `lang: en` at file level, so it was
unexercised twice over.

The second face is not a fold at all. `pack.vowels()` was being asked several different
questions and answering all of them with one flat `frozenset`:

| pack | `vowels()` | folded | folded, less `y`/`ÿ` |
|---|---|---|---|
| en | `aeiou` (5) | `aeiou` | `aeiou` |
| de | `aeiouäöü` (8) | `aeiou` | `aeiou` |
| fr | `aeiouyàâäèéêëîïôöùûüÿ` (21) | `aeiouy` | `aeiou` |

`supervocalic` publishes *"each of the five vowels exactly once"* and read that set, so it
demanded German's eight and French's twenty-one against folded text that could never
contain an umlaut: **unsatisfiable in both languages**, permanently. English was correct
only because its readings coincide.

And the sweep filed French `monoconsonantal("yoyo")` — `consonants: 0`, satisfied — as a
defect. It is not one, and saying why is the substance of D2. Both `y` in `yoyo` are /j/,
but a flat set cannot express a letter whose class depends on where it stands, and every
language here has such letters: English `y w u i o` (`myth`, `cwm`, `quick`, `onion`),
German `y i` (`Physik`, `Familie`), French `y i u ou` (`stylo`, `pied`, `huit`, `oui`).
`rhythm` has two syllables and no vowel letter at all.

The candidate rule — *a vowel letter standing before another vowel letter is a consonant*
— scored **30 of 34** on the probe cases, with three of the four misses being probe error
and the genuine miss German `Quelle`, where `qu` is /kv/. It is a good rule. Applied to
these rows it is measurably wrong:

```
en onion    vowel letters oio  → oo   UNIVOCALIC in o
en quick    vowel letters ui   → i    UNIVOCALIC in i
en million  vowel letters iio  → o    UNIVOCALIC in o
fr oui / huit / lui / nuit     → i    UNIVOCALIC in i
```

No *Word Ways* editor accepts `onion` as an o-univocalic. `en.py` had already reached the
same conclusion and encoded it: `_VOWELS = frozenset("aeiou")` for letter-play,
`_VOWEL_GROUP = re.compile(r"[aeiouy]+")` for syllable counting. The two readings were
already separate; nothing named the separation, so nothing stopped a row taking the wrong
one.

## Decision

**D1. `vowels()` is split by the question asked, and only two of the three questions are
answered so far.** Reading its call sites finds three:

| method | returns | consumers |
|---|---|---|
| `vowels()` | every character *written* as a vowel, accented forms included | `word_ladder._alphabet`, `univocalic`, `bivocalic`, `monoconsonantal`, `source_compare` (`homoconsonantism`, `homovocalism`) and `spoonerism._letter_onset` — **six call sites across seven rows, two questions**, see Consequences |
| `vowel_inventory()` | the base vowel letters the language names | `supervocalic` alone |
| a contextual classifier | one class per character, **phonetically** | `spoonerism` alone — **not built**, see D5 |

`vowels()` keeps its name and its meaning because of the first of those call sites:
`word_ladder._alphabet` asks no question about vowelhood at all — it wants the diacritic
variants a ladder step may be — and renaming the method would make that site read as a
classification it is not. The other five sites, serving six rows, do ask a classification
question, and get the orthographic answer, which is the one D2 says they are entitled to.
So this split takes one of the three readings out of `vowels()` and leaves two behind it;
the Consequences say what that costs.

`vowel_inventory()` lives on `LanguagePack` with a `BasePack` default that folds the
written set and removes the ambiguous letters (`_AMBIGUOUS = frozenset("yÿ")`). **All
three packs answer `aeiou` and none overrides.** The fold is what does the work — not the
order of the two steps, which was claimed to be load-bearing during implementation and
measured false: folding `y`/`ÿ` never produces a base vowel, so reversing the steps gives
the identical result. What matters is that the fold happens **at all**. Without it the
inventory is German's eight and French's nineteen (twenty-one written vowel letters, less
the two ambiguous ones), against a definition that says five.

**D2. A row's `requires` list licenses which reading of a letter it may take.** The split
is by row, not by language.

`univocalic`, `bivocalic`, `monoconsonantal` and `supervocalic` are `family: letter`,
sourced to Bombaugh (1867) and *Word Ways*, and declare
`requires: [tokens, fold_diacritics, alphabet]` — **no `phonemes`**. `homoconsonantism`
and `homovocalism`, the two `source_compare` rows, declare the same. A glide rule in any
of them is a row making a pronunciation judgement while advertising that it works on
letters alone, which is the defect class ADR 0030 fixed twice in one day. The measurement
above is what it would cost: seven ordinary words silently become univocalics.

`spoonerism` is the one consumer that declares `phonemes`, and its `_letter_onset` already
calls itself "a written stand-in for the phonetic boundary it cannot reconstruct". That is
where the contextual reading belongs, whenever it is built.

*Rejected:* one contextual rule in `BasePack` for all three languages. It measured correct
linguistically and flipped zero golden cases — but zero flips is evidence, not proof, and
correctness about phonetics is not a licence for rows defined on orthography.

`tests/test_reading_boundary.py` pins the boundary by name rather than by implementation:
`onion`, `quick`, `million`, `oui`, `huit`, `nuit` and `lui` must not be univocalics, and
the four rows must not gain `phonemes` without this decision being revisited. It holds
whether or not the phonetic reading exists.

**D3. The parameter side folds the way the text side folds.** `core/text.py` gains
`fold_letter(ch, pack, *, fold)`, the parameter-side twin of `letter_spans`, applied at
every site that compares a parameter against a folded text. `fold_diacritics: false` stops
being the workaround it was. A target that is a phrase rather than a single letter is
*flattened*, so a `ß` claims the two units its two letters need: `acrostic`, `telestich`
by inheritance, and `double_acrostic`, which keeps its own copy of the expression and had
to be fixed separately — which is why the sweep's two acrostic rows are three.

**D4. A single-letter parameter that folds to several characters is refused, by name.**
`single_letter()` raises `InvalidParams` naming the field, the value, what it folded to,
and `fold_diacritics: false` as the way to use it as one letter. These callers compare
letter against letter, and a two-letter `expected` against a one-character `got` is not a
comparison a violation can report honestly. This replaces `slenderizing`'s
`degenerate_output` advising `allow_identity=true`, which named neither the cause nor a
remedy and would have returned the untouched text as a slenderizing.

Matching the folded *sequence* instead was rejected: it turns a per-letter comparison into
a per-sequence one in four checkers and makes `found` and `expected` differ in length in
every violation they emit.

**D5. The contextual classifier is deferred, and this record does not describe it as
built.** The design for it stands — one class per alphabetic character of a single
*unfolded* word, since context is orthographic and does not cross a word boundary; French
`ou` marked consonant on both characters because a per-character return cannot say "these
two are jointly one glide". None of it is implemented. `spoonerism._letter_onset` still
splits on flat `vowels()` membership, so French `yoyo` still has an empty onset and
English `myth` is still entirely onset. That is a known-wrong approximation that continues
to ship, and D2 is the reason it is the *only* place the fix would be allowed to land.

**D6. `slenderizing`'s `_produce` goes through the same letter model as `_check`.** D3
applied to a generator. It is what restores the thesis for that row, and its round-trip is
now exercised in German rather than only in the English its fixture pinned.

## Consequences

**German `supervocalic` is satisfiable for the first time, and its catalogue row still
says `languages: ["en"]`.** No editorial `languages` value moved here, deliberately —
whether a row should now claim a language it can be satisfied in is an editorial decision
and not a side effect of a bug fix. So the catalogue continues to understate what these
rows do, and `runs_in` (ADR 0029) is the only place a caller can see it.

**French `monoconsonantal("yoyo")` still reports `consonants: 0`, and English still
reports 2 for the same text.** Under French orthographic convention `y` is a vowel letter,
so zero is the consistent answer for a row defined on letters — consistent, not obviously
right. A caller who reads `yoyo` as /jojo/ will think the row is broken, will find the
sweep filed it as a defect, and will find this record saying it is not. The en/fr
divergence on identical input is a convention difference this decision declines to erase.
Whether a text with zero consonants should satisfy `monoconsonantal` at all is a separate
verdict question, still unsettled.

**A rule that measured correct was refused, and the cost is that the packs stay wrong
about phonetics.** The glide rule was right in all three languages and broke no golden
case. It is not here. Every consumer that would genuinely benefit — the syllable path
already has its own reading, `spoonerism` has none — waits on D5, and until then
`spoonerism` publishes an onset it knows is sometimes wrong. Deferring a measured
improvement to keep a boundary clean is a real price and it is being paid on purpose.

**`ß` and `œ` cannot be single-letter parameters at all while folding is on.** What used
to be an unsatisfiable report is now a raised `InvalidParams`, which is a harder failure
than callers previously met: a script that passed `consonant="ß"` and read `satisfied`
now gets an exception instead of `false`. The message names the remedy, and the remedy
works, which is the whole difference from the error it replaces.

**With folding off, an accented vowel is inert in `supervocalic`.** The inventory is
always the folded `aeiou`, while `ä` stays `ä` in the text — so it neither supplies the
`a` the row requires nor counts as a repeat of one. That is the intended reading of a
definition that says five, and it is also a rule nobody would guess from the outside;
`tests/test_vowel_inventory.py` measures both halves so it cannot drift silently.

**`vowels()` still answers two questions, not one.** D1 split off the inventory and leaves
`univocalic`, `bivocalic`, `monoconsonantal`, the two `source_compare` rows and
`spoonerism._letter_onset` reading the written set to decide which letters in a text *are*
vowels, beside `word_ladder._alphabet`, which asks something else entirely. Both readings
are the ones those rows are entitled to under D2, so both are correct — but the method's
name still covers two questions, and the next person to add a consumer has only this
record to tell them which one they are getting.

**`denckring eval --all` goes from 487 to 495 passing cases and `denckring status` does
not move**, staying `155 · 130 · 121 · 121 · 25` and `0 instruments catalogued`. This
chapter adds no catalogue row and implements no procedure; it fixes six that were already
counted as implemented, which is precisely the kind of change the coverage line cannot
see.

## Alternatives considered

**Folding the parameter inside each checker.** Five checkers, five chances to differ, and
the two acrostic rows had already proved the point by diverging with one copy each of the
same expression. `fold_letter` is one function on the seam that already owns folding.

**Leaving `fold_diacritics: false` as the documented workaround.** It is what the sweep
found callers doing, and it is a per-call instruction to disable a default that exists
because it is right. It also cannot fix `slenderizing`, whose generator ignored the
parameter entirely.

**Giving `supervocalic` a literal `"aeiou"`.** It would have fixed the row and put a fact
about which letters a language names into a procedure module, which is the placement ADR
0030 and ADR 0034 D1 both moved away from. A fourth pack with a sixth vowel letter would
then be wrong in a file nobody would think to look in.
