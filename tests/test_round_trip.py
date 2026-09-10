"""The seed's central property, testable at last.

Batch 1 was restrictive throughout, so no procedure defined `apply` and
`check(apply(text))` had nothing to run on. The source-relative constructive
procedures are the first that can generate as well as validate.

Coverage gap, named rather than left implicit — and measured rather than asserted.
Every call below is `apply(text, lang=lang, **_apply_args(...))`: no parameter
beyond `source` and, where the procedure takes one, `seed` is ever supplied, so a
generator whose `params_model` requires another field is skipped on every single
call via the `except DenckringError`, not exercised by it.
That is the six rows in `PARAMETER_GATED` below, and
`test_the_named_coverage_gap_is_the_whole_coverage_gap` re-derives the set from
what `apply` actually produces rather than trusting this paragraph. `diastic` and
`mesostic` also take an extra parameter (`seed_phrase`, `spine`) but escape the gap
because their defaults happen to produce a usable selection on generic text.
Extending this harness to supply row-specific extra parameters is out of scope
here — it is its own piece of work with its own review surface. Until then, each of
the gated rows relies on its own row-level round-trip test (e.g.
`test_word_ladder.py::test_apply_finds_a_ladder_its_own_check_accepts`, and
`test_calculator_word.py::test_what_the_generator_makes_satisfies_its_own_checker`,
which does it in all three languages) as the substitute for what this property
cannot reach. `portmanteau` joined the set when it grew a generator: it needs a trade, which
is a parameter this harness does not supply, and it carries its own round-trip
test for the same reason the others do.

The seed is drawn, not pinned. Every property here used to pass `0`, so the ten
rows that draw were exercised at one draw per input and the rest of the seed space
never at all. That was the larger of the two blind spots the chapter-2 spec
recorded, and on a different axis from the missing `derandomize=True` beside it:
that one is about which inputs Hypothesis tries, this one about which draw each
generator makes from them, so closing either left the other standing. Both are
closed here. `test_apply_is_deterministic_under_a_fixed_seed` still pins its seed,
and must: its subject is that two identical calls agree.

`TEXT` carries `\n` in its alphabet, and that is load-bearing rather than
incidental. Without it this property was vacuous for every line- or page-oriented
generator: `fold_in`, `text_folding`, `mathews_algorithm` and `ideenwuerfeln`
raised on every example Hypothesis could draw, so eight rows were unreached where
an earlier version of this paragraph named nine — the other four being the
parameter-gated set the first paragraph above does name. That earlier count was
wrong twice over rather than merely off by one: `column_reading`, `haikuization`
and `spoonerism` were in fact reached (`spoonerism` on inputs like `'wu u pzyh'`,
via its letter-onset fallback), while `pasigraphy` and `slenderizing` — both
already parameter-gated — went unnamed.
`"|"` and `"."` are in the alphabet for the same reason and were found the same
way — by the guard, once it had teeth. `cent_mille_milliards` and `wechselsatz`
read their input as a sheet of alternatives separated by `"|"`, and `recombination`
splits on sentence terminators. With none of those three characters drawable, every
sheet offered exactly one option per position and every text was one sentence, so
all three returned their input on every example Hypothesis could draw. While the
guard was inert that read as three rows passing the round-trip property; with the
guard live it reads as three rows raising on every example, which is the same
vacuum said out loud.

An alphabet is not a shape, though, and three rows needed a shape. `TEXT` is now a
flat draw from that alphabet composed with two constructed shapes: `PARAGRAPHS`,
blank-line separated, for `fold_in` and `mathews_algorithm`, and `PROSE`,
terminated sentences, for `recombination`. All three were previously reached by
luck alone, and the `max_examples=1000` the coverage-gap test carried was the price
of that luck — a price that did not in fact buy the guarantee it looked like
buying: replayed over twelve fixed seeds, the flat-only strategy reached every row
on three of them. Building the shapes bought both a lower budget and a real floor.

`test_apply_output_satisfies_check` and `test_apply_does_not_return_its_input` see
only `texts[0]` of what a generator found, because that is all `apply` ever
returns. `test_every_produced_text_satisfies_check` and
`test_every_produced_text_differs_from_the_input` below call `produce` instead and
range over its whole `texts` list, so a bad candidate sitting behind a good first
one is no longer invisible. As of this writing two rows make that distinction
live: `paragram` and `anagram` are the constructive procedures whose `produce`
returns more than one candidate on the shapes `TEXT` draws, so they are the rows
the four properties above and below can actually disagree about. An earlier
version of this paragraph named `paragram` alone. The count was measured over
`produce` when `TEXT` gained its built shapes rather than read off the source, and
`anagram` turns out to have been live all along — the flat draw reaches it too.
"""

