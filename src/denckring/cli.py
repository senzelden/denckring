"""The command line. `check` exits 1 when unsatisfied, so it composes in pipelines."""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path
from typing import Annotated, Any, cast, get_args

import typer

from denckring import __version__
from denckring.core import catalogue
from denckring.core.describe import describe, summaries
from denckring.core.errors import DenckringError, UnknownLanguage
from denckring.core.protocol import FAMILIES, Constructive, Lang
from denckring.core.registry import all_procedures, get
from denckring.eval import harness

app = typer.Typer(add_completion=False, help="Experimental writing procedures.")


def _version(value: bool) -> None:
    """Print the installed version and stop. The first thing a bug report needs."""
    if value:
        typer.echo(f"denckring {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool, typer.Option("--version", callback=_version, is_eager=True, help="Show the version.")
    ] = False,
) -> None:
    """Experimental writing procedures."""


catalogue_app = typer.Typer(help="Work with the catalogue as data.")
app.add_typer(catalogue_app, name="catalogue")

CATALOGUE_LICENCE = "CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/"
CATALOGUE_ATTRIBUTION = "denckring catalogue, https://github.com/senzelden/denckring"

EXIT_UNSATISFIED = 1
EXIT_ERROR = 2

MAX_SHOWN_VIOLATIONS = 20


def _lang(value: str) -> Lang:
    """Narrow a command-line string to a supported language, or fail loudly."""
    if value not in get_args(Lang):
        raise UnknownLanguage(value)
    return cast(Lang, value)


def _read(source: str | None) -> str:
    if source is None or source == "-":
        return sys.stdin.read()
    return Path(source).read_text(encoding="utf-8")


