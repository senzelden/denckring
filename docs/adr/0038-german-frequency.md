# 38. German frequency, and a source whose case survives

## Context

German `anagram` could check but not generate. `runs_in` was already
`[en, de, fr]` and `check("anagram", "Esel Lese", lang="de", source="Lese Esel")`
was satisfied; only `apply` refused, because the generator ranks its covers by
the commonness of the rarest word in them and German's lexicon comes from
Wikidata Lexemes, which carries no frequency data at all.

`_PERMANENTLY_MISSING` therefore held `("de", "lexicon.graded_words")`, citing
ADR 0028: SCOWL is vendored into `denckring-en-data` alone. Its own comment
anticipated this record — "a future data chapter that lifts one is a one-line
removal, not a guess."

Two sources were tried. The first is written down because it fails in a way
worth never repeating.

**OpenSubtitles (`hermitdave/FrequencyWords`, CC BY-SA 4.0) has zero capitalised
entries in 1,157,685 rows.** It lowercases wholesale. German capitalises common
nouns, so `Tag`/`tag`, `List`/`list` and `Tower`/`tower` collapse into one string
and German nouns become indistinguishable from English homographs. The
contamination lands in the *common* bands, which is exactly what `anagram` ranks
by, and the first prototype answered `Wortspiel → list power`.

No filter recovers it. Intersecting with German Wiktionary headwords still
yields `list power`, because `List` (a ruse) and `Power` genuinely *are* German
lemmas. Cross-referencing SCOWL flags `die`, `gut`, `man` and `tag`, all German.
The information is destroyed at source.

## Decision

### D1. The Leipzig Corpora Collection, under the licence its own terms give downloads

Leipzig's terms of usage say two things, and the distinction is load-bearing:

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
sentence two — which is CC BY. The build downloads one archive once and caches
it, and never touches the query interface.

The **version** is in neither the prose nor the data. The terms say only "CC BY";
the archive documents no licence at all, its `meta.txt` being eight lines of
build statistics and its only other non-data member a MySQL schema dump, verified
in both the 10K and 1M corpora. It is carried by the link: the page's "CC BY"
points at the 4.0 deed. That is the project's own statement, and it is what
`Apache-2.0 AND CC-BY-4.0` rests on — recorded because secondary sources
disagree, the older printed frequency dictionaries being described as 3.0.

### D2. A sixth distribution, `denckring-de-frequency`

CC BY cannot enter `denckring-de-data`, which declares `Apache-2.0 AND CC0-1.0`:
CC0 waives rights where CC BY requires attribution, so adding it would make that
declaration false. ADR 0013's principle is that a data licence is quarantined in
its own distribution, and this is German's third.

It is deliberately independent of `denckring-de-wiktionary`. An earlier draft put
it there, on two premises that both collapsed: that the source was CC BY-SA, and
that Wiktionary headwords were needed to filter junk out of it. Leipzig's news
text is edited prose and needs no junk filter — measured on the chosen corpus
with the case rule applied to both sides, dropping that filter takes the
vocabulary from 54,483 to 101,296.

### D3. A German noun is counted only where it is capitalised

The decision the chapter turns on, and it had to be written into the build rather
than inherited from the source.

Leipzig preserves case — 100,059 capitalised types against 33,561 lowercase in
the 100K corpus — but **both German word lists in this project have themselves
discarded it**. `known_words()` is 0 capitalised of 668,580. Only `nouns()` keeps
case, all 184,040 of them. So the noun list is the case oracle:

- a form whose lowercase is a known noun counts **only from capitalised rows**;
- every other form counts only from lowercase rows.

| | Leipzig, with the rule | OpenSubtitles |
|---|---|---|
| `Tag` / `tag` | 598 / dropped | merged, ranked common |
| `List` / `list` | 3 / dropped | merged, ranked common |
| `Power` / `power` | 19 / dropped | merged, ranked common |
| `Tower` / `tower` | 11 / dropped | merged, ranked common |

### D4. Six bands, `(10, 20, 30, 40, 50, 60)`, larger meaning less common

Not re-derived. SCOWL's direction, which `graded_words` documents; the ceiling is
60 because `anagram`'s `max_size` is capped there; `denckring-fr-data` already
writes exactly this split. Third distribution, same five lines — re-deriving them
would be a third chance to invert the direction.

## Consequences

**101,296 graded words, 434 KB gzipped**, from 759,696 corpus rows. That sits
between English's 77,078 and French's 125,343, and `tests/test_de_frequency_corpus.py`
pins it so the figure cannot drift into prose.

**The register is news alone**, where French takes `max(books, films)` precisely
to avoid register bias. It is better than the alternative rather than neutral —
Leipzig's commonest words are `der die und den mit von`, written German, against
OpenSubtitles' `ich sie das ist du nicht` — but Leipzig also publishes web and
Wikipedia corpora and several years that could be combined, and none of that was
measured.

**Proper nouns reach the table.** News text is full of them and Wikidata's noun
list contains them, so `Neck`, `Olpe`, `Benz` and `EZB` are graded like any other
word and `Denckring → grind neck` is a reachable answer. Filtering them needs a
part-of-speech signal this distribution does not carry. Named here rather than
discovered later.

**German nouns print uncapitalised.** `graded_words` keys are lowercase by the
capability's de-facto convention — English's 77,078 and French's 125,343 carry 0
capitals between them — and `anagram` matches its covers against those keys, so a
capitalised key would match nothing. German is the first language for which that
convention loses information, a noun's capital being part of its spelling, and
the visible cost is output like `list power` where German writes `List Power`.
Changing it touches a capability contract and a procedure, and is deliberately
not this chapter's decision.

**ADR 0037's D5 lost its reason and kept its decision.** That record floored
`calculator_word`'s `apply_requires` on `lexicon.nouns` *because* German had no
graded words. It now has. The flooring is still right — `apply_requires` should
name what a row genuinely needs, not the best thing currently available — and
0037 is amended in place rather than rewritten, so a reader can see a decision
survive the collapse of its own premise.

**A rejected alternative, measured and recorded so it is not proposed again.**
Ranking by German Wiktionary sense count, which needs no new data or licence, was
validated where ground truth exists: Spearman against true frequency is
**−0.272 in French and −0.324 in English**. The right direction, under 10% of the
rank variance, and not a ranking.

**The rule is easy to lose, and was lost twice.** Once by choosing a source that
had already destroyed case; once, after diagnosing exactly that, by lowercasing
the Leipzig keys before intersecting — at which point `Wortspiel → list power`
came straight back, because lowercase English `list` does occur in German news at
1M scale and had not at 100K. Any future German data chapter reading a cased
corpus must decide what to do with case **before** intersecting, because nothing
downstream in this project preserves it.
