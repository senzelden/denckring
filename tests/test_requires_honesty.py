"""A row that declares a capability it never reaches misleads exactly as much as one
that omits a capability it needs. Group B was made of both kinds — `word_ladder` and
`tmesis` understated (they needed `lexicon.words` and did not say so). Understating
fails loudly: `BaseProcedure.check` gates every call on `meta.requires` before `_check`
runs, so a row that reaches for a capability it never declared hits `MissingCapability`
the first time anyone runs it against a pack that lacks that capability. Overstating
fails silently — nothing raises, nothing looks wrong, and the only way to see it is to
ask whether the declared capability was ever actually reached. This module guards the
silent half.

**Why "remove the capability and see if it breaks" does not work.** That gate in
`check` runs *before* `_check`, keyed on `meta.requires` alone — it has no idea whether
`_check`'s body goes on to touch the capability or not. Strip a declared capability from
the test pack and `check` raises `MissingCapability` for every row that declares it,
whether `_check` ever uses it or not. That construction cannot tell a used capability
from an unused one; it only re-tests the gate, which is not what is in question here.

**What this uses instead.** `test_every_declared_capability_is_reached_by_its_fixtures`
wraps the real language pack in a spy that records which of its methods get called, then
runs every one of a row's own golden fixtures through the *public* `check()` — the gate
still runs, unmodified, against the pack's real capabilities, so nothing about normal
behaviour changes. What the spy adds is visibility: after all of a row's fixtures have
run, did any of them ever call a method that capability is supposed to unlock? `limerick`
is the case this guard genuinely caught: it declared `requires: [tokens, phonemes,
stress]`, but `_check` calls `form_report(text, pack, scheme="AABBA")` with no `metre=`
argument, so no golden fixture of its ever touches `pack.stress_pattern` or
`pack.stress_patterns` — `stress` was never reached at all, and the assertion below
fired correctly. `requires` and its `notes` were corrected as part of this task.

**Scope, capability by capability — not one shared sentence.** The spy watches
`letter_shapes`, `lexicon.words`, `lexicon.nouns`, `phonemes`, `stress`, `syllables`,
`syllables.heuristic`, `syllables.dictionary` and `fold_diacritics`. It does not watch
`tokens` or `alphabet`, for two different reasons:

- `tokens`: several correct, working rows satisfy it by scanning letters directly
  (`denckring.core.text.letter_spans`) rather than by calling `pack.tokenize` or
  `pack.word_spans` — `homoconsonantism`, `homovocalism` and `univocalic` all do this.
  Watching it would flag rows that are not wrong.
- `alphabet`: `pack.alphabet()`/`pack.vowels()` are present on every pack this codebase
  ships, including the bare core-only default, so the capability can never actually be
  absent to gate against — a row can call `pack.vowels()` through a shared helper
  without declaring `alphabet` at all and never once observe a consequence
  (`homoconsonantism`/`homovocalism` do exactly this, via `letter_class_report`, which
  calls `pack.vowels()` on their behalf). Watching a capability whose own gate can never
  truly fire tests whether a fixture happened to exercise a code path, not whether the
  declaration does real work.

Note that `letter_shapes` and `fold_diacritics` are *also* present on the bare default
pack — being absent from a data-free install was never the actual dividing line, and an
earlier version of this docstring wrongly implied it was for all four. What makes
`letter_shapes` and `fold_diacritics` worth watching, and `tokens`/`alphabet` not, is
that the former two have no *known, demonstrated* alternate path around their own
methods in this codebase, and watching them found two real, live over-declarations:
`prisoners_constraint` (declared `tokens` and `fold_diacritics`, used neither — it scans
`enumerate(text)` directly and calls only `pack.exceeds_x_height`) and `spoonerism`
(declared `fold_diacritics`, and the string `fold` appears in that module only inside
its own docstring). Both `requires` were corrected as part of this task.

**Why `syllables` and `stress` share evidence.** `sonnet`, `ballade`, `ottava_rima`,
`curtal_sonnet`, `spenserian_stanza` and `englyn` declare `syllables` but never call a
method literally named `syllables` — nothing in this codebase does; `pack.syllables()`
is declared in every pack's `capabilities` but never overridden anywhere, so calling it
always raises regardless of which row asks. These rows instead derive a line's syllable
count from `len(pack.stress_pattern(word))`, established as sound reasoning for exactly
these rows in this batch's own review (`ottava_rima`/`ballade`: "both scan metre, which
reaches the syllable machinery"). So `stress_pattern`/`stress_patterns` count as
evidence for *both* `stress` and `syllables`. That is deliberately generous in one
direction only: it can under-report a missing declaration, never manufacture one.

**What this does not attempt — two distinct gaps.** First: a symmetric check — flag a
row that calls a capability's method without declaring the capability — is not
implemented, because the evidence is ambiguous in exactly the way the paragraph above
describes: a call to `stress_pattern` is real evidence for a `stress`-only row and
*also* satisfies `syllables`, so treating "method called" as proof of "this specific
capability was exercised" would misattribute calls between the two everywhere both
declarations coexist in this codebase. Understating a capability already fails loudly
at runtime (`MissingCapability`, direct and immediate) the moment a row is checked
against a pack lacking what it silently needed — that is real coverage, just not this
module's.

Second, and distinct from `limerick`'s case above: a row that *calls* a capability's
method and then discards the answer is invisible to this guard, because the guard only
observes whether a call happened, not what the caller did with the result. This is not
hypothetical — it is exactly what pre-correction `haikuization` did (`git show
e8b4b69^:src/denckring/procedures/haikuization.py`, lines 63 and 113): it called
`denckring.core.prosody.rhyme_keys`, which calls `pack.rhyme_keys` for every line, then
unpacked only the word (`for _, word, _ in rhyme_keys(...)`) and threw the rhyme-key set
away — the exact defect Task 9's review caught and R18 corrected, before this module
existed. Had this guard existed then, `phonemes` would have shown as "reached" (the
call happened) and the assertion would have passed, missing the defect entirely. Seeing
that requires asking whether a returned value affects the verdict, which is a
per-row semantic question a method-name spy has no way to answer.
"""

