# 30. German pronunciations come from Wiktionary, in a fourth distribution

## Context

`denckring status` reports coverage against the implementable subset, and that figure
is this project's headline claim. It was a claim about English. Chapter 4's spec
measured it: `en` 119 of 119, `de` 78, `fr` 70. Tranche A shipped a spelling heuristic
and took German to 89. The remaining 30 rows want `phonemes` (21), `stress` (17) and
`lexicon.glosses` (2), overlapping — every metre, rhyme and verse form in the
catalogue.

`stress` unblocks nothing on its own: it never appears in a `requires` without
syllables, and German Wiktionary marks it inside the transcription rather than
separately. So this is one piece of work and not three.

**Wikidata Lexemes cannot carry it**, which was measured before this was designed
because ADR 0023 already settled that source and its CC0 licence for the German
lexicon. Queried on 2026-08-30: 6,904 German forms carry IPA (P898), across 3,342
distinct written representations, against the 668,580 the pack already knows. **0.5%**,
and 2.5% of CMUdict's 135,166 entries. The cheap answer was tried first and it failed.

**German Wiktionary can.** Measured against the real
`dewiktionary-latest-pages-articles` dump on 2026-08-31 rather than against a sample:
945,429 German headwords carry a transcription or a definition; after filtering to
usable single-word German IPA, **837,689 pronunciations and 179,831 glosses**. Over
340,958 tokens of four public-domain German works — Wieland's *Oberon*, Goethe's
*Faust I*, Kafka's *Die Verwandlung*, Mann's *Buddenbrooks*:

| measure | coverage |
|---|---|
| tokens with a transcription | **94.0%** |
| tokens with a gloss | 72.5% |

The spec's earlier figure was 90.8% over 639 tokens of this project's own fixtures, and
said the dump measurement — not that one — belonged here. The dump is better, not
worse, and the residue is characterisable rather than random: pre-1901 orthography
(`daß` 1,798 occurrences, `muß`, `wußte`, `bißchen`, `läßt`, `dieß`, `sey`) and proper
names (`Buddenbrook`, `Permaneder`, `Hüon`). A pronouncing dictionary legitimately
lacks both. Per work the spread is 90.6% (Wieland) to 97.6% (Kafka), so the figure
degrades with archaism exactly where a reader would expect it to.

**The constraint that shaped everything.** `denckring/lang/__init__.py` refuses two
packs claiming one language:

```python
if lang in packs:
    raise DuplicatePack(lang, _SOURCES.get(lang, "an installed pack"), source)
```

So the obvious shape — a fourth distribution registering its own `de` entry point —
cannot work; installing it beside `denckring-de-data` raises at import, before any
procedure runs. That collides with ADR 0013, which quarantines a data licence per
distribution precisely so "a future copyleft lexicon has an established place to go".
Wiktionary is CC BY-SA 4.0 where the existing German data is CC0. Two rules of the
architecture, both right, pointing opposite ways.

## Decision

**D1. A fourth distribution, `denckring-de-wiktionary`, holding the CC BY-SA data.**
Under `pip install denckring[de-wiktionary]`. `LICENSE-WIKTIONARY` beside it, and
`scripts/build_pronunciations.py` regenerating the vendored files from the dump, the
committed-and-diffable convention `build_lexicon.py` established.

**D2. It registers no entry point. `denckring-de-data` gains a `pack()` factory, and
that one function is the whole seam.**

```python
def pack() -> GermanPack:
    try:
        from denckring_de_wiktionary import GermanWiktionaryPack
    except ImportError:
        return GermanDataPack()
    return GermanWiktionaryPack()
```

The `de` entry point resolves to this rather than to a class. `entry.load()()` is what
the registry calls, so a function and a class are interchangeable there and nothing in
core learns that German is special. One entry point, so `DuplicatePack` stays
meaningful; two distributions, so the licences stay quarantined.

`GermanWiktionaryPack` subclasses `GermanDataPack`, because an install with both has
both sets of data: `is_word`, `nouns` and `noun_index` keep answering from Wikidata
while the phonetic methods answer from Wiktionary.

**This amends the spec's D3, which is the more interesting half of this record.** The
spec proposed that `GermanDataPack` probe for the phonetic distribution and compute its
own `capabilities`, and it accepted, as a stated cost, that "a reader of
`GermanDataPack` can no longer see what it can do without knowing what else is
installed". That was drafted, built and working before the factory replaced it. The
factory removes the cost rather than paying it: every pack's `capabilities` stays a
fixed `ClassVar[frozenset]`, as on every other pack in the project. Which class you get
still depends on the install — that is unavoidable — but it is now readable in one
function with a docstring instead of smeared across a computed set.

**D3. Syllables and stress are read off the transcription; no second source.** German
Wiktionary's IPA marks primary stress `ˈ` and secondary `ˌ`, so `stress_pattern` is
derived from the string exactly as English derives one from CMUdict's digits. Secondary
stress reports as `?`, free, for the reason English reports its `2` that way. It
follows that `stress` is not a capability that can be present while `phonemes` is
absent, and a test asserts the equality rather than leaving it as prose.