def _coerce(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(value)
    except ValueError:
        return value


def _parse_params(pairs: list[str]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for pair in pairs:
        key, separator, value = pair.partition("=")
        if not separator:
            raise typer.BadParameter(f"--param expects key=value, got {pair!r}")
        params[key] = _coerce(value)
    return params


def _fail(exc: DenckringError) -> None:
    typer.echo(str(exc))
    raise typer.Exit(EXIT_ERROR)


@app.command("check")
def check_command(
    procedure_id: str,
    file: Annotated[str | None, typer.Argument(help="Path, or - for stdin")] = None,
    lang: str = "en",
    param: Annotated[list[str] | None, typer.Option("--param", "-p")] = None,
    source: Annotated[
        str | None, typer.Option("--source", help="File the text was made from")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Validate a text. Exits 1 when the text does not satisfy the procedure."""
    try:
        procedure = get(procedure_id)
        params = _parse_params(param or [])
        if source is not None:
            params["source"] = _read(source)
        report = procedure.check(_read(file), lang=_lang(lang), **params)
    except DenckringError as exc:
        _fail(exc)
        return
    if as_json:
        typer.echo(report.model_dump_json(indent=2))
    else:
        mark = "satisfied" if report.satisfied else "not satisfied"
        typer.echo(f"{procedure_id}: {mark} (score {report.score:.3f})")
        for violation in report.violations[:MAX_SHOWN_VIOLATIONS]:
            where = "" if violation.offset is None else f" at {violation.offset}"
            typer.echo(f"  {violation.rule}{where}: found {violation.found!r}")
        if len(report.violations) > MAX_SHOWN_VIOLATIONS:
            typer.echo(f"  … and {len(report.violations) - MAX_SHOWN_VIOLATIONS} more")
    if not report.satisfied:
        raise typer.Exit(EXIT_UNSATISFIED)


@app.command("apply")
def apply_command(
    procedure_id: str,
    file: Annotated[str | None, typer.Argument(help="Path, or - for stdin")] = None,
    lang: str = "en",
    seed: int | None = None,
    param: Annotated[list[str] | None, typer.Option("--param", "-p")] = None,
) -> None:
    """Generate text with a procedure, where the procedure supports it."""
    try:
        procedure = get(procedure_id)
    except DenckringError as exc:
        _fail(exc)
        return
    if not isinstance(procedure, Constructive):
        typer.echo(
            f"Procedure {procedure_id!r} has no generator in this install. "
            f"Its kind is {procedure.meta.kind}, so the form admits one, but none is "
            f"implemented here — see `describe {procedure_id}`, field `constructive`."
        )
        raise typer.Exit(EXIT_ERROR)
    # Forwarded only when asked for, because `seed` is a parameter of the ten
    # procedures that draw and not of the other seventeen. Sending the unset
    # `None` to a procedure that takes no seed would be an `InvalidParams` on
    # every invocation; sending a real one is a caller error worth reporting.
    drawn = {"seed": seed} if seed is not None else {}
    try:
        typer.echo(
            procedure.apply(_read(file), lang=_lang(lang), **drawn, **_parse_params(param or []))
        )
    except DenckringError as exc:
        _fail(exc)


@app.command("describe")
def describe_command(
    procedure_id: str,
    as_json: Annotated[bool, typer.Option("--json")] = False,
    scholarly: Annotated[bool, typer.Option("--scholarly")] = False,
    lang: Annotated[str, typer.Option("--lang")] = "en",
) -> None:
    """A procedure as a machine reads it: definition, hints, parameter schema."""
    try:
        described = describe(procedure_id, lang=_lang(lang), scholarly=scholarly)
    except DenckringError as exc:
        _fail(exc)
        return
    if as_json:
        typer.echo(described.model_dump_json(indent=2))
        return
    typer.echo(f"{described.id}  {described.name}")
    typer.echo(described.definition)
    if described.prompt_hints:
        typer.echo(f"\nHint: {described.prompt_hints}")
    if not described.runnable:
        typer.echo(f"\nNot runnable here — missing: {', '.join(described.missing)}")


@app.command("list")
def list_command(
    lang: str | None = None,
    kind: str | None = None,
    family: Annotated[str | None, typer.Option(help="|".join(FAMILIES))] = None,
    status: Annotated[str | None, typer.Option(help="catalogued|implemented|validated")] = None,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """List catalogue entries."""
    if as_json and (kind or status):
        typer.echo(
            "--json cannot be combined with --kind or --status: summaries() has no "
            "such filters, so the flag would silently be ignored rather than applied."
        )
        raise typer.Exit(EXIT_ERROR)
    if family and family not in FAMILIES:
        typer.echo(f"Unknown family {family!r}. Known families: {', '.join(FAMILIES)}")
        raise typer.Exit(EXIT_ERROR)
    if as_json:
        try:
            rows = summaries(family=family, lang=_lang(lang) if lang else "en")
        except DenckringError as exc:
            _fail(exc)
            return
        typer.echo(json.dumps([row.model_dump() for row in rows], indent=2))
        return
    implemented = set(harness.implemented_ids())
    validated = set(harness.validated_ids())
    for procedure_id in catalogue.ids():
        meta = catalogue.get(procedure_id)
        if procedure_id in validated:
            entry_status = "validated"
        elif procedure_id in implemented:
            entry_status = "implemented"
        else:
            entry_status = "catalogued"
        if lang and lang not in meta.languages:
            continue
        if kind and meta.kind != kind:
            continue
        if family and meta.family != family:
            continue
        if status and entry_status != status:
            continue
        typer.echo(f"{procedure_id:24} {entry_status:12} {meta.names.get('en', '')}")


@app.command("search")
def search_command(term: str) -> None:
    """Find procedures by id, name or alias. Exits 1 when nothing matches."""
    needle = term.casefold()
    matches: list[str] = []
    for procedure_id in catalogue.ids():
        meta = catalogue.get(procedure_id)
        haystack = [procedure_id, *meta.names.values(), *meta.aliases]
        if any(needle in field.casefold() for field in haystack):
            matches.append(procedure_id)
    if not matches:
        typer.echo(f"No procedure matches {term!r}.")
        raise typer.Exit(EXIT_UNSATISFIED)
    for procedure_id in matches:
        meta = catalogue.get(procedure_id)
        alias_note = f"  (also: {', '.join(meta.aliases)})" if meta.aliases else ""
        typer.echo(f"{procedure_id:24} {meta.family:12} {meta.names.get('en', '')}{alias_note}")


@app.command("show")
def show_command(
    procedure_id: str,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Show a procedure's metadata, parameters and golden examples."""
    try:
        meta = catalogue.get(procedure_id)
    except DenckringError as exc:
        _fail(exc)
        return
    examples = [c.model_dump() for c in harness.golden_cases() if c.procedure == procedure_id]
    schema: dict[str, Any] = {}
    if procedure_id in all_procedures():
        schema = get(procedure_id).params_schema()
    if as_json:
        typer.echo(
            json.dumps(
                {"meta": meta.model_dump(), "params_schema": schema, "examples": examples},
                indent=2,
                ensure_ascii=False,
            )
        )
        return
    typer.echo(f"{meta.names.get('en', procedure_id)} ({meta.id})")
    typer.echo(f"  {meta.definitions.get('en', '')}")
    typer.echo(f"  source: {meta.source}")
    typer.echo(f"  kind: {meta.kind}   languages: {', '.join(meta.languages)}")
    typer.echo(f"  requires: {', '.join(meta.requires) or '—'}")
    for example in examples:
        typer.echo(f"  example [{example['name']}] satisfied={example['satisfied']}")


@app.command("status")
def status_command(as_json: Annotated[bool, typer.Option("--json")] = False) -> None:
    """Print catalogue coverage — the project metric."""
    coverage = harness.status()
    typer.echo(coverage.model_dump_json(indent=2) if as_json else coverage.line())


@app.command("eval")
def eval_command(
    run_all: Annotated[bool, typer.Option("--all")] = True,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Run every golden example. Exits non-zero on regression."""
    board = harness.run()
    if as_json:
        typer.echo(board.model_dump_json(indent=2))
    else:
        for result in board.results:
            mark = "ok  " if result.passed else "FAIL"
            detail = f"  — {result.detail}" if result.detail else ""
            typer.echo(f"{mark} {result.procedure:24} {result.case}{detail}")
        procedures = len({r.procedure for r in board.results})
        typer.echo(f"{procedures} procedures · {board.passed} passed · {board.failed} failed")
        typer.echo(board.coverage.line())
    if not board.ok:
        raise typer.Exit(EXIT_UNSATISFIED)


@catalogue_app.command("export")
def catalogue_export(
    export_format: Annotated[str, typer.Option("--format")] = "json",
    output: Annotated[Path | None, typer.Option("--output")] = None,
) -> None:
    """Emit the catalogue as a standalone dataset."""
    rows = [catalogue.get(pid).model_dump() for pid in catalogue.ids()]
    if export_format == "json":
        text = json.dumps(
            {
                "licence": CATALOGUE_LICENCE,
                "attribution": CATALOGUE_ATTRIBUTION,
                "count": len(rows),
                "procedures": rows,
            },
            indent=2,
            ensure_ascii=False,
        )
    elif export_format == "csv":
        buffer = io.StringIO()
        columns = ["id", "family", "kind", "attribution", "source", "name_en", "definition_en"]
        writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "id": row["id"],
                    "family": row["family"],
                    "kind": row["kind"],
                    "attribution": row["attribution"],
                    "source": row["source"],
                    "name_en": row["names"].get("en", ""),
                    "definition_en": row["definitions"].get("en", ""),
                }
            )
        text = buffer.getvalue()
    else:
        typer.echo(f"Unknown format {export_format!r}. Use json or csv.")
        raise typer.Exit(EXIT_ERROR)
    if output is None:
        typer.echo(text)
    else:
        output.write_text(text, encoding="utf-8")
        typer.echo(f"wrote {output}")
