"""A row that declares a capability it never reaches misleads exactly as much as one
that omits a capability it needs, and this module guards both halves.

Understating fails loudly: `BaseProcedure.check` gates every call on `meta.requires`
before `_check` runs, so a row that reaches for a capability it never declared hits
`MissingCapability` the first time anyone runs it against a pack that lacks that
capability. Overstating fails silently — nothing raises, nothing looks wrong, and the
only way to see it is to ask whether the declared capability was ever actually reached.
The two tests below take the two halves, and they take them by different constructions
because the two failures leave different evidence.

**Overstating — `test_every_declared_capability_is_reached_by_its_fixtures`.**

*Why "remove the capability and see if it breaks" does not work.* That gate in `check`
runs *before* `_check`, keyed on `meta.requires` alone — it has no idea whether
`_check`'s body goes on to touch the capability or not. Strip a declared capability from
the test pack and `check` raises `MissingCapability` for every row that declares it,
whether `_check` ever uses it or not. That construction cannot tell a used capability
from an unused one; it only re-tests the gate, which is not what is in question here.

*What it uses instead.* It wraps the real language pack in a spy that records which of
its methods get called, then runs every one of a row's own golden fixtures through the
*public* `check()` — the gate still runs, unmodified, against the pack's real
capabilities, so nothing about normal behaviour changes. What the spy adds is
visibility: after all of a row's fixtures have run, did any of them ever call a method
that capability is supposed to unlock? `limerick` is the case this genuinely caught: it
declared `requires: [tokens, phonemes, stress]`, but `_check` calls `form_report(text,
pack, scheme="AABBA")` with no `metre=` argument, so no golden fixture of its ever
touches `pack.stress_pattern` or `pack.stress_patterns` — `stress` was never reached at
all, and the assertion fired correctly. `requires` and its `notes` were corrected as
part of this task.

**Understating — `test_declared_capabilities_are_sufficient`.** This one proceeds by
construction rather than by inference: it wraps the real pack so that every method whose
capability the row did *not* declare raises `MissingCapability`, then runs the row's own
golden fixtures through it. A row that survives has proved its declared set is enough to
run on; a row that does not has proved its `requires` is a promise the code breaks. The
verdict comes from running the row under its own stated contract, not from asking the
suite whether it happens to be green — which matters, because the suite *was* green for
the whole of the defect described three paragraphs below.

**Scope, capability by capability — not one shared sentence.** The spy watches
`letter_shapes`, `lexicon.words`, `lexicon.nouns`, `phonemes`, `stress`, `syllables`,
`syllables.heuristic` and `fold_diacritics`. It does not watch `tokens` or `alphabet`,
for two different reasons:

- `tokens`: several correct, working rows satisfy it by scanning letters directly
  (`denckring.core.text.letter_spans`) rather than by calling `pack.tokenize` or
  `pack.word_spans` — `homoconsonantism`, `homovocalism` and `univocalic` all do this.
  Watching it would flag rows that are not wrong.
- `alphabet`: `pack.alphabet()`/`pack.vowels()` are present on every pack this codebase
  ships, including the bare core-only default, so the spy can never see a row punished
  for omitting the declaration. `test_declared_capabilities_are_sufficient` covers it
  instead — that construction *does* make `alphabet`'s gate fire, and it is what found
  the six rows (`univocalic`, `bivocalic`, `monoconsonantal`, `homoconsonantism`,
  `homovocalism`, `univocalic_translation`) reaching `pack.vowels()` through
  `letter_class_report` without declaring `alphabet`.

Note that `letter_shapes` and `fold_diacritics` are *also* present on the bare default
pack — being absent from a data-free install was never the actual dividing line, and an
earlier version of this docstring wrongly implied it was for all four. What makes
`letter_shapes` and `fold_diacritics` worth watching by the spy is that they have no
*known, demonstrated* alternate path around their own methods in this codebase, and
watching them found two real, live over-declarations: `prisoners_constraint` (declared
`tokens` and `fold_diacritics`, used neither — it scans `enumerate(text)` directly and
calls only `pack.exceeds_x_height`) and `spoonerism` (declared `fold_diacritics`, and
the string `fold` appears in that module only inside its own docstring). Both `requires`
were corrected as part of this task. `spoonerism` gained `alphabet` afterwards, from the
sufficiency test rather than from this spy: `_letter_onset` calls `pack.vowels()`.

**Why `syllables` is watched only for `pack.syllables()`.** An earlier version of the
map below let `stress_pattern`/`stress_patterns` count as evidence for `syllables` too,
on the reasoning that scanning metre "reaches the syllable machinery". That reasoning
was wrong, and the generosity cost this batch its headline defect: `sonnet`, `ballade`,
`ottava_rima`, `curtal_sonnet` and `spenserian_stanza` declared `syllables`, satisfied
this guard on their `stress` calls alone, and every one of them raised
`MissingCapability('stress')` under a pack carrying exactly their declared set. Scanning
metre reaches `stress` (`prosody.word_stress` → `pack.stress_patterns`); it reaches
syllable counting only on the out-of-dictionary fallback, and that is
`syllables.heuristic`. Each capability now maps only to the methods that realise it, and
nothing shares evidence with anything else.

**What neither test attempts.** A row can *call* a capability's method and then discard
the answer. The spy sees only that a call happened, not what the caller did with the
result, and the sufficiency test sees only that nothing raised. This is not
hypothetical — it is exactly what pre-correction `haikuization` did (`git show
e8b4b69^:src/denckring/procedures/haikuization.py`, lines 63 and 113): it called
`denckring.core.prosody.rhyme_keys`, which calls `pack.rhyme_keys` for every line, then
unpacked only the word (`for _, word, _ in rhyme_keys(...)`) and threw the rhyme-key set
away — the exact defect Task 9's review caught and R18 corrected, before this module
existed. Had this guard existed then, `phonemes` would have shown as "reached" (the call
happened) and the assertion would have passed, missing the defect entirely. Seeing that
requires asking whether a returned value affects the verdict, which is a per-row
semantic question neither a method-name spy nor a capability gate has any way to answer.

**A gap `test_declared_capabilities_are_sufficient` itself does not close.** That test
can only refuse a capability path a row's golden fixtures actually walk; a row whose
fixtures happen never to need a capability its own code can still reach passes
regardless of what `_check` declares. That gap was not hypothetical. Ten metre-scanning
rows — `alcaic_stanza`, `blank_verse`, `elegiac_couplet`, `heroic_couplet`,
`iambic_pentameter`, `petrarchan_sonnet`, `rhyme_royal`, `sapphic_stanza`,
`shakespearean_sonnet` and `trochaic_tetrameter` — declared `stress` without
`syllables.heuristic` while reaching it through `prosody.word_stress`'s fallback for a
word its stress dictionary lacks, and every one of them was green here because no
fixture of theirs contained such a word.

All ten now declare `syllables.heuristic`, and each carries a golden case with an
invented word mid-line so the fallback is genuinely walked and the declaration is
proved rather than assumed. The structural gap remains — a capability reachable only
by input no fixture supplies is still invisible to this test — so the lesson stands:
a row surviving this guard has not thereby proved what the guard above claims it
proves. It has proved it for the texts its fixtures contain.
"""