A syllable nucleus is a vowel symbol *not* carrying the non-syllabic mark, or any
consonant carrying the syllabic mark. Both halves earn their place: without the first,
every German diphthong counts as two syllables (`haʊ̯s`); without the second, `ˈliːbn̩`
counts as one.

**D4. Lookup tries the token as written, then case-flipped.** German capitalises nouns
*and* sentence openers, and Wiktionary titles are case-sensitive, so a line-initial
`Und` has no entry while `und` does. Measured worth **4.7 points** of token coverage
over the same 340,958 tokens.

**D5. `syllables` is not claimed, and was being falsely claimed for English.** That
capability is `syllables(word)`, the written syllables of a word. A transcription does
not carry a division of the *spelling* — German Wiktionary marks a syllable break 115
times in 838,000 entries — so German does not declare it.

Deciding that surfaced the same claim already live for English:
`denckring-en-data` declared `SYLLABLES` and never implemented it, so
`get_pack("en").syllables("table")` raised `MissingCapability` naming a capability the
pack declared — the one contradiction that error exists to rule out. No row requires
it, so nothing was broken; but `runs_in` (ADR 0029) computes from `capabilities`, so
the first row to require it would have been reported as running in `en` and would then
have raised. The claim is removed rather than made true, because a pronouncing
dictionary is not a hyphenation dictionary.

**D6. Which phonemes are vowels is the pack's question.** `assonance_constraint` and
`spoonerism` both tested it as "carries a stress digit". That is CMUdict's convention
and true of no other source. Both rows declare `phonemes` and nothing else, so the
moment German had `phonemes` they ran in German, were reported as running, and found no
vowels in any German word at all — `assonance_constraint` failing every German text and
`spoonerism` treating every word as pure onset. `LanguagePack.is_vowel_phoneme` moves
the question to where the answer lives; the two rows ask instead of reading a digit.

This is the defect class that motivates the whole chapter, caught in the act: a
capability is a promise about a question, and a row that answers it with one language's
data conventions is making a promise it cannot keep in the second language.

## Consequences

**German runs every row: 89 → 119 of 119.** `denckring eval --all` goes from 365 to 401
passing cases, the 36 new ones German. Two of the thirty rows unblock on
`lexicon.glosses`, which came free: the same dump carries definitions, so the last two
rows cost a second table in a distribution that already existed rather than a third
licence decision.

**The lockstep is now four ways.** ADR 0013 admitted version-locking as a cost of
quarantining data per distribution; there are now four distributions pinned to one
version, and a release moves all of them.

**A German install has two shapes, and only one of them is exercised by the suite.**
`denckring[de]` and `denckring[de-wiktionary]` are both real installs a user can have.
The suite runs with both, so a new `german-without-pronunciations` CI job covers the
other: it asserts the factory returns `GermanDataPack` and that a phonetic row refuses
by naming the capability rather than guessing.

**13.7MB of vendored data**, roughly twice `denckring-en-data`'s 7.1MB. It is excluded
from the root sdist as the other packages are, so the sdist bound is untouched.

**The syllable count is the phonetic one, and that is sometimes not the count a metrist
wants.** `Familie` is `faˈmiːli̯ə`, three syllables, where the orthographic reading and
much of German verse take four. Tranche A's heuristic gives three for a different and
wrong reason. The dictionary's answer is the one that was measured, and a poem wanting
the other reading is asking a question this data cannot answer. Not softened, and
pinned by a test rather than left to be rediscovered.

**Attribution is now a live obligation.** CC0 asked nothing of this project; CC BY-SA
asks for attribution and share-alike, and `LICENSE-WIKTIONARY` carries both. Anyone
redistributing the derived tables inherits them.

**Verified against real verse, which is the claim worth making.** Goethe's opening
hexameter from *Hermann und Dorothea*, Voß's from the *Odüssee*, and Heine's trochaic
tetrameter all scan under the checkers unmodified, and `Herzen`/`Schmerzen` rhyme while
`Herzen`/`Katzen` do not. Twenty-two constructed German pentameters in eleven rhyme
families back the fixed forms, every one verified by the checker it is a fixture for.

## Alternatives considered

**Merge the data into `denckring-de-data`.** One distribution, no factory, no fourth
lockstep — and CC BY-SA applied to a distribution whose other data never carried it.
ADR 0013 exists to refuse exactly this.

**A `de` entry point on the new distribution.** Raises `DuplicatePack` at import when
both are installed, which is the normal case. Weakening `DuplicatePack` to prefer one
pack would mean core silently choosing between two claims to a language, which is the
thing that error was written to refuse.

**Compute `capabilities` from a probe** — the spec's D3, built and then replaced. See
D2.

**A hand-built stress lexicon.** `docs/expansion_ideas/handover-proteus.md` proposes
exactly this for a first pass: a few hundred hand-marked German words plus a stem-stress
heuristic (`ge- be- ver- ent- er- zer-` unstressed, compounds stressed on the first
element). It would have been defensible when German ran 89 rows and is indefensible
beside 94% real coverage from a source that also carries phonemes and glosses.
