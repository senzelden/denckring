#!/usr/bin/env python
"""Generate the documentation gallery from the catalogue and the golden fixtures.

Nothing here is written by hand, which is what makes 145 entries maintainable —
and the gallery cannot drift, because a fixture that stopped matching its
recorded result would fail the test suite long before it reached the docs.

Output is gitignored and rebuilt on every docs build. A committed generated file
is a file that can be stale.
"""

from __future__ import annotations

import shutil
from collections import defaultdict
from pathlib import Path

from denckring.core import catalogue
from denckring.core.protocol import FAMILIES, Meta
from denckring.core.registry import all_procedures
from denckring.eval import harness

ROOT = Path(__file__).resolve().parents[1]
GALLERY = ROOT / "docs" / "gallery"

FAMILY_BLURB = {
    "letter": "Procedures operating on individual characters.",
    "word": "Procedures operating on whole words, usually by way of a lexicon.",
    "syntax": "Procedures operating on sentence and clause structure.",
    "form": "Metre, rhyme and stanza.",
    "permutation": "Reordering a fixed set of parts.",
    "procedural": "A process applied to source material.",
    "translation": "Mapping one text onto another.",
    "visual": "The shape of the text on the page.",
}

CHECKABILITY_BLURB = {
    "self": "decidable from the text and its parameters alone",
    "source": "decidable against the source text it was made from",
    "none": "no computable acceptance criterion exists",
}

ATTRIBUTION_BLURB = {
    "primary": "a named author, work and year this catalogue stands behind",
    "reference": "attested in a standard reference rather than traced to an origin",
    "traditional": "classical or folk; no single origin to name",
}


def slug(procedure_id: str) -> str:
    return f"{procedure_id}.md"


def status_of(procedure_id: str, implemented: set[str], validated: set[str]) -> str:
    if procedure_id in validated:
        return "validated"
    if procedure_id in implemented:
        return "implemented"
    return "catalogued"


def render_examples(procedure_id: str) -> list[str]:
    cases = [c for c in harness.golden_cases() if c.procedure == procedure_id]
    if not cases:
        return []
    lines = ["", "## Examples", ""]
    for case in cases:
        verdict = "satisfies" if case.satisfied else "does not satisfy"
        lines.append(f"### {case.name}")
        lines.append("")
        lines.append(f"*{case.lang}* — this text **{verdict}** the procedure.")
        lines.append("")
        lines.append("```text")
        lines.extend(case.text.split("\n"))
        lines.append("```")
        lines.append("")
        if case.params:
            rendered = ", ".join(f"`{k}={v!r}`" for k, v in case.params.items())
            lines.append(f"Parameters: {rendered}")
            lines.append("")
        if case.source:
            lines.append(f"Source: {case.source}")
            lines.append("")
    return lines


def render_procedure(meta: Meta, implemented: set[str], validated: set[str]) -> str:
    state = status_of(meta.id, implemented, validated)
    lines = [
        f"# {meta.names.get('en', meta.id)}",
        "",
        f"`{meta.id}` · {meta.family} · **{state}**",
        "",
        meta.definitions.get("en", ""),
        "",
        "## Provenance",
        "",
        f"- **Source:** {meta.source}",
        f"- **Attribution:** `{meta.attribution}` — {ATTRIBUTION_BLURB.get(meta.attribution, '')}",
        f"- **Checkability:** `{meta.checkability}` — "
        f"{CHECKABILITY_BLURB.get(meta.checkability, '')}",
        "",
        "## Details",
        "",
        f"- **Kind:** {meta.kind}",
        f"- **Languages:** {', '.join(meta.languages)}",
        f"- **Requires:** {', '.join(f'`{c}`' for c in meta.requires) or '—'}",
        f"- **Deterministic:** {'yes' if meta.deterministic else 'no'}",
    ]
    if meta.aliases:
        lines.append(f"- **Also known as:** {', '.join(meta.aliases)}")

    other_names = {k: v for k, v in meta.names.items() if k != "en"}
    if other_names:
        rendered = ", ".join(f"{v} (*{k}*)" for k, v in sorted(other_names.items()))
        lines.append(f"- **In other languages:** {rendered}")

    if hint := meta.prompt_hints.get("en"):
        lines += ["", "## Prompt hint", "", f"> {hint}"]

    if meta.id in implemented:
        schema = all_procedures()[meta.id].params_schema()
        properties = schema.get("properties", {})
        if properties:
            lines += [
                "",
                "## Parameters",
                "",
                "| Name | Type | Default | Description |",
                "| --- | --- | --- | --- |",
            ]
            for name, spec in sorted(properties.items()):
                kind = spec.get("type", "—")
                default = spec.get("default", "—")
                description = spec.get("description", "")
                lines.append(f"| `{name}` | {kind} | `{default}` | {description} |")
    elif meta.checkability == "none":
        lines += [
            "",
            "## Why this has no checker",
            "",
            "This procedure has no computable acceptance criterion, so it will never be "
            "implemented. It is catalogued because the form belongs in an honest survey "
            "of the field, and `denckring status` counts it separately rather than "
            "reporting a gap that cannot close.",
        ]

    lines += render_examples(meta.id)
    return "\n".join(lines) + "\n"


def render_index(entries: dict[str, Meta], implemented: set[str], validated: set[str]) -> str:
    coverage = harness.status()
    by_family: dict[str, list[Meta]] = defaultdict(list)
    for meta in entries.values():
        by_family[meta.family].append(meta)

    lines = [
        "# Gallery",
        "",
        f"{coverage.line()}",
        "",
        "Every example below is a golden fixture the test suite enforces, so nothing on "
        "these pages can drift from what the code actually does.",
        "",
    ]
    for family in FAMILIES:
        members = sorted(by_family.get(family, []), key=lambda m: m.id)
        if not members:
            continue
        lines += [
            f"## {family}",
            "",
            FAMILY_BLURB.get(family, ""),
            "",
            "| Procedure | Status | Source |",
            "| --- | --- | --- |",
        ]
        for meta in members:
            state = status_of(meta.id, implemented, validated)
            name = meta.names.get("en", meta.id)
            lines.append(f"| [{name}]({slug(meta.id)}) | {state} | {meta.source} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    entries = catalogue.load()
    implemented = set(harness.implemented_ids())
    validated = set(harness.validated_ids())

    if GALLERY.exists():
        shutil.rmtree(GALLERY)
    GALLERY.mkdir(parents=True)

    (GALLERY / "index.md").write_text(
        render_index(entries, implemented, validated), encoding="utf-8"
    )
    for meta in entries.values():
        (GALLERY / slug(meta.id)).write_text(
            render_procedure(meta, implemented, validated), encoding="utf-8"
        )
    print(f"wrote {len(entries) + 1} pages to {GALLERY.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
