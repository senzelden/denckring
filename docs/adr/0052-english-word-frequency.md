# 52. English word frequency, from the Leipzig news corpus

## Context

English has had no frequency. `graded_words` is SCOWL's size classes, and ADR 0028
says plainly that a band is a speller's judgement of which dictionary size a word
belongs in, not how often anyone writes it. German has had a frequency since ADR
0038, from the Leipzig Corpora Collection, cut into bands to serve as its
`graded_words`. denckring-bench, needing the commonest English words to draw
everyday text from, typed a list in from Kučera and Francis's Brown corpus counts.

## Decision

`denckring-en-data` ships `frequencies.txt.gz`: for each word `graded_words` holds,
the number of times it occurs, in lowercase, in the Leipzig Corpora Collection's
`eng_news_2023_1M`. 49,631 of the 77,078 graded words occur. The pack declares a new
capability, `lexicon.frequency`, and answers it with `word_frequencies()`, a
read-only mapping of word to count. `denckring.words(lang, order="frequency")` sorts
the everyday view (ADR 0051) by it, commonest first.

**The licence is the one ADR 0038 established for Leipzig's downloads**, CC BY 4.0,
with the same reading of the version. It needs no new distribution:
`denckring-en-data` already declares `CC-BY-4.0` for Open English WordNet, so ADR
0013's quarantine has nothing to separate, unlike German, where CC BY could not join
a CC0 package. `LICENSE-LEIPZIG` and the `NOTICE` carry the attribution.

**Counts, not bands.** German's frequency became its `graded_words` because German
had no graded words. English has SCOWL's, and `anagram`, `paragram` and
`word_ladder` read them: replacing them would move those rows' outputs, which 0.3.2
does not do. So the frequency is a capability of its own, and a count rather than a
band, since a caller ranking words wants the order a band throws away.

**The case rule: lowercase only.** A capitalised form opens a sentence or names
something, and news is full of names. Counting `Trump`, `Bush` or `Bill` toward
`trump`, `bush` and `bill` would rank common nouns by a year's headlines. The cost is
the other capital: a word that often opens a sentence (`however`) is undercounted by
that share of its uses.

**Kept to the graded vocabulary.** The corpus's own word list holds 652,287 forms,
most of them names, numbers and typos. Restricting to `graded_words`' keys, SCOWL's
sizes up to 60 that carry no names, abbreviations or misspellings, means the table
ranks the words the pack already calls words and adds none.

The build downloads the 288 MB archive once, verifies its pinned SHA-256, reads the
one words file inside it, and writes a gzip with a zero timestamp, so a rebuild from
the same archive writes the same bytes.

## Consequences

- No checker reads the table, so no verdict, score or default moves. A later
  release could rank `anagram`'s covers by it; that would be a reading change for
  0.4.0, with its own measurements.
- The register is news. `said` is the 19th commonest word and `you` the 30th, where
  speech or fiction would put `you` far higher. Leipzig publishes web and Wikipedia
  corpora too, and none was measured.
- German and French have no `lexicon.frequency`: German's Leipzig table was cut to
  bands at build time, and French takes `max(books, films)` into its own bands.
  Their refusals name no extra, rather than one that would not help.
- The wheel grows by 203 KB.
