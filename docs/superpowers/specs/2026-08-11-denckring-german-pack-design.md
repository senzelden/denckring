# denckring — the German language pack

**Date:** 2026-08-11
**Status:** approved
**Scope:** sub-project 2 of 5 (see the Batch 1 spec for the decomposition)

## Purpose

Take the twelve Batch 1 procedures to German, and in doing so put the language-pack
interface under real load for the first time. English alone cannot prove that packs are
an interface rather than a dictionary: every capability question has a trivial answer in
an orthography with no diacritics, no `ß`, and no productive compounding.

German is deliberately taken before the lexicon-dependent batches. It costs no data —
Batch 1 needs no word list and no hyphenation — so the capability model can be tested
before anything depends on it, and before a copyleft lexicon forces the packaging
question.

## The defect this sub-project fixes

`prisoners_constraint` reads `letter_spans`, which folds diacritics. In German that
means `ß` becomes `ss` and `ä` becomes `a`, so the checker accepts *groß* and *Mädchen*
— but a written `ß` carries an ascender and an umlaut's dots sit above the x-height. The
constraint is about ink on the page, so it must see characters as written.

This is not a German-only bug: English *café* is wrongly accepted today for the same
reason. Adding a second orthography is what surfaced it, which is the argument for doing
this sub-project early.

## Decisions

| Decision | Rationale |
|---|---|
| Folding is a per-call parameter, defaulting to on | Whether *Mädchen* belongs in an a-lipogram is an editorial choice, not a library constant; Perec's translators had to make it too |
| The parameter is `fold_diacritics`, not `fold_umlauts` | The same switch governs French `é` and English *café*; naming it after German would be the German-identifier mistake in another form |
| It rides on the procedure's `Params` model | It then appears in `params_schema()` for the JSON contract and works as `--param fold_diacritics=false` with no extra plumbing |
| Shape questions never fold | An ascender is a property of the glyph, and folding is exactly what destroys that information |
| `exceeds_x_height` is a pack method, not a bigger character set | The "carries a mark above" half of the rule is orthography-general; only `ß` needs naming |
| German ships inside core, discovered by entry point | Batch 1 German needs no data, so core stays permissive and dependency-free while the third-party extension path gets exercised by a real pack |
| `alphabet()` stays the 26 base letters | Traditional German pangrams satisfy 26; demanding `ä ö ü ß` would be a stricter reading than the form's own practice |
| Strategies stay English-only | They exercise checker logic, which is language-independent; twelve German strategy modules would add no coverage |

## Design

### Fold policy

`letter_spans(text, pack, *, fold=True)` gains an argument. Unfolded still lower-cases,
so only the diacritic survives. A shared `DiacriticParams` base model carries
`fold_diacritics: bool = True`, inherited by the nine procedures that compare letters:
`lipogram`, `univocalic`, `tautogram`, `pangram`, `heterogram`, `palindrome`,
`beau_present`, `acrostic`, `telestich`.

Excluded, on purpose: `snowball` and `reverse_snowball` count word length rather than
letters, and `prisoners_constraint` must never fold.

### Glyph shapes

```python
def exceeds_x_height(self, ch: str) -> bool:
    """True when the written glyph rises above or drops below the x-height."""
```

`BasePack` implements it once: true when the lower-cased character is in
`ascenders() | descenders()`, or when its NFD decomposition contains any combining
mark. German overrides `ascenders()` to add `ß`; `ä`, `ö` and `ü` are caught by the
combining-mark half, as is French `é`. The method requires the `letter_shapes`
capability. `prisoners_constraint` iterates raw alphabetic characters and calls it.

### German pack

`GermanPack` declares the same four capabilities as English — `tokens`, `alphabet`,
`fold_diacritics`, `letter_shapes` — and no others. `syllables` and `lexicon.nouns`
raise, exactly as in English, which is what keeps the lexicon-dependent catalogue rows
honest about being unimplemented.

- `alphabet()` — the 26 base letters
- `vowels()` — `a e i o u ä ö ü`, so `univocalic` is correct in both fold modes
- `ascenders()` — `b d f h k l t` plus `ß`
- `descenders()` — `f g j p q y`

### Pack discovery

`_PACKS` is seeded with English directly, then merged on first lookup with whatever the
`denckring.lang` entry-point group advertises. German registers through that group from
inside the core wheel, so a third-party pack installs by exactly the same mechanism.
Seeding English directly rather than through the group means core never depends on its
own installed metadata being readable in order to find its own language.

### Fixtures

`lang` moves from file-level to per-case in `golden/<id>.yaml`, with the file-level
value as the default. German cases then live alongside English ones — one fixture file
per procedure still holds, and the docs gallery will show both languages together.

A new registry-wide invariant: **every language a procedure declares in `meta.languages`
must have at least one golden case in that language.** Without it, adding `de` to a
catalogue row would be an unbacked claim.

Every German fixture must be verified through the CLI before it is committed. Where no
public-domain German instance of a form exists, the case is constructed and its `source`
says so — never dressed up as authentic.

## Build sequence

1. Entry-point pack discovery, with English seeded directly.
2. `fold` argument on `letter_spans`; `DiacriticParams` across the nine procedures.
3. `exceeds_x_height`; `prisoners_constraint` stops folding. English *café* now
   correctly violates — a behaviour change, recorded in the changelog.
4. `GermanPack`, registered through the entry-point group.
5. Per-case `lang` in fixtures, plus the declared-language invariant. It fails at this
   point, which is the proof it is load-bearing.
6. German golden cases for all twelve procedures, each CLI-verified. Invariant goes
   green.
7. Catalogue rows to `languages: [en, de]`; ADRs 0009 and 0010; README and changelog.

## Acceptance

- `uv run pytest`, `ruff check`, `ruff format --check`, `mypy --strict src tests` all green.
- `uv run denckring eval --all` green, covering both languages.
- `uv run denckring check lipogram --lang de` works from a clean install.
- The declared-language invariant fails if a `de` fixture is deleted.
- `uv run denckring check prisoners_constraint` rejects *café* in English.

## Out of scope

Any lexicon, hyphenation or syllable data; the French pack; German compound handling;
`apply()`; Batches 2–4; the catalogue expansion to 500; CI and release rails. No network
access at runtime or test time.
