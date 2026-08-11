"""Level 2: generated texts must agree with the checker, both ways."""

from hypothesis import HealthCheck, given, settings

from conftest import strategy_module
from denckring import check
from strategies import Case

SETTINGS = settings(
    max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)


def test_satisfying_texts_check_true(procedure_id: str) -> None:
    module = strategy_module(procedure_id)

    @SETTINGS
    @given(module.satisfying())
    def run(case: Case) -> None:
        text, params = case
        report = check(procedure_id, text, **params)
        assert report.satisfied, f"{text!r} with {params} should satisfy {procedure_id}"
        assert report.score == 1.0

    run()


def test_violating_texts_check_false(procedure_id: str) -> None:
    module = strategy_module(procedure_id)

    @SETTINGS
    @given(module.violating())
    def run(case: Case) -> None:
        text, params = case
        report = check(procedure_id, text, **params)
        assert not report.satisfied, f"{text!r} with {params} should violate {procedure_id}"
        assert report.violations

    run()