from pathlib import Path

import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

# Private API, and knowingly so: `OneOfStrategy` and its `element_strategies` both live
# under `hypothesis.strategies._internal`, so an upgrade may move them and break this
# import. There is no public way to ask a strategy how many branches it has, and the
# alternative — reasoning it out from the `st.one_of` call — is what produced two false
# comments in this file already. If the import breaks, replace the mechanism rather than
# dropping the check: `test_the_flat_draw_keeps_half_the_branches` explains what it buys.
from hypothesis.strategies._internal.strategies import OneOfStrategy

import denckring.eval as _eval
from denckring.core.base import ConstructiveProcedure
from denckring.core.errors import DegenerateOutput, DenckringError
from denckring.core.protocol import Constructive
from denckring.core.registry import all_procedures

CONSTRUCTIVE = sorted(pid for pid, p in all_procedures().items() if isinstance(p, Constructive))

FIXTURES = Path(_eval.__file__).parent / "fixtures"

#: The newline is deliberate: half the constructive rows operate on lines or pages and
#: cannot be reached at all without one. The bar and the full stop are deliberate for
#: exactly the same reason, discovered the same way. See the module docstring.
FLAT = st.text(alphabet="abcdefghijklmnopqrstuvwxyz \n|.", min_size=1, max_size=80)

#: Text shaped like prose paragraphs, reached by construction rather than by luck.
#: `fold_in` and `mathews_algorithm` need two blank-line-separated paragraphs, which
#: `FLAT` offers about once in three hundred examples — so the suite was carrying
#: `max_examples=1000` to buy a shape it could have built.
PARAGRAPHS = st.lists(
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz |.", min_size=1, max_size=30),
    min_size=2,
    max_size=4,
).map("\n\n".join)

#: Paragraphs of *terminated* sentences — the same idea, for the row that turned out to
#: be the expensive one. `recombination` needs two sentences whose terminator is followed
#: by whitespace, and neither shape above builds one: both draw `.` uniformly from an
#: alphabet, so a full stop lands beside a space only by accident. It was `recombination`,
#: not `fold_in`, that the old `max_examples=1000` was really paying for, and it was not
#: paying enough: replayed over twelve fixed seeds, the old flat-only strategy reached
#: every row 3 times out of 12 at a thousand examples. That budget was never a floor, it
#: was one lucky `derandomize` seed. No `.` inside a clause, so every terminator here is
#: a real boundary rather than a coin flip.
PROSE = st.lists(
    st.lists(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz |", min_size=1, max_size=20),
        min_size=1,
        max_size=3,
    ).map(lambda clauses: ". ".join(clauses) + "."),
    min_size=2,
    max_size=4,
).map("\n\n".join)

#: A second, distinct handle on `FLAT`, and the wrapper is the whole point of it.
#: `st.one_of` dedupes its branches by identity, so naming `FLAT` twice buys nothing at
#: all — and writing the `st.text(...)` call out a second time buys nothing either,
#: because `st.text` is `@cacheable` and an identical call returns the very same object.
#: `.map` builds a new strategy, which is what the deduping is unable to collapse.
FLAT_AGAIN = FLAT.map(lambda text: text)

#: Composed with `FLAT` rather than replacing it: the alphabet's `\n`, `|` and `.` are
#: each load-bearing for other rows and the module docstring records how each was found.
#: `FLAT` gets two of the four branches and the two built shapes one each, because the
#: built shapes serve three rows between them and `FLAT` serves the other twenty reachable
#: ones, `spoonerism` most marginally of all. Widening in one direction can narrow in
#: another, so the balance is measured rather than assumed: the comment above `@settings`
#: carries the numbers, and `test_the_flat_draw_keeps_half_the_branches` holds the
#: composition to the four branches they were measured at. How much of the *draw* each
#: branch then gets is a separate question with a surprising answer — see that test.
TEXT = st.one_of(FLAT, FLAT_AGAIN, PARAGRAPHS, PROSE)

