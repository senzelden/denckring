# Homophonic translation

## Contract

ADR 0049 records the user-selected acceptance boundary. Dictionary relation checks
require every source token to have an appropriate replacement, in order. Supplied
bilingual checks certify only their explicit data and matching rule, not semantic
or pronunciation accuracy. This row supplies a checker, not a generator.

## Evidence

The golden fixture contains independently specified positive and negative examples.
`tests/test_strict_relations.py` tests dictionary-backed order, multiplicity,
unknowns, empty sources, immutable data and metadata checksums.
`tests/test_supplied_bilingual.py` tests supplied-data completeness, exact gloss
segmentation, sound-distance boundaries, malformed schemas and normalization.

## Limits

See ADR 0049 and the catalogue definition before interpreting success. Unknown
required entries cannot pass; a caller must not read a partial score as success.