from __future__ import annotations

from typing import Any

import pytest

from denckring.core import catalogue
from denckring.core.errors import DenckringError, MissingCapability
from denckring.core.protocol import Lang, LanguagePack
from denckring.core.registry import get
from denckring.eval import harness
from denckring.lang.base import (
    ALPHABET,
    FOLD_DIACRITICS,
    LETTER_SHAPES,
    NOUNS,
    PHONEMES,
    STRESS,
    SYLLABLES,
    SYLLABLES_HEURISTIC,
    TOKENS,
    WORDS,
)

#: Capability -> the pack methods that realise it, for the spy in
#: `test_every_declared_capability_is_reached_by_its_fixtures`. Each capability maps
#: only to the methods that actually realise it: nothing shares evidence with anything
#: else, which is the correction the `syllables`/`stress` defect forced. See the module
#: docstring for why `tokens` and `alphabet` are deliberately not among these keys — it
#: is not simply "absent from the bare pack"; `letter_shapes` and `fold_diacritics` are
#: on the bare pack too and are watched anyway.
CAPABILITY_METHODS: dict[str, tuple[str, ...]] = {
    "letter_shapes": ("ascenders", "descenders", "exceeds_x_height"),
    "fold_diacritics": ("fold_diacritics",),
    "lexicon.words": ("is_word",),
    "lexicon.nouns": ("nouns", "noun_index"),
    "phonemes": ("phonemes", "rhyme_key", "rhyme_keys"),
    "stress": ("stress_pattern", "stress_patterns"),
    "syllables": ("syllables",),
    "syllables.heuristic": ("syllable_count",),
}

_TRACKED_METHODS = frozenset(m for methods in CAPABILITY_METHODS.values() for m in methods)

