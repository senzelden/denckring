# 42. The blend needs no grapheme-to-phoneme model, and German needed a fold

## Context

ADR 0041 shipped `paronomasia` with a bound: it checks a displacement only when
the word that lands is itself in the pronouncing dictionary. The blends that
dominate the punning shopfront — `Haarmonie`, `Hairitage`, `Föhnix`,
`Chaarisma`, `Haarchitektur` — put a *coined* word there, and no pack here can
pronounce a word it has never seen. That ADR named `phonemes.g2p` as the
capability the family was blocked on, in the manner ADR 0015 prescribes: named
on the row, with no pack behind it.

The question then asked was whether to build it. Three routes were costed:
espeak-ng as an out-of-tree GPL-3.0 plugin; a model learned from the 837,689
German Wiktionary entries, 134,000 CMUdict entries and 125,343 Lexique entries
already shipped; or nothing.

**Measurement first, and it changed the question.** A blend is not an arbitrary
string. The host word and the word spliced into it are both ordinary dictionary
entries, so a blend can be verified as a *derived form* — the host recoverable
behind it, the spliced word really present, and that word sounding like a
stretch of the host — without ever pronouncing the coinage. Measured against the
named targets, using nothing that is not already installed:

| coinage | host | spliced | distance |
|---|---|---|---|
| Föhnix | Phönix | Föhn | 0.000 |
| Hairitage | heritage | hair | 0.000 |
| Breadwinner | breadwinner | bread | 0.000 |
| Hairways | airways | hair | 0.333 |
| **Haarmonie** | Harmonie | Haar | **0.667** |
| Chaarisma | Charisma | Haar | 0.667 |

English worked immediately. German did not, and the reason was not g2p at all:
German vocalises a syllable-final /r/, so `Haar` is transcribed `h aː ɐ̯` while
`Harmonie` opens `h a ʁ`. The same underlying segment, spelled two ways, and an
unweighted edit distance charges a full substitution for it — the cost ADR 0041
D3 admitted when it chose unweighted Levenshtein over a feature-weighted metric.

## Decision

**D1. No `phonemes.g2p`, and the name is retired rather than left standing.**
The family it was named for is reachable without it. What remains out of reach
is not g2p-shaped: a host the lexicon does not carry (usually a proper noun —
`Barbarella` is absent from CMUdict) and the cross-lingual blend (`Atmosph'air`),
which needs `phonemes.bilingual` and would need it whatever g2p existed.

Recorded as a decision because the alternative was attractive and expensive.
espeak-ng costs a system binary, a GPL-3.0 quarantine and a distribution of its
own, and its output would still need mapping into each pack's notation — which
for English is ARPABET, so the mismatch is real work, not a wrapper. A learned
model costs no licence, but it is a statistical component in a project whose
whole claim is that its verdicts are decidable: at 90% accuracy one verdict in
ten is wrong for a reason nobody can see, which is a far worse failure than
today's `MissingCapability`, and it would have to be evaluated against the very
dictionaries it was trained on.

**D2. `portmanteau` is its own row.** `paronomasia` displaces a whole word;
a blend splices inside one. Different operations, different violations, and ADR
0007 is one module per procedure. Folding both into one row would have made its
catalogue definition describe two things, which is the drift ADR 0015 exists to
prevent.

**D3. A per-language equivalence table, and it folds one thing.**
`core.phonetics.EQUIVALENT` records symbols that are one segment in a language's
own notation. German gets `{ʁ, ɐ̯, ɐ, r}`. **Vowel length is deliberately not
folded**: `aː` and `a` are contrastive — `Staat` and `Stadt` — so collapsing
them would buy `Haarmonie` a distance of 0.000 by discarding a distinction the
language makes. It sits at 0.333 instead. English and French get no entries:
ARPABET has no vocalised-r symbol and Lexique's SAMPA maps to a single `ʁ`, so a
table for them would be a guess dressed as data.

**D4. The window is searched, not aligned, and that is the row's weakest joint.**
Deciding *which* phonemes of the host the spliced letters cover would need
grapheme-to-phoneme alignment, which this project does not have. The check asks
instead whether the spliced word sounds like *some* window of the host of about
the right length. That would accept a blend whose word matches a stretch
somewhere other than where it was spliced. It is the strongest reading available
without an aligner, and it is stated in the module docstring rather than left for
a reader to discover.

**D5. `apply` is not shipped, though `kind` says `both`.** The figure is plainly
constructive, so misdescribing it as `restrictive` to match the implementation
would be the wrong direction. Generating a blend means choosing where to splice —
Deri and Knight's multitape-FST problem — and is its own piece of work.
`describe_procedure` will still report `both`; the docstring heads that off, as
`larding` and `lipogrammatic_translation` already do.

## Consequences

**Folding was verified additive before it shipped.** All nine German pairs the
existing fixtures and domain phrases turn on — `Kamm`/`Komm`, `Welle`/`Welt`,
`Zopf`/`Kopf`, `Glanz`/`Ganz` and the rest — score identically with and without
it, and a test pins that. So this is not a re-reading of work already checked.

**The prefilter had to learn the same fold, and briefly did not.** `shares_an_edge`
compares first and last phonemes to decide what is worth measuring; unfolded, it
rejected `Haar` against `Harmonie` before the metric ever saw the pair. A
prefilter stricter than the measure behind it hides candidates the band would
have accepted, silently. It now folds too.

**ADR 0041's `phonemes.g2p` note is now wrong and stays wrong on purpose.** The
row's `notes` and module docstring named it as the blocker in good faith and the
measurement overturned it; `paronomasia`'s notes now point here instead. The
older ADR is a record of what was decided when, not a document to keep tidy.

**A coinage that is its own host is not a blend, and the data found that before a
reader would have.** `Crustacean` contains `crust`; `Breadwinner` contains `bread`;
both satisfied an early draft at a spelling distance of 0.000, because nothing had
been spliced. That is the found pun, which `paronomasia` already excludes on the
grounds that it states no relation between two texts. The guard is
`identical_to_host`, and it exists because three trades' worth of authored blends
were run through the checker rather than admired.

**Two things are still unreachable, and neither is g2p's fault.** A proper-noun
host, which is most of the film and celebrity blends; and the cross-lingual
blend, which is a large share of the German salon window in practice — `British
Hairways` over a Berlin shop is English inside German, and `phonemes.bilingual`
is what that needs.

**Coverage moves.** 123 implemented rows become 124 and the catalogue 157
becomes 158; eight constructed cases take the corpus from 572 to 580. No case
claims external provenance, for ADR 0041 D7's reason, which has not changed.
