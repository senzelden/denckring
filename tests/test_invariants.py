"""Universal invariants. Every registered procedure, no exceptions."""

import contextlib
import json

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from denckring.core.errors import DenckringError
from denckring.core.registry import all_procedures, get
from denckring.lang import get_pack

SETTINGS = settings(
    max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)


def test_meta_id_matches_registry_key(procedure_id: str) -> None:
    assert get(procedure_id).meta.id == procedure_id


def test_module_name_matches_id(procedure_id: str) -> None:
    assert type(get(procedure_id)).__module__.rsplit(".", 1)[-1] == procedure_id


def test_required_capabilities_exist_in_every_declared_pack(procedure_id: str) -> None:
    proc = get(procedure_id)
    for lang in proc.meta.languages:
        pack = get_pack(lang)
        missing = set(proc.meta.requires) - set(pack.capabilities)
        assert not missing, f"{procedure_id} requires {missing} unsupported by {lang}"


def test_params_schema_is_json_serialisable(procedure_id: str) -> None:
    json.dumps(get(procedure_id).params_schema())


def test_check_is_deterministic_and_well_formed(procedure_id: str) -> None:
    proc = get(procedure_id)

    @SETTINGS
    @given(st.text(max_size=120))
    def run(text: str) -> None:
        try:
            first = proc.check(text)
            second = proc.check(text)
        except DenckringError:
            return  # a required parameter is missing; the per-procedure tests cover it
        assert first == second
        assert 0.0 <= first.score <= 1.0
        assert first.satisfied == (first.score == 1.0)
        assert first.procedure == procedure_id

    run()


def test_check_raises_nothing_but_denckring_error(procedure_id: str) -> None:
    proc = get(procedure_id)

    @SETTINGS
    @given(st.text(max_size=120))
    def run(text: str) -> None:
        with contextlib.suppress(DenckringError):
            proc.check(text)

    run()


def test_registry_is_not_empty() -> None:
    assert all_procedures()


def test_every_declared_language_has_a_golden_case(procedure_id: str) -> None:
    from conftest import load_golden_cases

    proc = get(procedure_id)
    covered = {c.lang for c in load_golden_cases() if c.procedure == procedure_id}
    missing = set(proc.meta.languages) - covered
    assert not missing, (
        f"{procedure_id} declares {sorted(missing)} in its catalogue row "
        f"but has no golden case in those languages"
    )


def test_registered_procedures_are_never_marked_unreachable(procedure_id: str) -> None:
    """If a checker exists, the catalogue row was mis-filed."""
    meta = get(procedure_id).meta
    assert meta.checkability != "none", (
        f"{procedure_id} is registered but its catalogue row says it cannot be "
        f"mechanically checked — one of the two is wrong"
    )


def test_a_satisfied_report_carries_no_violations(procedure_id: str) -> None:
    """Saying yes while listing faults is a contradiction.

    `satisfied == (score == 1.0)` was asserted from the start, but a violation
    that the score never counted could slip past it — the report would say the
    text passed and then list what was wrong with it.
    """
    proc = get(procedure_id)

    @SETTINGS
    @given(st.text(max_size=120))
    def run(text: str) -> None:
        with contextlib.suppress(DenckringError):
            report = proc.check(text)
            if report.satisfied:
                assert not report.violations, (
                    f"{procedure_id} says satisfied but reports "
                    f"{[v.rule for v in report.violations]}"
                )

    run()
