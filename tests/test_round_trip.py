"""The seed's central property, testable at last.

Batch 1 was restrictive throughout, so no procedure defined `apply` and
`check(apply(text))` had nothing to run on. The source-relative constructive
procedures are the first that can generate as well as validate.

Coverage gap, named rather than left implicit: every call below is
`apply(text, lang=lang, seed=0)` — no other parameter is ever supplied. A
generator whose `params_model` requires a field beyond `source` (or beyond a
field with a usable default) is therefore skipped by this property on every
single call, via the `except DenckringError` below, not exercised by it. As
of this writing that is four rows: `word_ladder` (`target`), `arca_musarithmica`
(`pinakes`), `pasigraphy` (`table`/`from_language`/`to_language`), and
`slenderizing` (`deleted`). `diastic` and `mesostic` also take an extra
parameter (`seed_phrase`, `spine`) but escape the gap because their defaults
happen to produce a usable selection on generic alphabetic text. Extending
this harness to supply row-specific extra parameters is out of scope here —
it is its own piece of work with its own review surface. Until then, each of
the four skipped rows relies on its own row-level round-trip test (e.g.
`test_word_ladder.py::test_apply_finds_a_ladder_its_own_check_accepts`) as the
substitute for what this property cannot reach.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from denckring.core.errors import DenckringError
from denckring.core.protocol import Constructive
from denckring.core.registry import all_procedures

CONSTRUCTIVE = sorted(pid for pid, p in all_procedures().items() if isinstance(p, Constructive))

TEXT = st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=1, max_size=80)


def test_there_is_something_to_round_trip() -> None:
    assert CONSTRUCTIVE, "no procedure defines apply(); the round-trip property is vacuous"


def _check_args(procedure_id: str, text: str) -> dict[str, str]:
    """Source-relative procedures need the text they were made from; others do not.

    `denckring` is constructive and self-checkable at once — it spins its own
    rings — so the suite cannot assume every generator takes a source.
    """
    fields = all_procedures()[procedure_id].params_model().model_fields
    return {"source": text} if "source" in fields else {}


@settings(max_examples=50, deadline=None)
@given(TEXT)
def test_apply_output_satisfies_check(text: str) -> None:
    for procedure_id in CONSTRUCTIVE:
        procedure = all_procedures()[procedure_id]
        assert isinstance(procedure, Constructive)
        lang = procedure.meta.languages[0]
        try:
            produced = procedure.apply(text, lang=lang, seed=0)
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
    for procedure_id in CONSTRUCTIVE:
        procedure = all_procedures()[procedure_id]
        assert isinstance(procedure, Constructive)
        lang = procedure.meta.languages[0]
        try:
            first = procedure.apply(text, lang=lang, seed=7)
        except DenckringError:
            continue
        assert first == procedure.apply(text, lang=lang, seed=7)
