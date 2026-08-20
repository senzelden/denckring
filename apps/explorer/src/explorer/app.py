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
from denckring.core.protocol import Constructive, Lang
from denckring.core.registry import all_procedures, get
from denckring.procedures.n_plus_7 import displace
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
        # The board borrows the stage's shell, which asks whether the chrome is
        # off; it has no `?chrome=off` of its own, so it answers rather than
        # leaving the template to read an undefined name as false.
        chrome_off=False,
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
        rhyme_endings=stage.RHYME_ENDINGS,
        chrome_off=chrome == "off",
    )


@app.post("/stage/denckring/act", response_class=HTMLResponse)
async def stage_denckring_act(request: Request) -> HTMLResponse:
    """Check the word the rings currently spell, turn them to a new one, or
    search for one German actually knows.

    Two verdicts, not one — `check("denckring", word)` can never fail for a
    word the rings themselves produced, which is why a single verdict button
    told a viewer nothing (see the task brief). "Off the rings" carries that
    always-true check anyway, with its reason on screen; "a word German
    knows" is `is_word`, the one that can actually fail.
    """
    form = dict(await request.form())
    word = str(form.get("word", ""))
    pieces: list[str] | None = None
    find_failed = False
    turn_failed = False
    if form.get("turn"):
        procedure = get("denckring")
        # `get` is typed as the base class, which has no `apply` — ADR 0002 keeps
        # it off `BaseProcedure` because it is optional. Degrade rather than raise
        # if that assumption ever stops holding, as `bench.generate` does.
        if isinstance(procedure, Constructive):
            word = ""
            # Draw-then-check every iteration, including the last one. An
            # earlier version drew once, then only re-checked *before*
            # redrawing on failure — so a run that missed on every one of
            # TURN_ATTEMPTS draws exited having just redrawn, and that final
            # draw reached pieces_for(word) below unchecked. That is the
            # exact "the filter covers four of five paths" defect this whole
            # round exists to close, even though it would take roughly 50
            # consecutive misses at the measured ~0.0315% per-draw failure
            # rate to ever actually happen.
            for _ in range(stage.TURN_ATTEMPTS):
                candidate = procedure.apply("", lang="de")
                if stage.fit_for_stage(candidate):
                    word = candidate
                    break
            # Every draw missing is astronomically unlikely, but if it ever
            # happens, say so rather than show a word that never passed the
            # filter. An empty panel with no verdict and no line of prose was
            # the earlier answer here, described in this comment as "the same
            # honest fallback `find_word`'s `find_failed` already uses" — which
            # it was not: that path renders a sentence saying the search came
            # up empty. This one now does too, in its own words, so the two
            # really are the same move.
            turn_failed = not word

            # The library chose this word; hand back which piece each ring would
            # have to show so the diagram can turn to match, not just the panel.
            pieces = stage.pieces_for(word) if word else None
    elif form.get("find"):
        found = stage.find_word()
        if found is None:
            word = ""
            find_failed = True
        else:
            word, pieces = found
    rings_report = denckring_check("denckring", word, lang="de") if word else None
    known_word = stage.german_pack().is_word(word) if word else False
    return page(
        request,
        "_stage_word.html",
        word=word,
        pieces=pieces,
        rings_report=rings_report,
        known_word=known_word,
        find_failed=find_failed,
        find_attempts=stage.FIND_ATTEMPTS,
        turn_failed=turn_failed,
        turn_attempts=stage.TURN_ATTEMPTS,
    )


@app.post("/stage/denckring/rhyme", response_class=HTMLResponse)
async def stage_denckring_rhyme(request: Request) -> HTMLResponse:
    """Lock the medial, final and suffix rings to one curated ending and sweep
    the initial ring through every letter it offers — the quotation's own
    recipe for finding rhyme-words, run against the rings rather than only
    described by them. See `stage.RHYME_ENDINGS` for why the endings on offer
    are curated rather than the raw lexicon's own `-icken`-style surprises.
    """
    form = dict(await request.form())
    ending = stage.rhyme_ending(str(form.get("ending", "")))
    sweep = stage.rhyme_sweep(ending) if ending else []
    return page(
        request,
        "_stage_rhyme.html",
        ending=ending,
        sweep=sweep,
        hits=[word for word in sweep if word],
    )


