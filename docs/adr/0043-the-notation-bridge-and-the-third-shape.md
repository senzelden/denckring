# 43. English and IPA made commensurable, and the shopfront's third shape

## Context

ADR 0042 concluded that the blend needed no grapheme-to-phoneme model, and it
was right about that. It also recorded two things left unreachable, and named
one of them wrongly as a curiosity rather than as the main event: the
cross-lingual blend.

Going to the attested collections (`docs/research/2026-09-10-…`) settled how
large that gap is. **The commonest real French salon name in existence is one
this project could not check.** tif.hair counts ~150 salons called *Imagin'hair*,
and the whole `-hair` family — *Atmosph'air*, *Caract'hair*, *Bulles d'hair*,
*L'Hair du Temps*, *Changement d'Hair* — is English spliced into French.
Roughly half the attested German names are the same shape in the other
direction: *Hairforce One*, *Open Hair*, *Bel Hair*, *Kamm Back*, *Wellkamm*.

The obstacle was not phonology. It was **notation**. CMUdict answers in ARPABET
and the German and French packs answer in IPA, so `hair` is `HH EH R` and
French `air` is `ɛ ʁ`, and an edit distance over those two symbol sets is
meaningless rather than merely inaccurate.

Separately, a third shape of shop name had been excluded by both rows and never
catalogued: *A Cut Above*, where nothing is displaced and nothing spliced, and
the trade alone supplies the second reading.

## Decision

**D1. A 39-entry ARPABET-to-IPA table, and nothing more clever.**
`phonetics.ARPABET_TO_IPA` maps CMUdict's phoneme set to IPA; German and French
pass through unchanged because they are IPA already. A table a reader can check
line by line against the CMUdict inventory, with nothing that can be silently
wrong — the property that ruled out a learned g2p in ADR 0042 rules *in* a
lookup table here.

**D2. Rhotics fold across languages and only across languages.**
`CROSS_LINGUAL` holds one class: `{ɹ, ʁ, r, ɐ̯, ɐ, ɚ}`. English `ɹ`, French and
German `ʁ`, German's vocalised `ɐ̯` are one category realised differently, and a
pun turns on the category. Kept separate from the per-language `EQUIVALENT`,
because folding `ɹ` and `ɐ̯` together *inside* English would assert something
about English that this table is not asserting. Measured: `hair` against French
`air` is 0.333 with the fold and two edits apart without it.

**D3. The splice may come from another pack, named by a parameter.**
`portmanteau.splice_lang` resolves the spliced word in its own language's pack
and compares through `phonetics.across_languages`. No new capability is
declared: what the row needs is `phonemes` on *two* packs, which is the
capability it already requires, asked of a second language. Naming a
`phonemes.bilingual` capability here would claim a pack provides something no
pack provides — the bridge is in core.

**This does not unblock `homophonic_translation`.** That row is still marked
blocked on `phonemes.bilingual` and stays so. The notation half of its problem
is now solved; judging that a whole target text follows the sound of a whole
source across a language barrier is the other half, and much the larger.

**D4. A host may be more than one word.** `Mona Lisa` behind *Monhaarlisa*,
`Hart am Limit` behind *Haart am Limit*. Pronunciation is now assembled
word-by-word and run together, all-or-nothing: one unknown word in a host would
otherwise silently shorten it and move every distance computed from it.

**D5. `portmanteau`'s default band opens to 0.7**, from 0.5. Measured on the
attested corpus, real names sit above the old ceiling — *Haarwaii* at 0.667,
*Coiff'Hair* at 0.667 — because a splice genuinely may cover a stretch loosely.
A blend may also name its own `max_distance`, which one shipped name uses:
*Monhaarlisa* is a blend you **see** rather than hear, `Haar` covering the `a`
of `Mona` and sounding nothing like it, and it asks for 1.0 rather than being
dropped for failing a test of the wrong sense.

**D6. `amphibologia` is a row of its own.** *(Withdrawn 2026-09-10, the day it
was decided. The row was built, evaluated and cut in one session, and the reason
is worth more than the row was: **its checker is a proxy.** Polysemy is not a
phrase reading two ways — `A Cut Above` and `A Room with a View` both carry a
word of the trade with more than one sense, and only one of them is a pun. The
sense counts it leaned on are an editor's decision besides: Open English WordNet
gives `cut` seventy senses and another dictionary would give another number.
A row whose definition says "can be taken two ways" while its checker asks "is
this word polysemous" is the ADR 0015 error in a subtler dress than the two this
session already caught, and the honest response to finding it a third time is to
delete rather than to reword.

Puttenham's `Amphibologia, or the Ambiguous` is real and was verified — he files
it among the vices of style, beside Pleonasmus and Bomphiologia — and the figure
may well deserve a row one day. It does not deserve one whose checker cannot see
it. The paragraph below is left as written, because an ADR records what was
decided when.)* Puttenham, *The Arte of English
Poesie* (1589): speaking "doubtfully, and the sense may be taken two ways". A
phrase carrying a word of the trade, where that word is polysemous, so a second
reading exists for the trade to activate. `requires: [tokens, lexicon.glosses]`,
`checkability: self`, `kind: restrictive`.

Puttenham files it among the **vices** of style, beside Pleonasmus and
Bomphiologia, and it is left there rather than quietly promoted — a shop sign
wants the doubtful reading caught, so the vice is the point.

