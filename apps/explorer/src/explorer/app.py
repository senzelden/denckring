"""The explorer: a local browser for the catalogue and a bench for the procedures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from denckring import __version__
from denckring import check as denckring_check
from denckring.core import catalogue
from denckring.core.errors import UnknownProcedure
from denckring.core.protocol import Constructive
from denckring.core.registry import all_procedures, get
from explorer import bench, board, catalogue_view, corpora, env, stage, witz

env.load()

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


@app.get("/board", response_class=HTMLResponse)
def the_board(request: Request) -> HTMLResponse:
    """Every procedure's golden cases, run now and laid out to be scanned."""
    return page(
        request,
        "board.html",
        page_id="board",
        tiles=board.tiles(),
        scoreboard=board.scoreboard_line(),
    )


@app.get("/stage", response_class=HTMLResponse)
def the_stage(request: Request, chrome: str = "on") -> HTMLResponse:
    return page(request, "stage_index.html", scenes=stage.SCENES, chrome_off=chrome == "off")


@app.get("/stage/denckring", response_class=HTMLResponse)
def stage_denckring(request: Request, chrome: str = "on") -> HTMLResponse:
    return page(
        request,
        "stage_denckring.html",
        scene=stage.scene("denckring"),
        rings=stage.rings(),
        chrome_off=chrome == "off",
    )


@app.post("/stage/denckring/act", response_class=HTMLResponse)
async def stage_denckring_act(request: Request) -> HTMLResponse:
    """Check the word the rings currently spell, or turn them to a new one."""
    form = dict(await request.form())
    word = str(form.get("word", ""))
    if form.get("turn"):
        procedure = get("denckring")
        # `get` is typed as the base class, which has no `apply` — ADR 0002 keeps
        # it off `BaseProcedure` because it is optional. Narrow once, here.
        assert isinstance(procedure, Constructive)
        word = procedure.apply("", lang="en")
    report = denckring_check("denckring", word) if word else None
    return page(request, "_stage_word.html", word=word, report=report)


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
        corpora=corpora.available() if implemented and bench.wants_corpus(procedure_id) else [],
        can_read=witz.available(),
        missing=catalogue_view.sort_for(
            meta, set(all_procedures()), catalogue_view._capabilities()
        ).missing,
    )


def _corpus_from(form: dict[str, Any]) -> tuple[str, str]:
    """The corpus the bench has loaded, read here rather than posted back.

    A 28,000-entry corpus is 5.8MB, which the form-field size limit refuses
    outright — so the browser carries the path and the file is read server-side.
    """
    path = str(form.pop("corpus_path", ""))
    return corpora.load(path) if path else ("", "")


@app.post("/p/{procedure_id}/check", response_class=HTMLResponse)
async def check(request: Request, procedure_id: str) -> HTMLResponse:
    form = dict(await request.form())
    text = str(form.pop("text", ""))
    lang = str(form.pop("lang", "en"))
    corpus, corpus_problem = _corpus_from(form)
    if corpus_problem:
        return page(request, "_proof.html", report=None, problem=corpus_problem)
    if corpus:
        form["source"] = corpus
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
    corpus, corpus_problem = _corpus_from(form)
    if corpus_problem:
        return page(request, "_generated.html", produced="", problem=corpus_problem)
    # `apply` takes the corpus as its text — the bench's own text box is the
    # source only when no corpus is loaded.
    text = corpus or text
    fields = bench.fields_for(procedure_id)
    headword = str(form.get("headword", ""))
    style = str(form.pop("style", witz.DEFAULT_REGISTER))
    try:
        params = bench.coerce(fields, {k: str(v) for k, v in form.items()})
    except ValueError as exc:
        # The check route has always guarded this; apply used to let the
        # ValueError escape as a 500 for any procedure with an integer field.
        return page(request, "_generated.html", produced="", problem=f"That is not a number: {exc}")
    produced, problem = bench.generate(procedure_id, text, lang, params)
    return page(
        request,
        "_generated.html",
        produced=produced,
        problem=problem,
        procedure_id=procedure_id,
        headword=headword,
        lang=lang,
        style=style,
        can_read=witz.available() and bench.wants_corpus(procedure_id),
    )


@app.post("/p/{procedure_id}/corpus", response_class=HTMLResponse)
async def load_corpus(request: Request, procedure_id: str) -> HTMLResponse:
    """Put a corpus from disk into the bench, and list its headwords."""
    form = dict(await request.form())
    path = str(form.get("path", ""))
    text, problem = corpora.load(path)
    chosen = next((c for c in corpora.available() if c.path == path), None)
    return page(
        request,
        "_bench.html",
        meta=catalogue.get(procedure_id),
        fields=bench.fields_for(procedure_id),
        languages=bench.languages_for(procedure_id),
        can_apply=bench.can_apply(procedure_id),
        corpora=corpora.available(),
        can_read=witz.available(),
        headwords=corpora.headwords_of(text),
        loaded_path=path if not problem else "",
        loaded_name=chosen.name if chosen else "",
        loaded_entries=chosen.entries if chosen else 0,
        loaded_style=chosen.style if chosen else witz.DEFAULT_REGISTER,
        problem=problem,
    )


@app.post("/p/{procedure_id}/witz", response_class=HTMLResponse)
async def read_witz(request: Request) -> HTMLResponse:
    """A reading of one throw. Not a verdict — see explorer.witz."""
    form = dict(await request.form())
    reading = witz.read(
        str(form.get("throw", "")),
        headword=str(form.get("headword", "")),
        lang=str(form.get("lang", "en")),
        register=str(form.get("style", witz.DEFAULT_REGISTER)),
    )
    return page(request, "_witz.html", reading=reading.text, problem=reading.problem)


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
