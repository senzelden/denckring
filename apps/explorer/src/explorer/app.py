"""The explorer: a local browser for the catalogue and a bench for the procedures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from denckring import __version__
from denckring.core import catalogue
from denckring.core.errors import UnknownProcedure
from denckring.core.registry import all_procedures
from explorer import bench, catalogue_view

HERE = Path(__file__).parent

app = FastAPI(title="denckring explorer", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")

#: What each drawer of the case holds. Written for a reader, not copied from the
#: catalogue's own family table.
DRAWER_NOTES = {
    "letter": "Rules about the characters themselves — which may appear, how often, in what order.",
    "word": "Rules about whole words, most of them needing a dictionary to walk.",
    "syntax": "Rules about the shape of sentences rather than the words in them.",
    "form": "Metre, rhyme and stanza: the inherited fixed forms.",
    "permutation": "A fixed set of parts, reordered — the Denckring's own family.",
    "procedural": "A process applied to source material, from cut-up to erasure.",
    "translation": "Carrying a text across by something other than its meaning.",
    "visual": "What the text looks like on the page.",
}


def page(request: Request, name: str, **context: Any) -> HTMLResponse:
    return templates.TemplateResponse(request, name, {"version": __version__, **context})


@app.get("/", response_class=HTMLResponse)
def the_case(request: Request) -> HTMLResponse:
    return page(
        request,
        "case.html",
        drawers=catalogue_view.case(),
        coverage=catalogue_view.coverage(),
        notes=DRAWER_NOTES,
    )


@app.get("/missing", response_class=HTMLResponse)
def missing(request: Request) -> HTMLResponse:
    return page(
        request,
        "missing.html",
        coverage=catalogue_view.coverage(),
        gaps=catalogue_view.gaps(),
        unreachable=catalogue_view.unreachable(),
    )


@app.get("/search", response_class=HTMLResponse)
def search(request: Request, q: str = "") -> HTMLResponse:
    return page(request, "_results.html", results=catalogue_view.find(q), term=q)


@app.get("/p/{procedure_id}", response_class=HTMLResponse)
def procedure(request: Request, procedure_id: str) -> HTMLResponse:
    try:
        meta = catalogue.get(procedure_id)
    except UnknownProcedure:
        return page(request, "unknown.html", procedure_id=procedure_id)
    implemented = procedure_id in all_procedures()
    return page(
        request,
        "procedure.html",
        meta=meta,
        implemented=implemented,
        fields=bench.fields_for(procedure_id) if implemented else [],
        examples=bench.examples_for(procedure_id) if implemented else [],
        languages=bench.languages_for(procedure_id) if implemented else [],
        can_apply=bench.can_apply(procedure_id) if implemented else False,
        missing=catalogue_view.sort_for(
            meta, set(all_procedures()), catalogue_view._capabilities()
        ).missing,
    )


@app.post("/p/{procedure_id}/check", response_class=HTMLResponse)
async def check(request: Request, procedure_id: str) -> HTMLResponse:
    form = dict(await request.form())
    text = str(form.pop("text", ""))
    lang = str(form.pop("lang", "en"))
    fields = bench.fields_for(procedure_id)
    try:
        params = bench.coerce(fields, {k: str(v) for k, v in form.items()})
    except ValueError as exc:
        return page(request, "_proof.html", report=None, problem=f"That is not a number: {exc}")
    report, problem = bench.run(procedure_id, text, lang, params)
    return page(
        request,
        "_proof.html",
        report=report,
        problem=problem,
        marked=bench.mark_up(text, report) if report else "",
        text=text,
    )


@app.post("/p/{procedure_id}/apply", response_class=HTMLResponse)
async def apply(request: Request, procedure_id: str) -> HTMLResponse:
    form = dict(await request.form())
    text = str(form.pop("text", ""))
    lang = str(form.pop("lang", "en"))
    fields = bench.fields_for(procedure_id)
    params = bench.coerce(fields, {k: str(v) for k, v in form.items()})
    produced, problem = bench.generate(procedure_id, text, lang, params)
    return page(request, "_generated.html", produced=produced, problem=problem)


@app.post("/p/{procedure_id}/example", response_class=HTMLResponse)
def load_example(request: Request, procedure_id: str, index: int = Form(...)) -> HTMLResponse:
    examples = bench.examples_for(procedure_id)
    example = examples[index] if 0 <= index < len(examples) else None
    return page(
        request,
        "_bench.html",
        meta=catalogue.get(procedure_id),
        fields=bench.fields_for(procedure_id),
        languages=bench.languages_for(procedure_id),
        can_apply=bench.can_apply(procedure_id),
        example=example,
    )
