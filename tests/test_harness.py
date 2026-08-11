from denckring.eval import harness


def test_run_is_green_on_the_shipped_fixtures() -> None:
    board = harness.run()
    assert board.failed == 0
    assert board.ok
    assert board.passed == len(harness.golden_cases())


def test_status_counts_are_consistent() -> None:
    coverage = harness.status()
    assert coverage.catalogued >= coverage.implemented >= coverage.validated
    assert coverage.implemented == len(harness.implemented_ids())


def test_scoreboard_serialises_to_json() -> None:
    harness.run().model_dump_json()


def test_coverage_separates_implementable_from_unreachable() -> None:
    coverage = harness.status()
    assert coverage.implementable < coverage.catalogued
    assert coverage.unreachable > 0
    assert coverage.implementable + coverage.unreachable == coverage.catalogued


def test_implemented_never_exceeds_implementable() -> None:
    coverage = harness.status()
    assert coverage.implemented <= coverage.implementable


def test_coverage_line_names_the_unreachable_rows() -> None:
    assert "not mechanically checkable" in harness.status().line()
