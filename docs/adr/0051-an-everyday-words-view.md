# 51. An everyday-words view, and an editorial override of SCOWL's band 10

## Context

A caller drawing everyday vocabulary, such as a benchmark minting a lipogram's text
from common words, read `graded_words()` and did four things to it itself: kept
band 10, kept words of lowercase ASCII letters, sorted them, and removed by hand the
entries that are no words a reader would accept. denckring-bench listed `cs`, `re`,
`hes`, `cums`, `payed` and `numbest`, all of which SCOWL grades in band 10, its
commonest. ADR 0028 explains why: SCOWL's bands are a speller's size classes, and a
speller admits a fragment or a variant spelling that an everyday reader would not.

N+7 had the matching problem from the other side. Its default dictionary is the
pack's noun list, which a model asked to perform N+7 is never shown, so the answer
depends on material outside the prompt. The bench rebuilt the list to print it.

## Decision

`denckring.words(lang, *, max_band=None, letters_only=True)` returns a pack's graded
words up to `max_band`, sorted by band and then alphabetically, kept to words of
letters alone unless `letters_only` is false, and without the entries in the pack's
`word_exclusions()`. `BasePack.words` is the same view. `word_exclusions` is an
optional pack member read with `getattr`, as `syllable_evidence` is: a pack written to the protocol
alone gets the view with nothing excluded, and the `LanguagePack` protocol does not
change.

`denckring-en-data` ships `everyday_exclusions.txt`: `cs`, `cums`, `hes`, `leaved`,
`numbest`, `payed` and `re`, each with its reason on its line. This is an editorial
override of SCOWL, made knowingly, of the kind ADR 0028 declined to make silently
for the letter `i`. It is bounded in three ways:

- It touches the view only. `graded_words()` keeps every entry, and `is_word` and
  every checker read what they read before, so no verdict, score or default moves.
- Each entry was measured in band 10 and is held there by a test, so an entry SCOWL
  stops grading, or regrades, fails the suite rather than lingering.
- It removes; it never adds. Adding words, such as the pronoun `I`, would be a
  judgement about English the sourced list exists to avoid.

`denckring.nouns(lang, *, max_band=None)` returns N+7's dictionary in the order N+7
walks it. With `max_band`, it keeps the nouns `words(lang, max_band=...,
letters_only=False)` also lists, so a caller can build a source whose every noun a
prompt can print. N+7's `dictionary` parameter names both functions, and the
catalogue's `hidden_material` (audit C4) flags the row.

`pi` is not excluded, although the bench listed it: it is a word, the Greek letter
and the constant.

## Consequences

- The view is a new public function. Its ordering and its exclusions may change in
  a minor release, and the changelog will say so.
- The pronoun `i` is still absent, as ADR 0028 records. Restoring it is an open item
  for a pack-level addition list, which this ADR does not create.
- German and French have no exclusion list. Their views are their graded tables cut
  to the band, and a list for either would follow this one's rules.
