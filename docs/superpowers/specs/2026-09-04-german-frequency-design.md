# denckring — German frequency, so `anagram` can generate

Date: 2026-09-04
Status: approved, not implemented

## Purpose

Give the German pack `lexicon.graded_words`, so `anagram` can generate in German
as it already does in English and French.

German `anagram` already *checks*: `runs_in` is `[en, de, fr]`, and
`check("anagram", "Esel Lese", lang="de", source="Lese Esel")` is satisfied. Only
generation is missing, and for one reason — the generator ranks its covers by the
commonness of the rarest word in them, and German's lexicon comes from Wikidata
Lexemes, which carries no frequency data at all.

This is the last row in the catalogue whose German gap is a data gap rather than
a permanent ceiling.

## The measurements that chose the design

All measured 2026-09-04. Two sources were tried; the first is recorded because
it fails in a way worth never repeating.

### The source that does not work, and why

`hermitdave/FrequencyWords` (OpenSubtitles 2018, CC BY-SA 4.0) has **zero
capitalised entries in 1,157,685 rows** — it lowercases wholesale. German
capitalises common nouns, so `Tag`/`tag`, `List`/`list` and `Tower`/`tower`
collapse into one string and German nouns become indistinguishable from English
homographs. The contamination lands in the *common* bands, which is exactly what
`anagram` ranks by, and it produced `Wortspiel → list power`.

No filter recovers it. Intersecting with German Wiktionary headwords still yields
`list power`, because `List` and `Power` genuinely *are* German lemmas.
Cross-referencing SCOWL flags `die`, `gut`, `man` and `tag` — all German. The
information is destroyed at source.

### The source that does

The Leipzig Corpora Collection, `deu_news_2023_*`. Its `*-words.txt` is
`id ⇥ word ⇥ frequency`, and **case is preserved**: 100,059 capitalised types
against 33,561 lowercase in the 100K corpus. The same probe words:

| | Leipzig | OpenSubtitles |
|---|---|---|
| `Tag` / `tag` | 598 / absent | merged, ranked common |
| `List` / `list` | 3 / absent | merged, ranked common |
| `Power` / `power` | 19 / 1 | merged, ranked common |
| `Tower` / `tower` | 11 / absent | merged, ranked common |

The register is better too, not merely different. Leipzig's commonest words are
`der die und den mit von das ist auf für sich ein` — written German.
OpenSubtitles gave `ich sie das ist du nicht`, which is spoken register and
which no reader of a word game is ranking against.

### Yield, and the artefact

Both rows below apply the case rule of D3, which matters: a first version of
this table compared a case-aware 1M against a case-blind 100K and made the
corpus look like the variable when the rule was.

| corpus | download | graded words | artefact, gzipped |
|---|---|---|---|
| `deu_news_2023_100K` | 23 MB | 43,956 | 183,243 bytes |
| `deu_news_2023_1M` | 219 MB | **101,296** | 433,822 bytes |

101,296 sits between English's 77,078 and French's 125,343. The 1M corpus is
chosen: 57,000 more words for 190 MB of build-time download that is never
vendored.

## Decisions

### D1. Leipzig, under the licence its own terms give the downloads

The project's terms state two things, and the distinction is load-bearing:

> The data and applications provided by the project … are made available free of
> charge for private and scientific use under the Creative Commons licence
> **CC BY-NC**. Any use beyond the query options provided on the WWW, automated
> queries (except via our web services) and commercial use of the data are
> prohibited …
>
> The text corpora offered for download are made available under the Creative
> Commons licence **CC BY**.

The NC clause and the automated-query prohibition govern the **web service and
dictionary portal**. What this chapter uses is a published corpus tarball —
sentence two — which is **CC BY**: attribution, no non-commercial restriction,
redistributable.

The build downloads one archive once and caches it. It never touches the query
interface, which is what the second half of the first sentence forbids.

### D2. A sixth distribution, `denckring-de-frequency`

CC BY cannot go into `denckring-de-data`, which declares `Apache-2.0 AND
CC0-1.0`: CC0 waives rights where CC BY requires attribution, and adding it would
make that declaration false. ADR 0013's principle is that a data licence is
quarantined in its own distribution, and this is a third German licence.

It could have gone into `denckring-de-wiktionary` (CC BY-SA), and an earlier
draft of this design said it would. That rested on the source being CC BY-SA and
on needing Wiktionary headwords to filter junk. Both premises are gone: the
source is CC BY, and Leipzig's news text is edited prose that needs no junk
filter. Dropping the Wiktionary dependency also nearly doubles the vocabulary:
measured on the chosen 1M corpus with D3's case rule applied to both sides,
**101,296 without that filter against 54,483 with it**.

Consequence: `denckring[de-frequency]` is a **light** extra, 434 KB, that does not
drag in the 6.5 MB Wiktionary package.

### D3. The case rule: a German noun is counted only where it is capitalised

This is the decision the whole chapter turns on, and it must be written into the
build rather than assumed from the source.

Leipzig preserves case, but **both German word lists here throw it away**:
`known_words()` is 0 capitalised of 668,580. Only `nouns()` keeps it — 184,040
entries, all capitalised. So the rule is:

- a form whose lowercase is in `nouns()` is a German noun, and is counted **only
  from Leipzig's capitalised rows**;
- every other form is counted only from lowercase rows.

Lowercase `power`, `list` and `tower` in German news are another language's
tokens and are dropped. Their capitalised German counterparts are kept with the
frequency they actually have.

