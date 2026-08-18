# Catalogue Backlog — Design

**Status:** approved, awaiting implementation plan
**Date:** 2026-08-18
**Branch point:** `218eed4` (152 catalogued · 129 implementable · 86 implemented · 86 validated)

## Goal

Implement the catalogued procedures that need no capability the language packs
lack, and correct the catalogue rows that turn out to be misdescribed.

The scoreboard moves **86 → 114 implemented**. The second product is seven
corrected catalogue rows, which is not a side effect: the catalogue is a
published CC BY 4.0 dataset and a row that misstates what a procedure needs is a
defect in it.

## Scope

Filtering the 66 unimplemented rows for `checkability != none` and no lexicon
capability beyond `nouns`/`words` gives 35 candidates. Reading their definitions
against what the packs can actually do splits them four ways.

### Group A — build as catalogued (23)

`requires` is accurate and the definition is mechanically decidable.

| Family | Rows |
|---|---|
| form (11) | `alliterative_verse`, `assonance_constraint`, `ballade`, `clerihew`, `curtal_sonnet`, `englyn`, `ghazal`, `ottava_rima`, `rondeau`, `sonnet`, `spenserian_stanza` |
| word (3) | `homoconsonantism`, `homovocalism`, `mathews_algorithm` |
| translation (2) | `lipogrammatic_translation`, `univocalic_translation` |
| procedural (5) | `column_reading`, `diastic`, `fold_in`, `mesostic`, `text_folding` |
| syntax (1) | `larding` |
| visual (1) | `boustrophedon` |

### Group B — build, after correcting `requires` (5)

Buildable, but the row understates what it needs. The capability exists in the
packs; only the declaration is wrong. This is the same class of defect as the
thirteen rows that declared `lexicon.nouns` while wanting word membership.

| Row | Correction |
|---|---|
| `word_ladder` | add `lexicon.words` — "every step being itself a word" is a membership test |
| `tmesis` | add `lexicon.words` — the halves either side of the insert must form a word |
| `haikuization` | add `phonemes` — "keeps only the rhyme-words" needs rhyme |
| `spoonerism` | add `phonemes` — "exchange of initial sounds", not initial letters |
| `univocalic_lipogram_pair` | **definition, not `requires`.** It reads "a text satisfying two or more named constraints at once", which is a generic composite constraint and not the univocalic-plus-lipogram pair the id names. Either the id or the definition is wrong; the definition describes the more useful procedure, so the row is renamed to `multiple_constraint` and the definition kept. |

### Group C — blocked on a capability that does not exist (4)

`requires` is corrected to name what the row actually needs; the row stays
unimplemented and is honestly blocked. Implementing these is out of scope.

| Row | Needs |
|---|---|
| `homosyntaxism` | part-of-speech tagging — "substituting new words of the same part of speech" |
| `verbless_prose` | finite-verb detection, which is the same capability |
| `homophonic_translation` | phonemes in the source *and* target language |
| `perverb` | a proverb corpus, which ADR 0020 says the project does not ship |

Two of these want the same thing. A `pos` capability is coherent future work and
would unblock more than these two rows, but it needs its own ADR and its own data
question, the way lexicon capabilities needed ADR 0015. It is named here so the
next person does not rediscover it.

### Group D — reclassified to `checkability: none` (3)

No program decides these against a source. Reclassifying is the same operation
ADR 0011 already sanctions, run in the direction opposite to `denckring`,
`cent_mille_milliards` and `wechselsatz`, which moved *into* decidable.

| Row | Why no acceptance criterion exists |
|---|---|
| `back_translation` | "translated onward and then returned" — deciding this needs translation, not comparison |
| `transduction` | a chain through several languages; the drift is the point and nothing measures it |
| `intralingual_translation` | "into another register or period of its own language" — register is not mechanically detectable |

Each reclassification records its reasoning in the row's `notes`, so the
catalogue states *why* it is undecidable rather than merely asserting it.

## Non-goals

- Implementing group C, or adding a part-of-speech capability.
- The 8 rows blocked on `lexicon.synonyms` / `antonyms` / `glosses`. Measured
  separately: the extracts are cheap (0.60 / 0.04 / 1.88 MB gzipped) and WordNet
  is already licence-cleared in `denckring-en-data`, but there is no build script
  to re-run and antonym coverage is only 6,041 lemmas, which is too thin for the
  two antonym rows as they are defined.
- Any change to `list_procedures()`, the MCP tool surface, or the CLI.

## Approach

Phased, extracting shared machinery from rows that already exist rather than
designing it ahead of them — the way `form_report` was extracted from real
sonnets.

### Phase 1 — the 11 form rows

These need no new machinery. `rhyme_scheme.form_report` already takes a scheme
and a metre and returns violations, and `petrarchan_sonnet` shows the whole
pattern in 43 lines. Each row is a params model, a scheme, a metre and a line
count.