@app.get("/stage/ideenwuerfeln", response_class=HTMLResponse)
def stage_ideenwuerfeln(request: Request, chrome: str = "on") -> HTMLResponse:
    choices = stage.corpus_choices()
    return page(
        request,
        "stage_ideenwuerfeln.html",
        scene=stage.scene("ideenwuerfeln"),
        choices=choices,
        # The picker's first option is whatever a reader sees pre-selected, so the
        # toggle's own pre-selected option follows that same corpus's style — the
        # two controls agreeing at first paint, without yet being the same control.
        default_lang=stage.default_lang(choices[0].style) if choices else "en",
        can_read=witz.available(),
        chrome_off=chrome == "off",
    )


@app.post("/stage/ideenwuerfeln/act", response_class=HTMLResponse)
async def stage_ideenwuerfeln_act(request: Request) -> HTMLResponse:
    """Throw the dice: draw slips from the chosen corpus under one headword,
    forced across distinct fields wherever the headword's pool allows it.

    Same-field slips are the smaller half of the procedure — the collision is
    the point, and `distinct_domains` is what makes it real rather than
    merely claimed. The register comes from the corpus that was actually
    loaded, not from a field the form could have carried unchanged — the
    picker offers only corpora `stage.corpus_choices()` knows about, so this
    is the same lookup rather than a second, trustable-or-not copy of the
    same fact.

    What the page says about the draw is read back from the draw, not
    predicted before it. `apply` silently widens a headword pool too thin to
    fill `slots` entries to the *whole corpus* — a pre-flight check of the
    headword's own pool cannot see that widening coming, and would describe a
    throw that never happened. `stage.slips_of` maps each slip back to its
    real entry, so `filed` below is what the throw actually did.

    The language toggle is a second, independent control from the corpus
    picker: it never changes which corpus is read, only the `lang` `apply`
    is called with and, later, the register the Witz reading is asked for.
    """
    form = dict(await request.form())
    path = str(form.get("corpus_path", ""))
    headword = str(form.get("headword", ""))
    chosen = next((c for c in stage.corpus_choices() if c.path == path), None)
    text, problem = corpora.load(path) if path else ("", "no corpus chosen")
    if problem:
        return page(request, "_stage_throw.html", throw="", problem=problem, headword=headword)

    # The toggle overrides the corpus's own suggestion when it carries a value; an
    # empty post (no `lang` field at all — never sent by the picker itself, which
    # always submits one of its two options) falls back to what `chosen.style`
    # suggests, the same rule the page pre-selects the toggle with at first paint.
    lang = str(form.get("lang", "")) or stage.default_lang(chosen.style if chosen else "")

    params: dict[str, Any] = {"distinct_domains": True}
    if headword:
        params["headword"] = headword
    produced, trouble = bench.generate("ideenwuerfeln", text, lang, params)

    slips = stage.slips_of(text, produced, headword) if produced else []
    distinct = len({slip.domain for slip in slips})
    filed = bool(slips) and all(slip.filed for slip in slips)
    note = ""
    if produced and headword:
        if distinct < len(slips):
            # Same signal `apply` itself used to fall back to a plain draw —
            # whichever pool it drew from (the headword's own, or the whole
            # corpus after widening) did not span enough fields.
            note = "fallback"
        elif not filed:
            # Enough distinct fields, but not from the headword's own pool —
            # the widening happened, and the slips are honest about it.
            note = "widened"

    return page(
        request,
        "_stage_throw.html",
        slips=slips,
        throw=produced,
        problem=trouble,
        headword=headword,
        filed=filed,
        note=note,
        style=chosen.style if chosen else witz.DEFAULT_REGISTER,
        register=chosen.register if chosen else "modern",
        lang=lang,
        can_read=witz.available(),
    )


#: The canonical demonstration sentence, one per language the toggle offers.
#: Not a translation of each other — the same shape (a creature, a piece of
#: furniture) so that switching the toggle keeps telling the same kind of
#: joke rather than a different one — and each lands cleanly inside its own
#: shipped noun list (see `stage.displacement`) so the columns always have
#: something to show, on a machine with no corpus configured and nothing
#: else set up. "cat" is the word the reel note tells the catafalque-to-
#: catacomb story about (see `_stage_reels.html`), which is why that note is
#: guarded to only ever fire for this exact English pair — the German source
#: below never produces it.
N_PLUS_7_SOURCES: dict[Lang, str] = {
    "en": "the cat sat on the table",
    "de": "die Katze saß auf dem Tisch",
}