#: Ten of the 27 constructive rows draw at random. Every property below used to
#: pass `_apply_args(procedure_id, 0)` — the same seed on every example, in every
#: property, on every run — so those ten were exercised at exactly one draw per
#: input text and never the rest of the seed space. A generator producing text
#: its own `check` rejects on seed 1 but not on seed 0 passed here in silence.
#: Bounded rather than unbounded because a seed is fed to `random.Random` and a
#: bignum buys no additional coverage, only slower shrinking.
SEED = st.integers(min_value=0, max_value=2**16 - 1)

#: Rows this property cannot reach, because `apply` here is only ever called with
#: `seed` and (where the model has it) `source`. Four need a further parameter with no
#: usable default: `word_ladder` (`target`), `arca_musarithmica` (`pinakes`),
#: `pasigraphy` (`table`/`from_language`/`to_language`), `slenderizing` (`deleted`).
#:
#: `calculator_word` is here for a different reason, and the distinction matters to
#: whoever extends this harness. Its parameters all have usable defaults; what it
#: cannot take is the *text*. Its `apply` argument is a digit string — the material
#: the generator decodes — so every text `TEXT` can draw raises `InvalidParams`
#: before any parameter is consulted. Supplying `digits` would not reach it; only a
#: per-row text strategy would.
#: Asserted below against what `apply` really produces, so the list cannot rot into
#: prose the way it already did once.
PARAMETER_GATED = frozenset(
    {
        "arca_musarithmica",
        "calculator_word",
        "pasigraphy",
        "portmanteau",
        "slenderizing",
        "word_ladder",
    }
)


def _ignores_input(procedure_id: str) -> bool:
    """Read from the class attribute rather than listed by hand.

    The membership is pinned in `test_non_degeneracy.py`; repeating three ids
    here would be a second copy of it, free to rot when a fourth device lands.
    """
    procedure = all_procedures()[procedure_id]
    return isinstance(procedure, ConstructiveProcedure) and procedure.ignores_input


#: The devices whose `_produce` never reads `text` — the rings, the board, the wheel.
#: The two properties below compare output against the input, and for these three that
#: comparison carries no information at all: the argument was never read, so output
#: equalling it says nothing about whether the procedure ran. `_is_degenerate` skips the
#: same comparison for the same reason, and asserting the opposite of the spine is a
#: contradiction the suite kept only by luck — `llull_figure` and `poesie_automat` emit
#: text that lies entirely inside the alphabet `TEXT` draws from, so nothing but the
#: draw stood between this and a failure, and widening that alphabet is exactly what an
#: earlier chapter did once already.
IGNORES_INPUT = frozenset(pid for pid in CONSTRUCTIVE if _ignores_input(pid))


def test_there_is_something_to_round_trip() -> None:
    assert CONSTRUCTIVE, "no procedure defines apply(); the round-trip property is vacuous"


def test_the_flat_draw_keeps_half_the_branches() -> None:
    """`TEXT` claims four branches, so the count is asserted rather than read off the call.

    `st.one_of` dedupes its branches by identity, so `one_of(FLAT, FLAT, PARAGRAPHS,
    PROSE)` silently collapses to three and `FLAT` loses the extra weight the second
    mention was there to give it. That is how this shipped once. It is also why the claim
    here is about branch count and nothing else: **branch count is not draw share.**
    `st.one_of` does not sample its branches uniformly, so the share cannot be divided out
    of the count, and two successive attempts to reason it out from the call — a half, then
    a third — were both wrong. Measured instead, by tagging each branch and counting 33,000
    draws over eleven seeds per composition, the collapse costs about half the flat draw:
    11% flat at three branches against 20% at four. `PROSE` takes the largest share either
    way — 49% at three branches, 45% at four, though an independent 51,000-draw replay put
    that last figure at 44%, which is about as much precision as a sample of this size
    supports. All of these are a snapshot of this exact branch list and will not survive a
    change to it — measure again rather than reasoning again, and say how many draws.

    `spoonerism` is the row that pays for a starved flat draw, and the budget below was
    measured at four branches.
    """
    assert isinstance(TEXT, OneOfStrategy)
    assert len(TEXT.element_strategies) == 4, (
        "TEXT lost a branch to st.one_of's identity dedupe, so the flat draw is weighted "
        "differently from the composition the floor below was measured at"
    )


