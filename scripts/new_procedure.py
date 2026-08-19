#!/usr/bin/env python
"""Deterministic scaffolding. An agent fills in logic and invents no structure.

    uv run python scripts/new_procedure.py <id>

writes the five files a procedure needs — module, test, strategy, golden fixture and
catalogue row — with FILL IN markers where judgement belongs. It never overwrites.

This is a contributor tool and lives outside the package deliberately. It writes into
`src/denckring/procedures/` and appends to this repository's `catalogue.yaml`, so it
only means anything inside this repository; shipping it as `denckring new` put a command
in every user's CLI that could do nothing useful for them.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from string import Template

TEMPLATES = Path(__file__).resolve().parent / "templates"


def class_name(procedure_id: str) -> str:
    """`reverse_snowball` -> `ReverseSnowball`, `n_plus_7` -> `NPlus7`."""
    return "".join(part.capitalize() for part in re.split(r"[_\-]", procedure_id))


def _render(template: str, procedure_id: str) -> str:
    text = (TEMPLATES / template).read_text(encoding="utf-8")
    return Template(text).substitute(id=procedure_id, **{"class": class_name(procedure_id)})


def scaffold(procedure_id: str, root: Path) -> list[Path]:
    """Write module, test, strategy, golden fixture and catalogue row. Never overwrites."""
    targets = {
        "procedure.py.tmpl": root / f"src/denckring/procedures/{procedure_id}.py",
        "test.py.tmpl": root / f"tests/test_{procedure_id}.py",
        "strategy.py.tmpl": root / f"tests/strategies/{procedure_id}.py",
        "golden.yaml.tmpl": root / f"src/denckring/eval/fixtures/golden/{procedure_id}.yaml",
    }
    for path in targets.values():
        if path.exists():
            raise FileExistsError(f"{path} already exists — refusing to overwrite")

    written: list[Path] = []
    for template, path in targets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_render(template, procedure_id), encoding="utf-8")
        written.append(path)

    catalogue_path = root / "src/denckring/data/catalogue.yaml"
    with catalogue_path.open("a", encoding="utf-8") as handle:
        handle.write(_render("catalogue_row.yaml.tmpl", procedure_id))
    written.append(catalogue_path)
    return written


def main() -> int:
    """Scaffold one procedure, reporting what was written."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("procedure_id", help="the new procedure's id, e.g. reverse_snowball")
    parser.add_argument(
        "--root", type=Path, default=Path("."), help="repository root (default: here)"
    )
    args = parser.parse_args()
    try:
        written = scaffold(args.procedure_id, args.root)
    except FileExistsError as exc:
        print(exc, file=sys.stderr)
        return 1
    for path in written:
        print(f"wrote {path}")
    print(f"Now fill in the FILL IN markers, starting with {args.procedure_id}.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
