# ADR 0049: Strict relations and supplied bilingual data

## Context and accepted decisions

The user selected strict data-backed synonym/antonym checking: every source token
needs a supported relation; unknowns fail. For bilingual procedures, the user chose
explicit supplied data with structural checks and documented limits. Together with
ADR 0048's perverb, these decisions implement the six remaining rows in #22.
No `checkability: none` entry is reclassified.

## Dictionary relations

Use OEWN 2024, the English pack's existing CC BY 4.0 source. The reproducible
`packages/denckring-en-data/scripts/build_relations.py` uses wn 1.1.1. Synonyms
are distinct single-word lemmas sharing a synset; antonyms are direct sense-level
antonym edges. Source and target are case-folded alphabetic lemmas; identity,
multiword entries, inferred/transitive relations and morphology are excluded.
The builder emits sorted JSON in deterministic gzip streams, with row counts,
source rules and SHA-256 hashes in the existing metadata file.

The measured filtered tables contain 44,948 synonym source lemmas and 6,039
antonym source lemmas. These are not the earlier note's unfiltered sense/lemma
counts. Reproduction requires downloading `oewn:2024` once through wn; runtime
uses only packaged data and makes no network requests.

`LexicalRelations` is optional; the stable `LanguagePack` protocol is unchanged.
The English data and POS packs supply the new capabilities, base packs refuse.
The two antonym procedures share the same positional relation checker. Every
source occurrence must be replaced, in order, with one supported token; extra
and missing words fail. Function words are not exempt. Empty sources fail.
Synonymic substitution checks one iteration; callers can validate consecutive
iterations. It does not judge when text becomes unrecognisable.

This is exact dictionary membership, not contextual semantic truth: any recorded
sense can support a pair, and no word-sense disambiguation is inferred. Most
ordinary sentences will fail coverage, deliberately. A partial score never means
success. The three rows supply checkers, not generators.

## Supplied bilingual schemas

Both checkers accept `data` as a JSON string, like the existing pasigraphy table.
It must declare `version: supplied-bilingual-v1`, distinct `source_language` and
`target_language` values from en/de/fr, and a nonblank caller provenance label.
`lang` must equal the source label. Unknown fields/versions, duplicate JSON keys,
case/NFC-colliding word keys, malformed values and empty entries are errors.
Labels and provenance are declarations, not independently verified facts.

`definitional_translation` adds `glosses`, a mapping from source tokens to lists
of target-language gloss strings. Each source occurrence expands to one complete
gloss, in order; target tokens must be fully covered with no extras. A dynamic
set of reachable boundaries avoids greedy rejection when alternatives share a
prefix. No source token may be unknown. Empty sources fail. Case, NFC, punctuation
and whitespace are normalized with the appropriate source/target tokenizers.
Each text is limited to 4096 word tokens. Supplied definitions are not checked
for dictionary authenticity or target-language correctness.

`homophonic_translation` adds an explicit shared `alphabet` and separate
`source_pronunciations` and `target_pronunciations` word-to-symbol-list maps.
Every word must resolve; no unknown word is silently dropped. Nonempty streams
are concatenated, ignoring word boundaries, and compared by Levenshtein edit
count divided by the longer stream length. The required `max_distance` is finite
and in [0,1], with an inclusive boundary. Each stream is limited to 4096 symbols.
Symbols are opaque shared units: no IPA validity, pronunciation correctness,
stress removal, equivalent-sound folding or perceptual calibration is inferred.
Caller-supplied data is flagged in report metrics. Reports do not embed the data;
callers must retain their JSON to reproduce a result.

The bilingual capability lives in the supplied input, not a language pack.
Consequently these rows require `tokens`, not fictional pack-level bilingual
lexicon/phoneme capabilities. This differs from ADR 0043's dictionary notation
bridge: we are explicitly checking declared streams, not inferring a sound
judgment from ordinary prose. Both rows initially provide checking only. Searching
for a fluent target text is not implemented or implied by registration.

## Consequences and validation

All six rows now have mechanical checks under explicit, bounded interpretations.
They do not solve unrestricted semantic substitution or literary translation.
Catalogue definitions and prompts state these limits where callers encounter them.
Golden fixtures and independent examples cover all five new checkers. Tests cover
unknowns, identity, occurrence order, extra/missing output, ambiguous gloss prefixes,
invalid schemas, normalization, threshold boundaries and capability refusal.
The existing capability-use audit now observes synonym and antonym lookups.

## Supplied-data examples

These are constructed mappings, not claims of dictionary authority. Python and
MCP callers pass the serialized JSON string as `data`; the CLI accepts the same
string via `--param data=...`. `source` is the original text, and `lang` is its
language. The schema itself carries the target language.

```python
import json
from denckring import check

mapping = {
    "version": "supplied-bilingual-v1",
    "source_language": "en",
    "target_language": "fr",
    "provenance": "caller example, unverified",
    "glosses": {"cat": ["petit animal"]},
}
check("definitional_translation", "petit animal", source="cat",
      data=json.dumps(mapping))

sounds = {
    "version": "supplied-bilingual-v1",
    "source_language": "en",
    "target_language": "fr",
    "provenance": "synthetic shared symbols, not real pronunciations",
    "alphabet": ["a", "b"],
    "source_pronunciations": {"cat": ["a", "b"]},
    "target_pronunciations": {"chat": ["a", "b"]},
}
check("homophonic_translation", "chat", source="cat",
      data=json.dumps(sounds), max_distance=0)
```

A successful synthetic-symbol example demonstrates structural agreement only.
Callers seeking a sound judgment must supply and retain credible pronunciation
sources and choose a threshold appropriate to their declared symbol units.