Without this rule the design silently reverts to the failure it was written to
fix: a first pass lowercased the Leipzig keys before intersecting, and
`Wortspiel → list power` came straight back at 1M scale, where lowercase `list`
appears and at 100K it had not.

### D4. Six bands, `(10, 20, 30, 40, 50, 60)`, larger means less common

Not re-derived. `graded_words`' contract is SCOWL's direction, `anagram`'s
`max_size` is capped at 60, and `denckring-fr-data`'s `build_lexicon.py` already
does exactly this split. Third use of the same five lines.

## Components

### L1. `packages/denckring-de-frequency/`

A sixth workspace member, modelled on `denckring-de-data`, with a
`LICENSE-LEIPZIG` naming the Leipzig Corpora Collection, Universität Leipzig /
Sächsische Akademie der Wissenschaften / InfAI, as CC BY requires.

**The licence *version* is not settled and must be before that file is written.**
The terms say "the Creative Commons licence CC BY" with no version, and the
archive carries no licence file — `meta.txt` names none either. Secondary sources
report 4.0 (and 3.0 for an older CD-ROM), which is not good enough to put in a
`license` expression: an SPDX identifier is a claim, and `CC-BY-4.0` asserts a
version nobody here has read. The first task of the plan is to establish it from
the project's own page or by writing to them, which their terms explicitly
invite. Until then the expression is unwritable, not guessable.

It registers **no entry point**. Core refuses two packs claiming one language and
ADR 0013 forbids merging licences, so `de` still resolves through
`denckring_de_data:pack()`, whose factory returns the richer subclass when the
extra distribution is importable — exactly the arrangement ADR 0030 built for
`denckring-de-wiktionary`, and the reason that ADR's rejected probe approach must
not be reintroduced.

`GermanFrequencyPack` declares `GRADED_WORDS` and returns a `MappingProxyType`
over an `lru_cache`d table, for the reason English states: the cached dict is
shared, and handing it out lets one caller corrupt it for all.

**The two extras compose, and that needs deciding once rather than per-caller.**
A reader may install `de`, `de-frequency`, `de-wiktionary`, or all three. The
factory returns the class carrying the union of what is importable.

### L2. `scripts/build_frequency.py`

Downloads `deu_news_2023_1M.tar.gz` into `~/.cache/denckring-dumps` (where the
Wiktionary chapter already caches), reads one member — `*-words.txt` — and writes
`graded_words.txt.gz`. Implements D3 and D4. Never vendors the archive.

### L3. Library changes

- `errors._PERMANENTLY_MISSING` **loses** `("de", "lexicon.graded_words")`. Its
  own comment anticipates this: "a future data chapter that lifts one is a
  one-line removal, not a guess."
- `_SPECIALIST_EXTRAS` gains `("de", "lexicon.graded_words"): "de-frequency"`.
- `anagram`'s catalogue row adds `de` to `languages`, which currently reads
  `[en, fr]`.
- `pyproject.toml` gains the `de-frequency` extra; `_EXTRAS` is unchanged, since
  it is keyed by language.

### L4. Golden cases and tests

German `anagram` golden cases, led by `Lebensmittel → mitbestellen` — a genuine
single-word anagram. The corpus figures pinned the way
`tests/test_calculator_corpus.py` pins its own, so the table size cannot drift
into prose. A test asserting the case rule directly: lowercase `power` is absent
from the built table while `power` (from `Power`) is present with a plausible
band.

## Testing

Beyond the four-command gate and `eval --all`:

- **The case rule is the thing to test, because it is the thing that was got
  wrong twice.** A fixture of Leipzig-shaped rows containing `Tag`/`tag`,
  `Power`/`power` and `gut`/`Gut`, asserted through the build function rather
  than through a downloaded corpus.
- **`test_round_trip.py`** — `anagram` is already in the harness and already
  passes in English; German generation joins it without a new gate.
- **The explorer's own suite**, since a catalogue row's `languages` changes.
- CI's longer typecheck form gains `packages/denckring-de-frequency/src`.

## Out of scope, and the costs this design accepts

**Proper nouns.** News text is full of them and Wikidata's noun list contains
them, so `Neck`, `Olpe`, `Benz` and `EZB` reach the table and produce
`Denckring → grind neck`. Filtering them needs a part-of-speech signal this
distribution does not have. Named here rather than discovered later.

**`graded_words` keys stay lowercase.** Both shipped packs are 0 capitals in
77,078 and 125,343, and `anagram` matches against the keys, so capitalised keys
would silently exclude every German noun. The consequence is that German output
prints nouns lowercased — `list power` rather than `List Power` — which is
orthographically wrong German. German is the first language for which this
convention loses information. Changing it is its own decision, touching a
capability contract and a procedure, and it is not this chapter's.

**A second frequency signal.** French takes `max(books, films)` to avoid register
bias; this takes news alone. Leipzig publishes web and Wikipedia corpora and
multiple years that could be combined, and none of that was measured.

**Wiktionary sense count**, measured and rejected before Leipzig was found:
Spearman against true frequency is **−0.272 (fr)** and **−0.324 (en)** — right
direction, under 10% of the rank variance. Recorded so it is not proposed again.

## ADR

ADR 0038, recording D1 (the licence reading), D2 (a sixth distribution) and D3
(the case rule). D3 is the one that binds future work: any German data chapter
reading a cased corpus must decide what to do with case *before* intersecting,
because both German word lists in this project have already discarded it.