It is a row and not a mode because it states a relation of a different kind:
`paronomasia` and `portmanteau` relate two texts, and this relates a text to a
trade. Folding it into either would make that row's definition describe two
things, which is the drift ADR 0015 exists to prevent.

**D7. Both new rows generate, and neither invents from nothing.**

`portmanteau.apply` proposes every way of splicing each trade word into the host
— replace any stretch, including none — and hands each candidate to this row's
own `check`. What survives is a blend because the checker said so; the generator
only decides what to ask about. That is the project's thesis used as a search,
and it is what makes the missing grapheme-to-phoneme alignment survivable: not
knowing *where* to splice stops mattering if you can afford to try everywhere.
The search is small — `w * (n+1)(n+2)/2` candidates, at most 859 for English
`paraphernalia`, about 0.2s.

`amphibologia.apply` **selects** rather than invents, which is what that figure
is: it is noticed in something people already say, not built from parts. The
reader supplies the phrases one per line, per ADR 0020, and the row returns those
that read two ways for the trade. The round trip is closed by construction.

**D8. The blend ranking is `(sound, host-recoverability, seam)`, chosen by
measurement and shipped with its failures named.**

Measured against the attested corpus with the shipped hair vocabulary: the real
salon name comes back **first for 10 of 12 hosts** and is in the first ten for 11.
The misses:

- `paraphernalia` gives `phairaphernalia` ahead of `hairaphernalia`, by one place.
- `Chamäleon` gives `ChKammäleon` ahead of `Kammäleon`, at rank 23. It is a *seam
  stutter*: keeping `Ch` **and** adding `Kamm` retains more of the host than
  replacing `Cham` does, so it wins on recoverability while being a word no
  German speaker would write.

**Three fixes were tried and each made the whole result worse**, and they are
recorded so nobody spends the afternoon again:

1. *Filter on seam similarity.* A bound tight enough to remove the stutters
   (0.75) keeps 37 of 38 attested names but loses `Coiff'Hair`, which replaces
   `ure` with `hair` and resembles it not at all.
2. *Rank by absolute length difference.* It began preferring coinages that
   **delete** host letters — `Haaronie`, `hairtage`, `SHaara` — which mangle the
   host worse than the stutters do.
3. *Rank by the length of the replaced stretch.* Fixed `Chamäleon` and broke
   `heritage`, which then preferred `hairtage` over `hairitage`.

Twelve attested names is not enough to tune a ranking against, and each of those
three was a rule that fit the examples in front of it. `test_portmanteau.py`
pins the 10-of-12 floor and pins the `Chamäleon` case as a *known* failure, with
a note saying that if it ever starts passing the test should be deleted rather
than kept as a monument.

**D9. The blend's search window is seeded from a real window, and two shipped
names were resting on the fact that it was not.**

`_closest_window` began at `(1.0, 0, 0)` and returned that untouched when no
window scored below 1.0 — a *zero-length* window, reported as evidence:
`h aː ɐ̯ for  at 1.000`, a comparison against nothing. It read as a loose match
and was no match at all.

Two blends shipped on it, both with `max_distance: 1.0` and a comment calling
them blends you *see* rather than hear. With the bug fixed the measurement is
plain: `Monhaarlisa` is 1.000 from every stretch of `Mona Lisa`, and `Pawsome`
is 1.000 from every stretch of `awesome`. They are not blends this row can see,
so **both are removed from the shipped data**, and the per-blend `max_distance`
that existed only to carry them is removed from the model with them.

This is the sharper form of what ADR 0042 already admitted. There is a real
class of name — `Monhaarlisa`, `Pawsome`, `Yes We Kämm` — whose joke is visual
and cultural, where the letters carry it and the sound does not. No phonetic
rule reaches them, because there is no phonetic fact to reach. What this row
checks is the heard relation, and it should say so rather than open its band
until anything passes.

## Consequences

**Ambiguity is read off a sense count, which is an editor's decision.** Open
English WordNet gives `cut` seventy senses and German Wiktionary gives `Haar`
three; neither number would survive a change of dictionary. What survives is the
ordering, so the row asks for *more than one* rather than scoring them, and
`xylophone` — one sense — is the case that shows the test is not vacuous.

**`amphibologia` ships no `apply` and is `kind: restrictive`.** Generating one
means choosing a phrase from a corpus of things people say, and ADR 0020 gives
the corpus to the reader. There is nothing here for a generator to search that
the reader has not already supplied.

**Fifteen of the sixteen names the maintainer asked for now check**, across all
three rows. The one that does not is *Pony & Clyde*: `Bonnie` is in no
dictionary here, and the only honest routes to it are a caller-supplied
pronunciation or the g2p ADR 0042 declined. It is left failing and said so.

**Coverage.** 124 implemented rows become 125 and the catalogue 158 becomes 159;
six constructed cases take the corpus from 583 to 589, and the externally
sourced share falls to 11.2% — arithmetic, for ADR 0041 D7's reason, which the
research trip did not change: the attested corpus is entirely post-1929.

**The two limits that remain are unchanged in kind.** A proper-noun host, which
is most celebrity blends; and the found pun's cousin where the phrase is not one
anybody says, which no test here can see.
