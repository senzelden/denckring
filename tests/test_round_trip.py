"""The seed's central property, testable at last.

Batch 1 was restrictive throughout, so no procedure defined `apply` and
`check(apply(text))` had nothing to run on. The source-relative constructive
procedures are the first that can generate as well as validate.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from denckring.core.protocol import Constructive
from denckring.core.registry import all_procedures

CONSTRUCTIVE = sorted(pid for pid, p in all_procedures().items() if isinstance(p, Constructive))

TEXT = st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=1, max_size=80)


def test_there_is_something_to_round_trip() -> None:
    assert CONSTRUCTIVE, "no procedure defines apply(); the round-trip property is vacuous"


@settings(max_examples=50, deadline=None)
@given(TEXT)
def test_apply_output_satisfies_check(text: str) -> None:
    for procedure_id in CONSTRUCTIVE:
        procedure = all_procedures()[procedure_id]
        assert isinstance(procedure, Constructive)
        produced = procedure.apply(text, seed=0)
        report = procedure.check(produced, source=text)
        assert report.satisfied, (
            f"{procedure_id}: apply produced text that its own check rejects: {produced!r}"
        )


@settings(max_examples=25, deadline=None)
@given(TEXT)
def test_apply_is_deterministic_under_a_fixed_seed(text: str) -> None:
    for procedure_id in CONSTRUCTIVE:
        procedure = all_procedures()[procedure_id]
        assert isinstance(procedure, Constructive)
        assert procedure.apply(text, seed=7) == procedure.apply(text, seed=7)
