# ADR 0048: A bounded proverb corpus

## Context

Issue #22's perverb row needed `corpus.proverbs`. Oulipo's public account
(https://www.oulipo.net/fr/contraintes/perverbe, consulted 2026-09-22)
describes combining fragments of sayings, not an arithmetic halfway split.
The broader practice includes poems, whose merit is not mechanically decidable.

## Decision

Implement the two-fragment graft only. `source` names the first saying and the
required `donor` names the second. Both must match different corpus entries after
case-folding and tokenization. The source prefix joins the donor suffix at
editorially selected boundaries. Punctuation and whitespace are not judged.
No new shared source model is needed. Generation is deterministic for a pair.

The optional `ProverbCorpus.proverbs()` protocol returns immutable prefix/suffix pairs under
`corpus.proverbs`. Base packs refuse it. The English data pack supplies a small,
explicit starter corpus; the POS pack inherits it. The stable `LanguagePack` protocol remains unchanged; existing third-party
structural packs need no new method unless they advertise this capability.

The three sayings are transcribed from Thomas Preston, *A Dictionary of English
Proverbs and Proverbial Phrases*, entries 123, 1367 and 1532, public-domain text
at https://www.gutenberg.org/files/39281/39281-h/39281-h.htm (consulted 2026-09-22).
The selected seams are editorial annotations, not claimed source punctuation:
after “feather”, “stone” and “time”, respectively. Corpus content is versioned
with `denckring-en-data`; the capability does not imply exhaustive coverage.

## Consequences

Only six ordered pairings are currently available. Unknown sayings are unresolved,
not disproved; generation refuses them. This is a deliberately small implementation,
not a general proverb detector, corpus search service, or judge of poetry. Caller
supplied arbitrary sayings do not bypass the membership requirement. Enlarging the
corpus requires attested entries and reviewed seams. Repeated or same-source pairs
are refused even with `allow_identity`: two distinct sayings define this contract.

This addresses one remaining row of #22. Antonym/synonym semantics and bilingual
resources remain separate work; this PR must not close that umbrella issue.
