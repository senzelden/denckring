# 23. The German lexicon is Wikidata Lexemes

## Context

German shipped with four capabilities and no lexicon. Five implemented procedures —
`charade`, `semordnilap`, `word_square`, `n_plus_7`, `s_plus_7` — were English-only for
want of `lexicon.words` and `lexicon.nouns`.

The candidates each carry a licence the core would have had to answer for. igerman98 is
GPL-2/3; a Wiktionary dump is CC BY-SA; DeReWo is non-commercial. ADR 0013 already
quarantines data licences per distribution, so any of them was *possible* — but a
permissive one costs nothing to prefer.

## Decision

Wikidata Lexemes, CC0, vendored in `denckring-de-data`.

Coverage measured before the decision, not after: 184,040 noun lemmas surviving the
single-token filter, and 668,580 distinct written representations across all lexical
categories for membership. For comparison, CMUdict carries 135,166 entries.

The 668,580 figure is distinct written representations, not a count of Wikidata form
entities. An earlier pass counted 1,399,865 noun forms alone by entity, before
deduplication — many German forms share one written string, and membership stores
casefolded distinct strings rather than form identifiers. Both numbers are correct
measurements of different things; the gap is not lost coverage.

Membership unions every lexical category, not nouns alone: `charade` and `word_square`
ask "is this a word", and a noun-only oracle rejects `singen` and `rot`.

Umlauts and ß are preserved in storage. Casefolding is applied for membership
comparison, and `casefold()` deliberately folds ß to ss there, merging the Swiss and
German spellings of one word (e.g. Maßen/Massen) into a single membership entry; the
noun list keeps ß as written and is not casefolded. `fold_diacritics` is a separate,
unrelated fold — it is not applied to membership, because collapsing `Bär` into `Bar`
is a decision ADR 0009 makes a parameter of the procedure, not a property of the
lexicon.

## Consequences

The generating SPARQL is committed, so the vendored files are reproducible and a diff
between versions is readable. CMUdict is not, and this is the better precedent.

CC0 means no attribution or share-alike obligation reaches a user of `denckring[de]`.
`LICENSE-WIKIDATA` records the provenance anyway, because the project records
provenance.

The oracle is broad in the way ADR 0015 described for English: it answers "could this be
a German word", and procedures resting on it inherit that.
