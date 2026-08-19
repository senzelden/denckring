"""A row that declares a capability it never reaches misleads exactly as much as one
that omits a capability it needs. Group B was made of both kinds — `word_ladder` and
`tmesis` understated (they needed `lexicon.words` and did not say so); `haikuization`
overstated (it declared `phonemes`, computed a rhyme key, and never let the result
affect a verdict). Understating fails loudly: `BaseProcedure.check` gates every call on
`meta.requires` before `_check` runs, so a row that reaches for a capability it never
declared hits `MissingCapability` the first time anyone runs it against a pack that
lacks that capability. Overstating fails silently — nothing raises, nothing looks
wrong, and the only way to see it is to ask whether the declared capability was ever
actually reached. This module guards the silent half.

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
run, did any of them ever call a method that capability is supposed to unlock? If a row
declares `phonemes` and not one golden case ever calls `pack.phonemes`, `pack.rhyme_key`
or `pack.rhyme_keys`, the declaration looks exactly like `haikuization`'s did.

**Scope, stated plainly.** The spy only watches methods behind capabilities a bare,
data-free pack cannot provide: `letter_shapes`, `lexicon.words`, `lexicon.nouns`,
`phonemes`, `stress`, `syllables`, `syllables.heuristic` and `syllables.dictionary`.
`tokens`, `alphabet` and `fold_diacritics` are deliberately left out: they are present
on every pack this codebase has, including the bare core-only default, and several
rows satisfy them by scanning letters directly (`denckring.core.text.letter_spans`)
rather than by calling `pack.tokenize` or `pack.word_spans` — `homoconsonantism` and
`univocalic` are two working, correct rows that do exactly this. Watching those three
capabilities would flag rows that are not wrong, which is worse than not watching them
at all: a check with known false positives trains the next reader to ignore its output.

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

**What this does not attempt.** A symmetric check — flag a row that calls a capability's
method without declaring the capability — is not implemented, because the evidence is
ambiguous in exactly the way the paragraph above describes: a call to `stress_pattern`
is real evidence for a `stress`-only row and *also* satisfies `syllables`, so treating
"method called" as proof of "this specific capability was exercised" would misattribute
calls between the two everywhere both declarations coexist in this codebase. Building a
reliable version of that direction would need per-row semantic knowledge (which of the
two a given call is "for") that a method-name spy cannot see. Understating a capability
already fails loudly at runtime (`MissingCapability`, direct and immediate) the moment a
row is checked against a pack lacking what it silently needed — that is real coverage,
just not this module's.
"""

from __future__ import annotations

from typing import Any

import pytest

from denckring.core import catalogue
from denckring.core.errors import DenckringError
from denckring.core.protocol import Lang, LanguagePack
from denckring.core.registry import get
from denckring.eval import harness

#: Capability -> the pack methods that realise it. Every key here is a capability
#: absent from the bare, data-free default pack (`EnglishPack`/`GermanPack` with no
#: extra installed) — see the module docstring for why `tokens`, `alphabet` and
#: `fold_diacritics` are deliberately not among them. `stress_pattern`/`stress_patterns`
#: appear under both `stress` and `syllables` for the reason given there.
CAPABILITY_METHODS: dict[str, tuple[str, ...]] = {
    "letter_shapes": ("ascenders", "descenders", "exceeds_x_height"),
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
            f"golden fixtures ever call pack.{'/'.join(methods)}() — the declaration "
            f"looks unreachable, the shape of the haikuization/phonemes defect this "
            f"guard exists to catch"
        )