@app.get("/stage/n_plus_7", response_class=HTMLResponse)
def stage_n_plus_7(request: Request, chrome: str = "on") -> HTMLResponse:
    lang = stage.N_PLUS_7_DEFAULT_LANG
    source = N_PLUS_7_SOURCES[lang]
    return page(
        request,
        "stage_n_plus_7.html",
        scene=stage.scene("n_plus_7"),
        source=source,
        steps=stage.displacement(source, 7, lang=lang),
        default_lang=lang,
        examples=N_PLUS_7_SOURCES,
        # The two figures the panel's note quotes, read off the lists
        # themselves rather than typed into the prose. One scene over, the
        # Denckring's legend generates its counts on the reasoning that a
        # hand-typed number "would be the one place on this page a viewer
        # could catch the arithmetic disagreeing with itself"; the same rule
        # applies to a page that names the size of the dictionary it walks.
        noun_counts={lang: len(stage.pack(lang).nouns()) for lang in N_PLUS_7_SOURCES},
        chrome_off=chrome == "off",
    )


@app.post("/stage/n_plus_7/act", response_class=HTMLResponse)
async def stage_n_plus_7_act(request: Request) -> HTMLResponse:
    """Displace the posted source, then check the result against that same source.

    Both halves of the round trip `n_plus_7.apply`/`.check` perform underneath are
    run here exactly as the library runs them — `displace` produces the text, and
    `denckring_check` is asked to confirm it independently — so there is nothing on
    this page for a viewer to take on faith that the library did not already verify.

    `lang` genuinely changes what comes back, unlike Ideenwürfeln's own toggle: it
    picks which noun list `displace` walks, so it is threaded into `stage.pack`
    (by way of `displace`), `stage.displacement` (the reels) and `denckring_check`
    alike, rather than governing only the reading the way the other scene's does.
    """
    form = dict(await request.form())
    source = str(form.get("source", ""))
    lang = bench.as_lang(str(form.get("lang", "")))
    produced = displace(source, stage.pack(lang), 7) if source else ""
    report = denckring_check("n_plus_7", produced, source=source, lang=lang) if source else None
    return page(
        request,
        "_stage_displaced.html",
        source=source,
        produced=produced,
        report=report,
        # `displace` leaves a word alone exactly when the noun list does not know
        # it, so text that comes back identical is text with no noun to displace
        # at all — read back from the result rather than predicted from the
        # source, the same way every other scene here reports what happened.
        unchanged=bool(source) and produced == source,
        # The reels show this source too, and the fragment swaps them back out of
        # band; see `_stage_displaced.html`.
        steps=stage.displacement(source, 7, lang=lang),
    )


@app.get("/stage/cent_mille_milliards", response_class=HTMLResponse)
def stage_cent_mille_milliards(request: Request, chrome: str = "on") -> HTMLResponse:
    state = stage.queneau_initial_state()
    poem = stage.queneau_poem(state)
    report = denckring_check("cent_mille_milliards", poem.text, source=stage.queneau_source())
    return page(
        request,
        "stage_cent_mille_milliards.html",
        scene=stage.scene("cent_mille_milliards"),
        poem=poem,
        state=stage.queneau_state_to_text(state),
        report=report,
        chrome_off=chrome == "off",
    )


@app.post("/stage/cent_mille_milliards/deal", response_class=HTMLResponse)
async def stage_cent_mille_milliards_deal(request: Request) -> HTMLResponse:
    """Redraw every position at once — a fresh poem, not the one-line change a
    flip makes. Checked exactly like a flip's own result, against the same
    source, so a viewer sees a real verdict on whichever poem is on screen
    rather than a claim carried over from before the deal.
    """
    state = stage.queneau_deal()
    poem = stage.queneau_poem(state)
    report = denckring_check("cent_mille_milliards", poem.text, source=stage.queneau_source())
    return page(
        request,
        "_stage_poem.html",
        poem=poem,
        state=stage.queneau_state_to_text(state),
        report=report,
    )


@app.post("/stage/cent_mille_milliards/flip", response_class=HTMLResponse)
async def stage_cent_mille_milliards_flip(request: Request) -> HTMLResponse:
    """Redraw one strip, the other thirteen holding — the scene's whole claim
    that a flip changes only the line it touched.

    The posted `state` is the poem as it stood a moment ago; a form this
    page's own markup never sends without it, but a malformed or stale one
    falls back to first paint's poem rather than guessing at indices that
    might run past a position's own alternatives. `position` is clamped the
    same defensive way, to the first strip, so a request outside what the
    page itself can send still returns something checked rather than a 500.
    """
    form = dict(await request.form())
    current = stage.queneau_state_from_text(str(form.get("state", "")))
    if current is None:
        current = stage.queneau_initial_state()
    offered = stage.queneau_offered()
    try:
        position = int(str(form.get("position", "")))
    except ValueError:
        position = 0
    if not (0 <= position < len(offered)):
        position = 0
    new_state = stage.queneau_flip(current, position)
    poem = stage.queneau_poem(new_state)
    report = denckring_check("cent_mille_milliards", poem.text, source=stage.queneau_source())
    return page(
        request,
        "_stage_flip.html",
        strip=poem.strips[position],
        state=stage.queneau_state_to_text(new_state),
        report=report,
    )