#: Pack method -> the capability whose absence must make it raise. This is the whole
#: `LanguagePack` surface that `BasePack` gates, read off `denckring.lang.base` rather
#: than off `CAPABILITY_METHODS`: the spy above watches a deliberately narrow subset,
#: while sufficiency has to model every gate a row could walk into.
METHOD_CAPABILITY: dict[str, str] = {
    "tokenize": TOKENS,
    "word_spans": TOKENS,
    "fold_diacritics": FOLD_DIACRITICS,
    "alphabet": ALPHABET,
    "vowels": ALPHABET,
    "ascenders": LETTER_SHAPES,
    "descenders": LETTER_SHAPES,
    "exceeds_x_height": LETTER_SHAPES,
    "syllable_count": SYLLABLES_HEURISTIC,
    "syllables": SYLLABLES,
    "phonemes": PHONEMES,
    "rhyme_key": PHONEMES,
    "rhyme_keys": PHONEMES,
    "stress_pattern": STRESS,
    "stress_patterns": STRESS,
    "is_word": WORDS,
    "nouns": NOUNS,
    "noun_index": NOUNS,
}


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


#: The one row whose `requires` is deliberately *not* the set its calls need.
#: `multiple_constraint` is a generic combinator: what a call needs depends on which
#: procedures `constraints` names, which is not knowable until call time, so the row
#: declares its own logic only and lets each delegate's own `MissingCapability`
#: propagate naming the delegate. `test_multiple_constraint_does_not_declare_a_delegates_capability`
#: pins that decision; sufficiency cannot be asked of a set that was never meant to be
#: closed. Any other entry here would be a defect being written down instead of fixed.
_NOT_A_CLOSED_SET: dict[str, str] = {
    "multiple_constraint": (
        "requires is deliberately this row's own logic only — a generic combinator "
        "cannot declare the union of delegates named at call time"
    ),
}


class _StrictPack:
    """Wraps a real, fully-working pack, but refuses every undeclared capability.

    Where `_SpyPack` leaves behaviour alone and only watches, this changes it: any
    method whose capability is absent from `declared` raises `MissingCapability`
    instead of answering, exactly as a pack genuinely lacking it would. `capabilities`
    reports `declared`, so `BaseProcedure.check`'s own gate sees the row's stated
    contract and nothing more.

    `syllables.dictionary` implies `syllables.heuristic`: a pack with real counts
    satisfies a row that would have settled for estimates.
    """

    def __init__(self, inner: LanguagePack, declared: frozenset[str], procedure_id: str) -> None:
        self._inner = inner
        self._declared = declared
        self._procedure_id = procedure_id
        self.capabilities = declared

    def _has(self, capability: str) -> bool:
        if capability in self._declared:
            return True
        return capability == SYLLABLES_HEURISTIC and "syllables.dictionary" in self._declared

    def __getattr__(self, name: str) -> Any:
        inner = object.__getattribute__(self, "_inner")
        attr = getattr(inner, name)
        capability = METHOD_CAPABILITY.get(name)
        if capability is None or not callable(attr) or self._has(capability):
            return attr

        def _refuse(*args: Any, **kwargs: Any) -> Any:
            raise MissingCapability(
                object.__getattribute__(self, "_procedure_id"), inner.lang, capability
            )

        return _refuse


def test_declared_capabilities_are_sufficient(
    procedure_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run each row's own golden fixtures against a pack carrying exactly what the row
    declares. Anything it reaches for beyond that raises, which is what a real pack
    without the capability would do.

    This is the half `check`'s gate cannot cover: the gate compares `requires` against
    the pack and stops, so a row whose `_check` calls further than it declared runs fine
    on the full `en` pack and crashes on a minimal one. Every one of the six form rows
    corrected by ruling R28 failed exactly here while the whole suite stayed green.
    """
    if procedure_id in _NOT_A_CLOSED_SET:
        pytest.skip(_NOT_A_CLOSED_SET[procedure_id])
    meta = catalogue.get(procedure_id)
    declared = frozenset(meta.requires)
    procedure = get(procedure_id)
    cases = [case for case in harness.golden_cases() if case.procedure == procedure_id]
    assert cases, f"{procedure_id} is implemented but ships no golden fixture at all"

    from denckring.lang import get_pack as real_get_pack

    def strict_get_pack(lang: Lang) -> _StrictPack:
        return _StrictPack(real_get_pack(lang), declared, procedure_id)

    monkeypatch.setattr("denckring.lang.get_pack", strict_get_pack)
    for case in cases:
        try:
            procedure.check(case.text, lang=case.lang, **case.params)
        except MissingCapability as exc:
            raise AssertionError(
                f"{procedure_id} declares requires {sorted(declared)}, but golden case "
                f"{case.name!r} ({case.lang}) reaches {exc.capability!r} — the row's "
                f"published contract is a promise its own code breaks"
            ) from exc
        except DenckringError:
            continue
