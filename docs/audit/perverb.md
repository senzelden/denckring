# Perverb

## Contract

ADR 0048 implements a two-fragment corpus graft. Source and donor are distinct
attested sayings; their boundaries are editorial. Case, punctuation and whitespace
are ignored; word order is checked. This does not judge poems inspired by a graft.

## Probes

`tests/test_perverb.py` exhausts every ordered distinct pair of the shipped corpus,
checks the expected prefix and suffix independently, and round-trips each output.
It also probes unknown and identical pairs, empty candidates, wrong donors,
normalization, missing parameters and the base pack's capability refusal.
Golden fixtures distinguish a valid graft, a wrong suffix and unresolved source.

## Limitations

The starter corpus contains three sayings (six pairings); its provenance and seams
are recorded in ADR 0048. Unknown sayings cannot be assessed. No heuristic infers
proverb status, grammatical quality or a good join from arbitrary prose.