@app.get("/stage/word_ladder", response_class=HTMLResponse)
def stage_word_ladder(request: Request, chrome: str = "on") -> HTMLResponse:
    lang = stage.WORD_LADDER_DEFAULT_LANG
    start, target = stage.WORD_LADDER_EXAMPLES[lang]
    ladder = stage.word_ladder(start, target, lang)
    report = denckring_check("word_ladder", ladder.text, lang=lang) if not ladder.problem else None
    return page(
        request,
        "stage_word_ladder.html",
        scene=stage.scene("word_ladder"),
        ladder=ladder,
        report=report,
        start=start,
        target=target,
        default_lang=lang,
        examples=stage.WORD_LADDER_EXAMPLES,
        chrome_off=chrome == "off",
    )


@app.post("/stage/word_ladder/act", response_class=HTMLResponse)
async def stage_word_ladder_act(request: Request) -> HTMLResponse:
    """Search a ladder from the posted start to the posted target, then check
    the result independently — both halves of `apply`/`check` the library
    itself performs, run here exactly as it runs them, the same round trip
    N+7's own action route shows.

    `stage.word_ladder` already tells the two failure modes apart (an
    endpoint the lexicon does not know, from a search that found no path
    between two it does), so this route only has to read back which one, if
    either, happened — never re-derive it from `apply`'s own exception text.
    """
    form = dict(await request.form())
    start = str(form.get("start", ""))
    target = str(form.get("target", ""))
    lang = bench.as_lang(str(form.get("lang", "")))
    ladder = stage.word_ladder(start, target, lang)
    report = denckring_check("word_ladder", ladder.text, lang=lang) if not ladder.problem else None
    return page(
        request,
        "_stage_ladder.html",
        ladder=ladder,
        report=report,
        start=start,
        target=target,
        lang=lang,
    )


#: English only — the row declares `[en, de]` but the shipped source poem is
#: English (see `stage.HAIKUIZATION_SOURCE`) and a German source has not been
#: written for it, so this scene carries no language toggle at all, unlike
#: N+7's and the word ladder's own.
HAIKUIZATION_LANG: Lang = "en"


@app.get("/stage/haikuization", response_class=HTMLResponse)
def stage_haikuization(request: Request, chrome: str = "on") -> HTMLResponse:
    source = stage.HAIKUIZATION_SOURCE
    haiku = stage.haikuize(source, lang=HAIKUIZATION_LANG)
    report = (
        denckring_check("haikuization", haiku.remnant, lang=HAIKUIZATION_LANG, source=source)
        if haiku.remnant
        else None
    )
    return page(
        request,
        "stage_haikuization.html",
        scene=stage.scene("haikuization"),
        source=source,
        haiku=haiku,
        report=report,
        # First paint shows the poem settled — the dissolve is what the button
        # does, not what the page does to itself before a recorder has pressed
        # anything (the stage's own "scenes do not autoplay"). Only
        # `stage_haikuization_act` below sets this.
        dissolve=False,
        chrome_off=chrome == "off",
    )


@app.post("/stage/haikuization/act", response_class=HTMLResponse)
async def stage_haikuization_act(request: Request) -> HTMLResponse:
    """Reduce the posted source to its own line ends, then check the result
    independently against that same source — the same round trip N+7's and
    the word ladder's own action routes run between `apply` and `check`.

    `stage.haikuize` never calls `apply` on a source with no non-blank line,
    so an empty box comes back with an empty remnant rather than a 500 —
    that is a real state this editable field can reach, not a malformed one.
    """
    form = dict(await request.form())
    source = str(form.get("source", ""))
    haiku = stage.haikuize(source, lang=HAIKUIZATION_LANG)
    report = (
        denckring_check("haikuization", haiku.remnant, lang=HAIKUIZATION_LANG, source=source)
        if haiku.remnant
        else None
    )
    return page(
        request,
        "_stage_haiku.html",
        source=source,
        haiku=haiku,
        report=report,
        # The one rendering that plays: a viewer pressed Reduce, so the lines
        # dissolve and the remnant arrives after them.
        dissolve=True,
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