def test_the_named_coverage_gap_is_the_whole_coverage_gap() -> None:
    """Every constructive row except `PARAMETER_GATED` must actually produce something
    for at least one drawn example. A row that raises on every example is swallowed by
    `except DenckringError` and contributes nothing to the property above, which is
    silent, invisible, and exactly what happened to nine rows for want of a newline.
    """
    reached: set[str] = set()

    # Six hundred, down from a thousand, because `TEXT` now builds the shapes the
    # rare rows need instead of waiting for the draw to offer them — see the
    # comments on `PARAGRAPHS` and `PROSE`. The number is a measurement, not a
    # guess. Replayed under explicit seeds rather than the single one `derandomize`
    # pins, this composition reached every reachable row on 60 of 60 seeds at 300
    # examples, 29 of 30 at 250, and 27 of 30 at 100. The row that goes missing
    # first is `spoonerism` — it wants flat text and is the one this composition
    # starves; at 75 examples, over the same thirty seeds, `diastic` and
    # `wechselsatz` start going too. Six hundred is twice that clean floor, which is
    # the headroom a net five other pieces of work land on should carry. It is also
    # a stronger guarantee than the thousand it replaces rather than merely a
    # cheaper one: replayed the same way, the old flat-only strategy reached every
    # row on three seeds out of twelve, so that budget was never a floor — it was
    # one lucky `derandomize` seed.
    @settings(max_examples=600, deadline=None, derandomize=True)
    @given(TEXT)
    def collect(text: str) -> None:
        # Only rows still unreached are retried, so the cost falls away after the
        # first few examples instead of re-running every generator six hundred times.
        for procedure_id in CONSTRUCTIVE:
            if procedure_id in reached:
                continue
            procedure = all_procedures()[procedure_id]
            assert isinstance(procedure, Constructive)
            lang = procedure.meta.languages[0]
            try:
                procedure.apply(text, lang=lang, **_apply_args(procedure_id, 0))
            except DenckringError:
                continue
            reached.add(procedure_id)

    collect()
    unreached = sorted(set(CONSTRUCTIVE) - reached)
    assert unreached == sorted(PARAMETER_GATED), (
        f"the docstring's coverage gap and the measured one disagree.\n"
        f"  documented: {sorted(PARAMETER_GATED)}\n"
        f"  measured:   {unreached}"
    )


def _check_args(procedure_id: str, text: str) -> dict[str, str]:
    """Source-relative procedures need the text they were made from; others do not.

    `denckring` is constructive and self-checkable at once — it spins its own
    rings — so the suite cannot assume every generator takes a source.
    """
    fields = all_procedures()[procedure_id].params_model().model_fields
    return {"source": text} if "source" in fields else {}


def _apply_args(procedure_id: str, seed: int) -> dict[str, int]:
    """`seed` only where the procedure takes one.

    `seed` used to be a keyword every generator named in its signature and none
    validated. On the spine it is a field on the procedures that draw, so passing
    it to one that does not is an `InvalidParams` — which this harness would
    swallow in its `except DenckringError`, making the property silently vacuous
    for those rows. Passing it to none of them is the mirror mistake, and the
    louder one: the rows that do draw would run unseeded, and the determinism
    test below would be comparing two different draws.
    """
    procedure = all_procedures()[procedure_id]
    assert isinstance(procedure, ConstructiveProcedure)
    accepts = "seed" in procedure.apply_params_model().model_fields
    return {"seed": seed} if accepts else {}


@settings(max_examples=50, deadline=None, derandomize=True)
@given(TEXT, SEED)
def test_apply_output_satisfies_check(text: str, seed: int) -> None:
    for procedure_id in CONSTRUCTIVE:
        procedure = all_procedures()[procedure_id]
        assert isinstance(procedure, Constructive)
        lang = procedure.meta.languages[0]
        try:
            produced = procedure.apply(text, lang=lang, **_apply_args(procedure_id, seed))
        except DenckringError:
            # Refusing unusable input is allowed: a corpus of one line is not
            # three excerpts. The property is about what apply produces, not
            # about it always producing something.
            continue
        report = procedure.check(produced, lang=lang, **_check_args(procedure_id, text))
        assert report.satisfied, (
            f"{procedure_id}: apply produced text that its own check rejects: {produced!r}"
        )


@settings(max_examples=50, deadline=None, derandomize=True)
@given(TEXT, SEED)
def test_every_produced_text_satisfies_check(text: str, seed: int) -> None:
    """Strictly stronger than the property above, which sees only `texts[0]`.

    A multi-result generator hides its bad candidates behind the first one, and
    the first one is the only one `apply` ever returned. This is the property
    that keeps a search honest once there is a search.
    """
    for procedure_id in CONSTRUCTIVE:
        procedure = all_procedures()[procedure_id]
        assert isinstance(procedure, Constructive)
        lang = procedure.meta.languages[0]
        try:
            produced = procedure.produce(text, lang=lang, **_apply_args(procedure_id, seed))
        except DenckringError:
            continue
        for candidate in produced.texts:
            report = procedure.check(candidate, lang=lang, **_check_args(procedure_id, text))
            assert report.satisfied, (
                f"{procedure_id}: produced text its own check rejects: {candidate!r}"
            )


