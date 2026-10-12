"""The verdict fingerprint: no checker's verdict moves without a bump (ADR 0061).

A probe is one golden text of a row and language, checked with one of the parameter sets
the golden cases of that row and language use. Each probe records two digests: its
outcome (`satisfied`, the score to six places, the set of violation rules, or the error
code it raised) and the checker versions that decided it (`provenance.checkers`).

`tests/test_verdict_fingerprints.py` compares a fresh run with the snapshot in
`tests/data/verdict-fingerprints.json`. An outcome that moved while its checkers digest
did not is a verdict moved without a bump. Run
`uv run python -m denckring.eval.fingerprint --write` to refresh the snapshot after a
bump or a golden-case change; it refuses while any verdict has moved unbumped, so the
snapshot cannot launder one.

The checkers digest is per probe rather than one version per row, because a delegating
row (`sestina`, the translations, `telestich`) is decided by its delegate's version as
well as its own, and `multiple_constraint`'s delegates depend on the call.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from denckring.core.protocol import Lang

#: The checked-in snapshot, for a source checkout. The module is a development tool; an
#: installed wheel has no `tests/`.
SNAPSHOT = Path(__file__).resolve().parents[3] / "tests" / "data" / "verdict-fingerprints.json"

WRITE_HINT = "run `uv run python -m denckring.eval.fingerprint --write`"

#: row -> probe key -> [outcome digest, checkers digest]
Fingerprints = Mapping[str, Mapping[str, Sequence[str]]]


def _digest(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def outcome_digest(satisfied: bool, score: float, rules: Iterable[str]) -> str:
    """What a caller scores on. Rounding to six places keeps platform float noise out."""
    return _digest([satisfied, round(score, 6), sorted(set(rules))])


def checkers_digest(checkers: Mapping[str, int]) -> str:
    """The versions of every row that decided a verdict, as `provenance.checkers` has them."""
    return _digest(sorted(checkers.items()))


@dataclass(frozen=True)
class Probe:
    procedure: str
    lang: Lang
    text: str
    params: dict[str, Any]

    @property
    def key(self) -> str:
        return _digest([self.lang, self.text, self.params])


def probes() -> list[Probe]:
    """Every distinct golden text of a row and language, crossed with every parameter set.

    Crossing rather than pairing is the point: a fixture pins one (text, params) pair,
    and a regression often shows at a parameter value no fixture pairs with that text.
    """
    from denckring import golden_cases

    texts: dict[tuple[str, Lang], dict[str, None]] = defaultdict(dict)
    params: dict[tuple[str, Lang], dict[str, dict[str, Any]]] = defaultdict(dict)
    for case in golden_cases():
        group = (case.procedure, case.lang)
        texts[group][case.text] = None
        params[group][json.dumps(case.params, sort_keys=True)] = case.params
    return [
        Probe(pid, lang, text, p)
        for (pid, lang), group_texts in sorted(texts.items())
        for text in group_texts
        for p in params[(pid, lang)].values()
    ]


def missing_cases() -> list[str]:
    """`row/lang: name` of each golden case this install cannot run, for want of a pack.

    Probes are built from the runnable cases, so on such an install a row loses probes,
    and a row that stays runnable loses parameter sets too. Neither is a verdict, and a
    snapshot written then would drop them silently, so the guard skips and `--write`
    refuses (ADR 0061).
    """
    from denckring import golden_cases

    # A multiset difference, not a set one: the corpus holds exact duplicate cases.
    every = Counter(f"{c.procedure}/{c.lang}: {c.name}" for c in golden_cases(runnable=False))
    runnable = Counter(f"{c.procedure}/{c.lang}: {c.name}" for c in golden_cases())
    return sorted((every - runnable).elements())


def run_probe(probe: Probe) -> list[str]:
    from denckring import check
    from denckring.core.errors import DenckringError
    from denckring.core.registry import get

    try:
        report = check(probe.procedure, probe.text, lang=probe.lang, **probe.params)
    except DenckringError as error:
        # An error is an outcome like any other. No report carries the checkers, so take
        # the row's own version and its static delegates'.
        row = get(probe.procedure)
        versions = {row.id: row.checker_version} | {i: get(i).checker_version for i in row.composes}
        return [_digest(f"error:{error.code}"), checkers_digest(versions)]
    # `BaseProcedure.check` stamps provenance on every report it returns.
    assert report.provenance is not None
    rules = [v.rule for v in report.violations]
    return [
        outcome_digest(report.satisfied, report.score, rules),
        checkers_digest(report.provenance.checkers),
    ]


def probe_outcomes() -> dict[str, dict[str, list[str]]]:
    """row -> probe key -> [outcome digest, checkers digest], for this install's run."""
    current: dict[str, dict[str, list[str]]] = defaultdict(dict)
    for probe in probes():
        current[probe.procedure][probe.key] = run_probe(probe)
    return dict(current)


