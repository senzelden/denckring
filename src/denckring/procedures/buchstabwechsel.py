"""Buchstabwechsel — Harsdörffer's letter-exchange: an anagram with an exempt `h`.

`anagram` already exists in this catalogue — multiset equality under
`fold_diacritics`, `attested: codified` — and this row is not a second copy of it.
Harsdörffer states rules for the Wechselschluß (die IV. Aufgabe, XIV. Theil,
*Erquickstunden*, 1651, pp. 513-515) that differ from plain multiset equality, in
two specific ways (Rule II, p. 514):

> "Müssen alle und jede Buchstaben deß Namens in dem Wechselschluß mit eingebracht
> werden / und wo möglich unverändert / das u und i die Stimmer nicht für v und j
> setzend. Doch hat das h. weil es vielmehr ein Hauchlaut / als ein vollstimmiger
> Buchstab, die Befreyung / daß es mag eingerucket oder übergangen werden."

- **`h` is exempt.** It "mag eingerucket oder übergangen werden" — may be inserted
  *or* passed over — because it is "vielmehr ein Hauchlaut, als ein vollstimmiger
  Buchstab" (more a breath-sound than a full letter). `anagram` would reject a
  Wechselschluß that adds or drops one. This row drops every `h` from both sides
  before comparing, which is the only reading of "insert or omit" that is
  symmetric: an `h` added by the candidate, dropped by the candidate, or moved
  within it are all indifferent to the count on either side.
- **`u`/`i` must not be set as `v`/`j`.** Against the period's own orthographic
  habit of treating each pair as one letter, Harsdörffer holds the vowel and the
  consonant apart. This needs no extra code: `pack.fold_diacritics` (case-folding
  plus combining-mark stripping, per `denckring.lang.base.BasePack`) never merges
  `u` with `v` or `i` with `j` — there is no NFKD decomposition or German
  orthographic convention that relates them — so the letter comparison below
  already holds them distinct. `test_buchstabwechsel.py` pins this with the
  historical collision itself: `Iohann` against `Johann` must fail, the Latin
  practice of writing `I` for consonantal `J` being exactly what Rule II refuses.
  A future change to `fold_diacritics` that started folding those pairs would be
  a regression this row's own test catches, not a documentation claim resting on
  today's implementation being left alone.

Everything else in the comparison is `anagram`'s own: `letter_counts` and
`multiset_violations`, imported rather than reimplemented, exactly as `antigram`
already imports them to add its own single further constraint. This row adds one
of its own — drop `h` first — the same shape of change `antigram` makes.

**Rule I** (ending) and **Rule III** (sense, completed by an emblem) are recorded
in the catalogue row's `notes`, not enforced: neither is decidable from the text
alone. Rule III in particular is the same shape of claim `antigram`'s own
definition already declines to check — "whether the sense is genuinely opposite
is a judgement no program makes" — and this row borrows that candour rather than
pretending a partial check is a full one.

**Unknown output words are disclosed, never failed.** Harsdörffer's own aim is
"daß endlich andere Wörter heraus kommen" — that other words come out — and
nothing in Rule II requires those words to be attested anywhere; a personal name
rearranges into proper names and archaic spellings as often as into dictionary
entries. So `check` never requires an output token to be a known word. Instead,
when the pack declares `lexicon.words` — not a member of this row's `requires`,
because `check` must keep working without it — `metrics["known_words"]` counts
how many of the candidate text's tokens the lexicon resolves, the same
disclose-rather-than-fail contract `definitional_expansion` uses for
`metrics["estimated_words"]`. Only `de` is declared in `languages`, but
`BaseProcedure.check` defaults an unspecified `lang` to `"en"`, and the
generic property tests in `test_invariants.py` and `test_strategies.py` call
`check` that way — so the guard is not academic even though every real caller of
this row supplies `lang="de"`.

**`apply` is deferred (ADR 0002).** Generating a Wechselschluß is a search over
partitions of a letter multiset — with `h` free to place anywhere or nowhere —
into words the lexicon knows, which is `anagram.apply`'s search with one added
degree of freedom. Building that search is not this task's job; `check` is what
registration requires, and the catalogue's `kind: both` records what the form
permits, the way `definitional_expansion`'s does, not what this row ships.
"""

from __future__ import annotations

from collections import Counter

from denckring.core.base import BaseProcedure, DiacriticParams, SourceParams
from denckring.core.protocol import LanguagePack, Report
from denckring.core.registry import register
from denckring.lang.base import WORDS
from denckring.procedures.anagram import letter_counts, multiset_violations


class BuchstabwechselParams(SourceParams, DiacriticParams):
    pass


def drop_h(counts: Counter[str]) -> Counter[str]:
    """`counts` with every `h` removed — Rule II's exemption, applied symmetrically.

    Harsdörffer permits `h` to be inserted or omitted; dropping it from both
    sides before comparison means neither side's `h` count constrains the
    other, whatever that count is on either side.
    """
    without_h = counts.copy()
    del without_h["h"]
    return without_h


@register
class Buchstabwechsel(BaseProcedure[BuchstabwechselParams]):
    """Every letter of a name, rearranged, with `h` exempt and `u`/`i` held apart
    from `v`/`j`. See the module docstring for why this is not `anagram`."""

    id = "buchstabwechsel"

    @classmethod
    def params_model(cls) -> type[BuchstabwechselParams]:
        return BuchstabwechselParams

    def _check(self, text: str, pack: LanguagePack, params: BuchstabwechselParams) -> Report:
        fold = params.fold_diacritics
        candidate = drop_h(letter_counts(text, pack, fold=fold))
        source = drop_h(letter_counts(params.source, pack, fold=fold))
        violations, shared, total = multiset_violations(candidate, source)
        metrics = {"letters": float(sum(candidate.values())), "shared": float(shared)}
        if WORDS in pack.capabilities:
            tokens = pack.tokenize(text)
            metrics["known_words"] = float(sum(1 for token in tokens if pack.is_word(token)))
        return self._report(
            good=shared,
            total=total,
            violations=violations,
            metrics=metrics,
        )