@settings(max_examples=50, deadline=None, derandomize=True)
@given(TEXT, SEED)
def test_every_produced_text_differs_from_the_input(text: str, seed: int) -> None:
    """The non-degeneracy companion, over all candidates rather than the first.

    `IGNORES_INPUT` is skipped, not exempted as a special case: see the comment
    on that set, and `ConstructiveProcedure.ignores_input`.
    """
    for procedure_id in CONSTRUCTIVE:
        if procedure_id in IGNORES_INPUT:
            continue
        procedure = all_procedures()[procedure_id]
        assert isinstance(procedure, Constructive)
        lang = procedure.meta.languages[0]
        try:
            produced = procedure.produce(text, lang=lang, **_apply_args(procedure_id, seed))
        except DenckringError:
            continue
        for candidate in produced.texts:
            assert candidate.strip() != text.strip(), (
                f"{procedure_id}: produced its input past the guard: {candidate!r}"
            )


@settings(max_examples=50, deadline=None, derandomize=True)
@given(TEXT, SEED)
def test_apply_does_not_return_its_input(text: str, seed: int) -> None:
    """The companion the round-trip property never had.

    `check(apply(text))` is satisfied by the identity, so on its own it accepts a
    generator that does nothing. Here `DegenerateOutput` is *not* swallowed: the
    spine raising it is the guard working, and any other refusal is allowed for
    the same reason it is above.

    `IGNORES_INPUT` is skipped, not exempted as a special case: see the comment
    on that set, and `ConstructiveProcedure.ignores_input`.
    """
    for procedure_id in CONSTRUCTIVE:
        if procedure_id in IGNORES_INPUT:
            continue
        procedure = all_procedures()[procedure_id]
        assert isinstance(procedure, Constructive)
        lang = procedure.meta.languages[0]
        try:
            produced = procedure.apply(text, lang=lang, **_apply_args(procedure_id, seed))
        except DegenerateOutput:
            continue
        except DenckringError:
            continue
        assert produced.strip() != text.strip(), (
            f"{procedure_id}: apply returned its input past the guard: {produced!r}"
        )


@settings(max_examples=25, deadline=None)
@given(TEXT)
def test_apply_is_deterministic_under_a_fixed_seed(text: str) -> None:
    """Two identical calls agree.

    For the procedures that do not draw, this asserts only that two identical
    calls agree — which is what determinism means for them, and is now checked
    rather than assumed via a seed they ignored.
    """
    for procedure_id in CONSTRUCTIVE:
        procedure = all_procedures()[procedure_id]
        assert isinstance(procedure, Constructive)
        lang = procedure.meta.languages[0]
        try:
            first = procedure.apply(text, lang=lang, **_apply_args(procedure_id, 7))
        except DenckringError:
            continue
        assert first == procedure.apply(text, lang=lang, **_apply_args(procedure_id, 7))


def test_every_gated_folding_row_has_a_non_default_language_case() -> None:
    """A `PARAMETER_GATED` row is invisible to the property above, so its golden
    file is the only net it has — and a golden file pinning one language is not a
    net at all for a row whose defect is language-shaped.

    `slenderizing` was gated *and* fixtured `lang: en` at file level with two
    ASCII cases, so the row excluded from the safety net was the row that broke,
    and the gate stayed green. Narrowed to rows declaring `fold_diacritics`,
    because that is what makes a row language-shaped: `pasigraphy` is gated too
    and requires only `tokens`, its whole mechanism being a caller-supplied
    table, so a German case there would assert nothing.
    """
    for pid in sorted(PARAMETER_GATED):
        if "fold_diacritics" not in all_procedures()[pid].meta.requires:
            continue
        path = FIXTURES / "golden" / f"{pid}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        default = data.get("lang", "en")
        languages = {case.get("lang", default) for case in data["cases"]}
        assert languages != {default}, (
            f"{pid} is parameter-gated out of the round-trip property and its golden "
            f"file only exercises {default!r}; the property cannot see it and neither "
            f"can the fixtures"
        )
