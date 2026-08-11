"""Deterministic scaffolding. An agent fills in logic and invents no structure."""

from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path
from string import Template

TEMPLATES = Path(str(files("denckring") / "scaffold" / "templates"))


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
