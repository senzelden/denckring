"""A verdict cannot move without a checker_version bump (ADR 0061)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from denckring.eval.fingerprint import (
    Probe,
    checkers_digest,
    compare,
    main,
    outcome_digest,
    probe_outcomes,
    run_probe,
)

SNAPSHOT = Path(__file__).parent / "data" / "verdict-fingerprints.json"


def test_no_verdict_moved_without_a_bump() -> None:
    problems = compare(json.loads(SNAPSHOT.read_text(encoding="utf-8")), probe_outcomes())
    assert not problems, "\n".join(problems)


def test_score_noise_past_six_places_is_not_a_move() -> None:
    assert outcome_digest(True, 0.1234561, ["a"]) == outcome_digest(True, 0.1234564, ["a"])
    assert outcome_digest(True, 0.123456, ["a"]) != outcome_digest(True, 0.123457, ["a"])


def test_an_unbumped_move_is_named_as_one() -> None:
    snap = {"r": {"k": ["old", "c1"]}}
    problems = compare(snap, {"r": {"k": ["new", "c1"]}})
    assert problems and "without a checker_version bump" in problems[0]
    assert "r, 1 probes" in problems[0]


def test_a_new_probe_is_not_called_a_verdict_move() -> None:
    snap = {"r": {"k": ["same", "c1"]}}
    problems = compare(snap, {"r": {"k": ["same", "c1"], "k2": ["x", "c1"]}})
    assert problems and "probes changed" in problems[0]
    assert not any("verdict moved" in p for p in problems)


def test_a_vanished_probe_is_not_called_a_verdict_move() -> None:
    problems = compare({"r": {"k": ["a", "c1"], "k2": ["b", "c1"]}}, {"r": {"k": ["a", "c1"]}})
    assert problems and "probes changed" in problems[0]
    assert not any("verdict moved" in p for p in problems)


def test_a_bumped_move_is_called_a_bump_not_an_unbumped_move() -> None:
    snap = {"r": {"k": ["old", "c1"]}}
    problems = compare(snap, {"r": {"k": ["new", "c2"]}})
    assert problems and "checker_version bumped for r" in problems[0]
    assert not any("without a checker_version bump" in p for p in problems)


def test_the_checkers_digest_ignores_order() -> None:
    assert checkers_digest({"a": 1, "b": 2}) == checkers_digest({"b": 2, "a": 1})
    assert checkers_digest({"a": 1, "b": 2}) != checkers_digest({"a": 1, "b": 3})


def test_an_error_is_an_outcome_decided_by_the_static_checkers() -> None:
    from denckring.core.registry import get

    outcome, checkers = run_probe(Probe("sestina", "en", "x", {"no_such_param": 1}))
    assert outcome == run_probe(Probe("sestina", "en", "y", {"other_bad": 2}))[0]
    assert outcome != run_probe(Probe("sestina", "en", "x", {}))[0]
    assert checkers == checkers_digest(
        {"sestina": get("sestina").checker_version, "quenina": get("quenina").checker_version}
    )


def test_a_moved_probe_is_named_by_its_text() -> None:
    snap = {"r": {"k": ["old", "c1"]}}
    problems = compare(snap, {"r": {"k": ["new", "c1"]}}, texts={"k": "The quick brown fox"})
    assert "'The quick brown fox'" in problems[0]


def test_a_text_moved_under_several_params_is_named_once() -> None:
    snap = {"r": {"k": ["old", "c"], "k2": ["old", "c"]}}
    problems = compare(
        snap, {"r": {"k": ["new", "c"], "k2": ["new", "c"]}}, texts={"k": "LVX", "k2": "LVX"}
    )
    assert "2 probes ('LVX')" in problems[0]


def test_the_cli_refuses_an_unknown_argument() -> None:
    with pytest.raises(SystemExit) as refused:
        main(["--frobnicate"])
    assert "usage" in str(refused.value.code)


def test_write_refuses_to_launder_an_unbumped_move(tmp_path: Path) -> None:
    current = probe_outcomes()
    row = next(iter(current))
    key = next(iter(current[row]))
    stale = {r: {k: list(v) for k, v in probes.items()} for r, probes in current.items()}
    stale[row][key] = ["0" * 16, current[row][key][1]]
    path = tmp_path / "snapshot.json"
    text = json.dumps(stale)
    path.write_text(text, encoding="utf-8")

    with pytest.raises(SystemExit) as refused:
        main(["--write"], path=path)
    assert refused.value.code != 0
    assert path.read_text(encoding="utf-8") == text


def test_write_records_a_bump_and_check_passes_after_it(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps({"gone_row": {"k": ["a", "b"]}}), encoding="utf-8")
    main(["--write"], path=path)
    assert not compare(json.loads(path.read_text(encoding="utf-8")), probe_outcomes())
    main([], path=path)


def test_check_mode_exits_non_zero_on_a_problem(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit) as failed:
        main([], path=path)
    assert failed.value.code != 0
