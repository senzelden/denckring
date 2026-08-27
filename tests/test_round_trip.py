"""The seed's central property, testable at last.

Batch 1 was restrictive throughout, so no procedure defined `apply` and
`check(apply(text))` had nothing to run on. The source-relative constructive
procedures are the first that can generate as well as validate.

Coverage gap, named rather than left implicit — and measured rather than asserted.
Every call below is `apply(text, lang=lang, **_apply_args(...))`: no parameter
beyond `source` and, where the procedure takes one, `seed` is ever supplied, so a
generator whose `params_model` requires another field is skipped on every single
call via the `except DenckringError`, not exercised by it.
That is the four rows in `PARAMETER_GATED` below, and
`test_the_named_coverage_gap_is_the_whole_coverage_gap` re-derives the set from
what `apply` actually produces rather than trusting this paragraph. `diastic` and
`mesostic` also take an extra parameter (`seed_phrase`, `spine`) but escape the gap
because their defaults happen to produce a usable selection on generic text.
Extending this harness to supply row-specific extra parameters is out of scope
here — it is its own piece of work with its own review surface. Until then, each of
the four gated rows relies on its own row-level round-trip test (e.g.
`test_word_ladder.py::test_apply_finds_a_ladder_its_own_check_accepts`) as the
substitute for what this property cannot reach.

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
"""

from inspect import signature

from hypothesis import given, settings
from hypothesis import strategies as st

from denckring.core.errors import DenckringError
from denckring.core.protocol import Constructive
from denckring.core.registry import all_procedures

CONSTRUCTIVE = sorted(pid for pid, p in all_procedures().items() if isinstance(p, Constructive))

#: The newline is deliberate: half the constructive rows operate on lines or pages and
#: cannot be reached at all without one. See the module docstring.
TEXT = st.text(alphabet="abcdefghijklmnopqrstuvwxyz \n", min_size=1, max_size=80)

#: Rows this property cannot reach, because `apply` here is only ever called with
#: `seed` and (where the model has it) `source`. Each needs a further parameter with no
#: usable default: `word_ladder` (`target`), `arca_musarithmica` (`pinakes`),
#: `pasigraphy` (`table`/`from_language`/`to_language`), `slenderizing` (`deleted`).
#: Asserted below against what `apply` really produces, so the list cannot rot into
#: prose the way it already did once.
PARAMETER_GATED = frozenset({"arca_musarithmica", "pasigraphy", "slenderizing", "word_ladder"})


def test_there_is_something_to_round_trip() -> None:
    assert CONSTRUCTIVE, "no procedure defines apply(); the round-trip property is vacuous"


def test_the_named_coverage_gap_is_the_whole_coverage_gap() -> None:
    """Every constructive row except `PARAMETER_GATED` must actually produce something
    for at least one drawn example. A row that raises on every example is swallowed by
    `except DenckringError` and contributes nothing to the property above, which is
    silent, invisible, and exactly what happened to nine rows for want of a newline.
    """
    reached: set[str] = set()

    @settings(max_examples=200, deadline=None, derandomize=True)
    @given(TEXT)
    def collect(text: str) -> None:
        # Only rows still unreached are retried, so the cost falls away after the
        # first few examples instead of re-running 26 generators two hundred times.
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
    """`seed` only where the procedure takes one, asked of whichever half declares it.

    `seed` used to be a keyword every generator named in its signature and none
    validated. On the spine it is a field on the procedures that draw, so passing
    it to one that does not is an `InvalidParams` — which this harness would
    swallow in its `except DenckringError`, making the property silently vacuous
    for those rows. Passing it to none of them is the mirror mistake, and the
    louder one: the rows that do draw would run unseeded, and the determinism
    test below would be comparing two different draws.

    Both halves are therefore asked, because the migration is in progress: a
    procedure on the spine declares `seed` as a field, one still hand-rolling
    `apply` declares it in the signature. The signature branch dies with the last
    unmigrated generator.
    """
    procedure = all_procedures()[procedure_id]
    assert isinstance(procedure, Constructive)
    model = getattr(procedure, "apply_params_model", None)
    accepts = (
        "seed" in model().model_fields
        if model is not None
        else "seed" in signature(procedure.apply).parameters
    )
    return {"seed": seed} if accepts else {}


@settings(max_examples=50, deadline=None)
@given(TEXT)
def test_apply_output_satisfies_check(text: str) -> None:
    for procedure_id in CONSTRUCTIVE:
        procedure = all_procedures()[procedure_id]
        assert isinstance(procedure, Constructive)
        lang = procedure.meta.languages[0]
        try:
            produced = procedure.apply(text, lang=lang, **_apply_args(procedure_id, 0))
        except DenckringError:
            # Refusing unusable input is allowed: a corpus of one line is not
            # three excerpts. The property is about what apply produces, not
            # about it always producing something.
            continue
        report = procedure.check(produced, lang=lang, **_check_args(procedure_id, text))
        assert report.satisfied, (
            f"{procedure_id}: apply produced text that its own check rejects: {produced!r}"
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