def _texts() -> dict[str, str]:
    return {probe.key: probe.text for probe in probes()}


def _shorten(text: str, width: int = 60) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= width else flat[: width - 1] + "…"


def unbumped_moves(snapshot: Fingerprints, current: Fingerprints) -> dict[str, list[str]]:
    """row -> probe keys whose outcome moved while their checkers digest did not."""
    moved: dict[str, list[str]] = {}
    for row in sorted(set(snapshot) & set(current)):
        keys = [
            key
            for key in sorted(set(snapshot[row]) & set(current[row]))
            if snapshot[row][key][1] == current[row][key][1]
            and snapshot[row][key][0] != current[row][key][0]
        ]
        if keys:
            moved[row] = keys
    return moved


def compare(
    snapshot: Fingerprints, current: Fingerprints, texts: Mapping[str, str] | None = None
) -> list[str]:
    """Every way `current` departs from `snapshot`, one line per row and kind.

    `texts` maps probe keys to their texts, for naming moved probes; by default it is
    built from the golden cases.
    """
    problems: list[str] = []
    moved = unbumped_moves(snapshot, current)
    if moved and texts is None:
        texts = _texts()
    for row, keys in moved.items():
        # One text crossed with several parameter sets is several probes; name it once.
        distinct = dict.fromkeys(_shorten((texts or {}).get(k, k)) for k in keys)
        named = "; ".join(repr(t) for t in list(distinct)[:3])
        problems.append(
            f"verdict moved without a checker_version bump: {row}, {len(keys)} probes ({named})"
        )
    for row in sorted(set(snapshot) | set(current)):
        before, after = snapshot.get(row, {}), current.get(row, {})
        if any(before[k][1] != after[k][1] for k in set(before) & set(after)):
            problems.append(
                f"checker_version bumped for {row} (or a row it composes); {WRITE_HINT}"
            )
        if set(before) != set(after):
            problems.append(f"golden probes changed for {row}; {WRITE_HINT}")
    return problems


def main(argv: Sequence[str] | None = None, *, path: Path = SNAPSHOT) -> None:
    """Check the snapshot, or with `--write` refresh it unless a verdict moved unbumped."""
    args = list(sys.argv[1:] if argv is None else argv)
    write = args == ["--write"]
    if args and not write:
        raise SystemExit("usage: python -m denckring.eval.fingerprint [--write]")
    if write and (missing := missing_cases()):
        shown = ", ".join(missing[:5]) + (", …" if len(missing) > 5 else "")
        raise SystemExit(
            f"refusing to write: {len(missing)} golden cases cannot run on this install, "
            f"so a data pack is missing ({shown}); install every extra first"
        )
    snapshot = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    current = probe_outcomes()
    if write:
        moved = unbumped_moves(snapshot, current)
        if moved:
            for line in compare(snapshot, current):
                if "without a checker_version bump" in line:
                    print(line, file=sys.stderr)
            raise SystemExit(
                f"refusing to write: bump checker_version for {', '.join(moved)} first"
            )
        path.write_text(json.dumps(current, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {sum(map(len, current.values()))} probes over {len(current)} rows")
        return
    problems = compare(snapshot, current)
    if problems:
        raise SystemExit("\n".join(problems))
    print("no verdict moved without a checker_version bump")


if __name__ == "__main__":  # pragma: no cover
    main()
