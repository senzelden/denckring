# Handover — `denckring.proteus`

**Scope.** One procedure: permute the words of a line, keep the permutations that still
satisfy a metrical constraint. Latin is the historical case; German and English ship in the
first pass, French is designed for but not built. This is deliberately *not* a prosody
library — it is a filter with a pluggable syllable source.

**Taxonomy.** `variatio ordinis` (Leibniz). Author-stated procedure: Scaliger, Bauhusius,
Puteanus; the counting problem is Leibniz's, *De Arte Combinatoria* (1666).

---

## Design — one seam

Everything language-specific sits behind two small objects. The permutation loop and the
foot matcher never learn what language they are in.

```
Syllabifier   word -> [Reading, ...]        # a Reading is a tuple of marks
Meter         (marks, word_boundaries) -> parse | None
```

A `Reading` is one admissible scansion of a word. Words with two admissible readings
(Latin `tibi`, `Virgo`; German unstressed particles) return several — the filter accepts a
permutation if *any* combination of readings parses. This ambiguity is not an edge case, it
is where the historical disagreements live.

`Meter` implementations:

| Meter | Marks | Languages |
|---|---|---|
| `QuantitativeFeet` | long / short | la |
| `AccentualFeet` | stressed / unstressed | de, en |
| `SyllableCount` | count + hemistich boundary | fr |

The existing hexameter matcher works unchanged under `AccentualFeet` — German naturalised
the classical foot grammar (Klopstock, Goethe), so one implementation covers both. Keep the
matcher generic over the mark alphabet; do not branch on language inside it.

## Language packs

**de** — first target. Stress marks. Meters: dactylic hexameter, iambic. No full lexicon in
v1: ship a hand-marked fixture lexicon of a few hundred words, plus a heuristic
(stem-initial stress; `ge- be- ver- ent- er- zer-` unstressed; compounds take primary
stress on the first element). Heuristic readings carry `confidence="heuristic"`; fixture
entries always override.

**en** — CMUdict gives stress digits directly, so coverage is cheap and exact. Meter:
iambic pentameter. English hexameter is not worth supporting.

**fr** — interface only in v1. No stress, so the constraint is syllable count plus caesura
at the hemistich (alexandrine 6+6). The real work is *e muet* and elision, which is why it
is deferred rather than half-built. Do not force French into `AccentualFeet`.

**Adding a language** should mean writing a `Syllabifier` and picking a `Meter`. If it
requires touching the matcher, the seam is in the wrong place.

## Rules

- **Fail loud on unknown words.** Raise, never silently drop or guess a reading. A scansion
  filter that guesses is a scansion filter that lies.
- **Never hardcode a count.** Counts are computed, always, and depend on the ruleset.
- **Guard the factorial.** 8 words = 40,320; 10 = 3.6M; 12 = 479M. `generate()` is lazy;
  `count()` refuses above `max_words` (default 9) unless passed explicitly; longer lines go
  through `sample(k, seed=...)`.

## API sketch

```python
from denckring.proteus import ProteusVerse

v = ProteusVerse.from_line(
    "Tot tibi sunt dotes, Virgo, quot sidera caelo",
    lang="la", meter="hexameter",
    spondaic_fifth=False, require_caesura=True,
)
v.count()                       # 40,320 permutations filtered
next(iter(v.generate()))        # lazy generator of word tuples
```

Ruleset flags belong on the constructor, not on `count()` — the eval harness varies them.

## Evals

The fixture is the parameter sensitivity, not a golden number. Record the rival counts for
Bauhusius's line and assert that *some* ruleset reproduces each:

| Count | Claimant | Year |
|---|---|---|
| 1022 | Puteanus (printed) | 1617 |
| 2196 | Prestet | 1675 |
| 3096 | Wallis | 1685 |
| 2580 | Leibniz | 1686 |
| 3276 | Prestet | 1689 |
| 3312 | Bernoulli | 1692 |
| 2880 | Whitworth; Hartley | 1902 |

History in Knuth, *TAOCP* §7.2.1.7. Add one hand-marked German hexameter line (a line from
*Hermann und Dorothea* via DTA is the obvious source) and one English pentameter line as
smoke tests — a handful of words each, not a corpus.

## Open questions

1. Does the stress lexicon live in package data or behind an optional extra (`denckring[de]`)?
   CMUdict is large enough that I would make English an extra and keep the German fixture inline.
2. Should `Meter` and `Syllabifier` sit in a shared `denckring.prosody` from day one? Later
   entries (rhyme-driven and metre-preserving substitutions) will want them, but building the
   shared namespace before the second consumer exists is speculative. My call: keep them inside
   `proteus` and move on the second use, with the move noted as expected in the ADR.
3. Strict OOV by default, or a `permissive=True` escape hatch for exploratory use?

## Batch shape

Not a ten-procedure batch — one module, three fixtures, one ADR (the seam). Demo at the end
is the Bauhusius count reproduced under two rulesets and one German line scanning.
