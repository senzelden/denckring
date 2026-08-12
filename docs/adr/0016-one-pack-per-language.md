# 16. One data pack per language, and a collision is an error

## Context

Entry-point discovery is keyed by language name. Adding a lexicon to a second
distribution would have meant two packages registering `en`, and the loader took
whichever loaded first and skipped the rest — silently, so the answers would have
depended on installation order.

## Decision

Two packs claiming one language raise `DuplicatePack`, naming both. The WordNet noun
list therefore goes into the existing `denckring-en-data` rather than a second
distribution, with each dataset carrying its own licence file: CMUdict under
BSD-2-Clause, WordNet under Princeton's licence, code under MIT.

## Consequences

The silent failure is gone, which matters more than the packaging convenience it cost:
a mistake now announces itself at import rather than changing results invisibly.

The limitation is real and worth naming. A language can have exactly one data pack, so
a third party cannot add morphology to English without replacing the pronunciation and
lexicon data too. Composition — several packages contributing capabilities to one
language — is the fix, and it is future work rather than something to improvise while
adding a noun list.

ADR 0013's reasoning still holds for languages: French data will be its own
distribution. What has changed is that *within* a language, data accumulates in one
package.
