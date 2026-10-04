# Reading a report

`check()` always returns a `Report`. Here it is on a lipogram forbidding `z`, first
on conforming text, then on text that breaks the rule twice:

```python
from denckring import check

check("lipogram", "A small conforming bit of writing", forbidden="z")
check("lipogram", "A zebra grazed", forbidden="z")
```

```json
{
  "procedure": "lipogram",
  "satisfied": true,
  "score": 1.0,
  "violations": [],
  "metrics": {
    "letters": 28.0,
    "hits": 0.0
  }
}
```

```json
{
  "procedure": "lipogram",
  "satisfied": false,
  "score": 0.8333333333333334,
  "violations": [
    {
      "rule": "forbidden_letter",
      "offset": 2,
      "found": "z",
      "expected": "any letter but 'z'",
      "note": null
    },
    {
      "rule": "forbidden_letter",
      "offset": 11,
      "found": "z",
      "expected": "any letter but 'z'",
      "note": null
    }
  ],
  "metrics": {
    "letters": 12.0,
    "hits": 2.0
  }
}
```

`satisfied` is never a judgment call — it is always exactly `score == 1.0`. There is
no threshold, no "close enough". If you only need a yes/no answer, read `satisfied`
and ignore the rest.

`score` is how far the text is from conforming, not a confidence value. Here it is
`good / total` over the twelve letters the pack could see against `z`: two hits out
of twelve chances is `10/12 ≈ 0.833`. What `good` and `total` count differs by
procedure — letters for a lipogram, lines for a metrical form, words for a lexical
one — so compare scores within a procedure, not across procedures.

Each entry in `violations` is where and how the text failed: `rule` names which check
tripped, `offset` is the character position in the original text (or `null` when a
violation is not localisable, such as a form-wide count), `found` is what was there,
and `expected` is what the rule required. `note` carries anything else worth saying
and is usually `null`.

`metrics` is free-form and procedure-specific, but one key recurs across the
syllable-counting forms — sonnets, ballades, iambic pentameter and the rest —
`metrics["estimated_words"]`. A pronouncing dictionary does not know every word, and
a procedure that needs a syllable count for a word it cannot look up falls back to a
spelling-based heuristic rather than refusing to check the line at all. Doing so
silently would let a caller believe every count was exact. `estimated_words` is how
the library discloses, instead, how many words in the checked text were guessed
rather than looked up — so a caller who needs certainty can decide whether that
number is small enough to trust.

To decide whether to trust a verdict at all, read `Report.estimated` rather than this
metric: it is true whenever the verdict rests on anything estimated or left unjudged,
including what `estimated_words` misses on some rows (rhyme endings, for one), and it
is under the README's stability promise, which `metrics` keys are not. So is
`evidence` itself, since 0.4.0: a caller can decide per entry from its `basis`
(`dictionary`, `ambiguous` or `estimated`) without reading a metric (ADR 0059).

A word the dictionary lists more than one way is looked up, not guessed, so it does not
make a verdict estimated. Its `evidence` entry has basis `ambiguous` and names every
reading (`every`: `2 or 3 syllables`), because the checker accepted any of them. A haiku
line passes when some reading of its words gives the count, as a metrical line scans
when some reading of its stresses fits (ADR 0054, ADR 0014).

## How a checker reads text

`describe(procedure_id, lang=...).reading` says how the text is cut up before it is
judged, so a caller can write a prompt or a guard that agrees with the checker:

- `tokenization` is the word pattern, and `word_examples` shows what it does with the
  cases a count turns on. An apostrophe between letters stays inside a word (`don't`,
  `l’âme`), but a word's length counts its letters only, so `snowball` reads `I'm` as
  two (ADR 0058); a hyphen splits a word in two (`well-known` is two words, in a
  sentence's word count as anywhere); a digit is no part of a word.
- `units` lists the characters that end a line, a clause and a sentence.
- `vowels` lists the letters the vowel rows (`univocalic`, `bivocalic`,
  `monoconsonantal`, `homovocalism`) read as vowels. `y` is one in French and not in
  English or German.
- `normalization` says how letters fold before they are compared, and `determinacy`
  whether the verdict can rest on an estimate or on words left unjudged. A row read
  `exact` never reports `estimated`, with no exceptions: `multiple_constraint` reads
  `heuristic`, since its entries may name a row that estimates.

`reading` is published but not yet under the stability promise.