Two need a decision rather than a declaration:

- **`sonnet`** is the generic row, while `petrarchan_sonnet` and
  `shakespearean_sonnet` are already implemented. It checks the properties every
  sonnet shares — fourteen lines, a volta-bearing rhyme scheme drawn from a named
  set — and delegates nothing. It must not silently accept a fourteen-line poem
  with no scheme at all.
- **`alliterative_verse`** and **`assonance_constraint`** are not stanzaic. They
  constrain sound within the line, so they sit alongside `form_report` rather
  than inside it.

### Phase 2 — three clusters, each extracting one helper

For each cluster: hand-write two or three rows, extract the helper from what they
actually needed, then write the rest of the cluster on it.

| Cluster | Rows | Helper |
|---|---|---|
| Selection from source | `mesostic`, `diastic`, `column_reading`, `haikuization` | the result is drawn from the source under a positional rule — verify every selected unit appears in the source, in order, and satisfies the rule |
| Letter-class preservation | `homoconsonantism`, `homovocalism` | one letter class preserved in order, the other replaced. One function, parameterised by class; the two rows differ only in which class is which |
| Rearrangement of source units | `boustrophedon`, `text_folding`, `fold_in`, `mathews_algorithm` | the result is the source's parts reordered by a rule — verify it is a rearrangement, then that the rule produced it |

`univocalic_translation` and `lipogrammatic_translation` need no helper. Their
checkable half is "the result satisfies this constraint", which delegates to the
existing `univocalic` and `lipogram` checkers; the translation half is not
decidable and the docstring must say so.

### Phase 3 — the remainder

`larding`, `tmesis`, `spoonerism`, `word_ladder`, `multiple_constraint`. Each is
its own shape and gets its own module.

## Generators

`check` for all 28. `apply` where the transform is mechanical, which is ten rows:

`boustrophedon`, `text_folding`, `fold_in`, `column_reading`, `mesostic`,
`diastic`, `haikuization`, `mathews_algorithm`, `spoonerism`, `word_ladder`.

`word_ladder` generates by searching `lexicon.words` for a path between two given
words, which is the most useful generator in the batch and the one most worth
getting right.

Deferred, with the reason recorded in each docstring: the rows whose generation
requires inventing content rather than transforming it — `larding` (insert a
*new* sentence), `homoconsonantism` and `homovocalism` (produce *new sense* from
the same skeleton), and the two translations.

ADR 0002 makes this legitimate: `apply` is optional and `kind` describes the
form, not the implementation. But the MCP surface now makes the gap visible — a
model reads `kind: constructive` from `describe_procedure` and gets
`not_constructive` from `apply_procedure` — so every deferral is a named decision
in the docstring, not an omission.

## German

All 35 rows are catalogued `languages: [en]`. 24 need only capabilities the
German pack already has, which is the `ideenwuerfeln` oversight waiting to happen
24 times.

The test is **linguistic, not mechanical**: declare `de` where the procedure means
something in German, not merely where `requires` is satisfiable. `alliterative_verse`
and `homovocalism` are germane; a row whose definition rests on English-specific
material is not. Every `de` declaration ships a German golden fixture, so the
claim is enforced rather than asserted.

## Testing

Per-row, following existing convention — `denckring new <id>` scaffolds all of it:

- **Golden fixtures**, at least two per row, satisfying and violating.
- **A Hypothesis strategy** generating conforming text, asserting `check`
  accepts it.
- **A round-trip property** for every row shipping `apply`: whatever `apply`
  produces, its own `check` accepts.
- **A German golden fixture** for every row declaring `de`.

Batch-level:

- `denckring eval --all` green. The scoreboard moves from
  `152 catalogued · 129 implementable · 86 implemented · 86 validated · 23 not mechanically checkable`
  to `152 catalogued · 126 implementable · 114 implemented · 114 validated · 26 not mechanically checkable`
  — `implementable` falls by the three rows group D reclassifies, and that fall is
  the point rather than a regression.
- The four catalogue corrections in group B and the three in group D are asserted
  by tests reading the catalogue, not merely edited into the YAML.
- A test asserting no implemented row declares a capability the row does not use,
  which is the defect group B is made of and the thing that would let it recur.

## Risks

**The definitions are the specification, and some are thin.** `column_reading`
("takes a printed page vertically") and `fold_in` ("fold one page lengthwise onto
another") describe physical operations on a printed page. Rendering them as
operations on a string is an interpretation, and the interpretation must be
written into the docstring or the row will mean whatever the implementation
happened to do.

**Group B may be larger than five.** Those five were found by reading 35
definitions closely. The batch should expect to find more understated `requires`
while implementing, and correcting them is in scope.

**`sonnet` overlapping two implemented rows** is the one place this batch can
make the catalogue worse, by creating a third row that accepts everything the
other two do plus anything else with fourteen lines.