from __future__ import annotations

from typing import Any

import pytest

from denckring.core import catalogue
from denckring.core.errors import DenckringError
from denckring.core.protocol import Lang, LanguagePack
from denckring.core.registry import get
from denckring.eval import harness

#: Capability -> the pack methods that realise it. See the module docstring's
#: "Scope, capability by capability" section for why `tokens` and `alphabet` are
#: deliberately not among these keys — it is not simply "absent from the bare pack";
#: `letter_shapes` and `fold_diacritics` are on the bare pack too and are watched
#: anyway. `stress_pattern`/`stress_patterns` appear under both `stress` and
#: `syllables` for the reason given there.
CAPABILITY_METHODS: dict[str, tuple[str, ...]] = {
    "letter_shapes": ("ascenders", "descenders", "exceeds_x_height"),
    "fold_diacritics": ("fold_diacritics",),
    "lexicon.words": ("is_word",),
    "lexicon.nouns": ("nouns", "noun_index"),
    "phonemes": ("phonemes", "rhyme_key", "rhyme_keys"),
    "stress": ("stress_pattern", "stress_patterns"),
    "syllables": ("syllables", "syllable_count", "stress_pattern", "stress_patterns"),
    "syllables.heuristic": ("syllable_count",),
    "syllables.dictionary": ("syllable_count",),
}

_TRACKED_METHODS = frozenset(m for methods in CAPABILITY_METHODS.values() for m in methods)


class _SpyPack:
    """Wraps a real, fully-working pack; records which tracked methods get called.

    Every attribute access falls through to the real pack unchanged — the spy
    changes nothing about what a call returns or raises, only whether it noticed
    the call happen. `capabilities`, `lang`, `word_re` and every untracked method
    pass straight through, so `BaseProcedure.check`'s own capability gate sees the
    pack's real, complete capability set exactly as it would without the spy.
    """

    def __init__(self, inner: LanguagePack) -> None:
        self._inner = inner
        self.called: set[str] = set()

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._inner, name)
        if name in _TRACKED_METHODS and callable(attr):

            def _wrapped(*args: Any, **kwargs: Any) -> Any:
                self.called.add(name)
                return attr(*args, **kwargs)

            return _wrapped
        return attr


def test_declared_languages_have_a_fixture(procedure_id: str) -> None:
    """A `de` (or any) language in `languages` with no golden fixture case is an
    unproven claim — the whole point of Part 1's fixture requirement.

    `procedure_id` is auto-parametrized by conftest across every registered row;
    no `@pytest.mark.parametrize` is added for it here.
    """
    meta = catalogue.get(procedure_id)
    fixture_langs = {case.lang for case in harness.golden_cases() if case.procedure == procedure_id}
    missing = set(meta.languages) - fixture_langs
    assert not missing, (
        f"{procedure_id} declares languages {sorted(missing)} with no golden fixture "
        f"case in that language — a declaration with no fixture is an assertion, not "
        f"a claim"
    )


def test_every_declared_capability_is_reached_by_its_fixtures(
    procedure_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every capability in `CAPABILITY_METHODS` that this row declares must be
    exercised by at least one of its own golden fixtures. See the module docstring
    for the construction, its scope, and what it deliberately does not attempt.
    """
    meta = catalogue.get(procedure_id)
    watched = sorted(set(meta.requires) & set(CAPABILITY_METHODS))
    if not watched:
        pytest.skip(f"{procedure_id} declares no capability this guard can observe")

    procedure = get(procedure_id)
    cases = [case for case in harness.golden_cases() if case.procedure == procedure_id]
    assert cases, f"{procedure_id} is implemented but ships no golden fixture at all"

    from denckring.lang import get_pack as real_get_pack

    spies: list[_SpyPack] = []

    def spying_get_pack(lang: Lang) -> _SpyPack:
        spy = _SpyPack(real_get_pack(lang))
        spies.append(spy)
        return spy

    monkeypatch.setattr("denckring.lang.get_pack", spying_get_pack)
    for case in cases:
        try:
            procedure.check(case.text, lang=case.lang, **case.params)
        except DenckringError:
            continue
    called: set[str] = set()
    for spy in spies:
        called |= spy.called

    for capability in watched:
        methods = CAPABILITY_METHODS[capability]
        assert called & set(methods), (
            f"{procedure_id} declares {capability!r} in requires, but none of its "
            f"golden fixtures ever call pack.{'/'.join(methods)}() — the capability "
            f"looks unreached, the shape of the limerick/stress defect this guard "
            f"exists to catch (though not the discarded-result variant — see the "
            f"module docstring)"
        )
