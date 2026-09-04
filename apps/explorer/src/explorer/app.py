"""The explorer: a local browser for the catalogue and a bench for the procedures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from denckring import __version__
from denckring import check as denckring_check
from denckring.core import catalogue
from denckring.core.errors import UnknownProcedure
from denckring.core.protocol import Constructive, Lang
from denckring.core.registry import all_procedures, get
from denckring.procedures.n_plus_7 import displace, resolve_dictionary
from explorer import agent, ars, bench, board, catalogue_view, corpora, env, models, stage, witz

env.load()

HERE = Path(__file__).parent

app = FastAPI(title="denckring explorer", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")

# The stage shell asks every scene whether it has a companion reading, so that
# the link can sit beside the caption and disappear with it under `?chrome=off`.
# A global rather than a kwarg on all eight scene routes: the lookup is the same
# on every one of them, and a ninth scene should not be able to be added without
# it. Nothing else is registered here — `page` still hands over everything a
# template renders.
templates.env.globals["reading_for"] = stage.reading_for

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


@app.get("/stage/{slug}/reading", response_class=HTMLResponse)
def stage_reading(request: Request, slug: str) -> HTMLResponse:
    """The companion page behind one scene.

    Keyed by *scene* slug rather than by the reading's own, because that is the
    only address a reader arrives from — the link is on the scene. Two of the
    readings answer to two scenes each, and that is the point of them rather
    than a redirect waiting to be written: Harsdörffer's rings and Gysin's
    blades are one argument, and so are Queneau's strips and Lescure's
    dictionary.

    No `?chrome=off` here, and there should never be one. The recording flag
    exists so a scene can be filmed without its caption; a reading is not
    filmed at all, which is the whole reason it is allowed to be longer than
    720 pixels.
    """
    found = stage.reading_for(slug)
    if found is None:
        return page(request, "reading_missing.html", slug=slug)
    # Every figure these pages state, gathered here rather than reached for
    # inside a template, so that what a reading asserts numerically is visible
    # in one place and computed from the same device files the scene runs on.
    # Handed over per reading rather than through one shared bag: the pages
    # make different arguments and need different numbers, and a context that
    # carried all of them would invite a page to state a figure it had not
    # thought about.
    facts: dict[str, Any] = {}
    if found.slug == "wheel-and-scissors":
        rings = stage.rings()
        facts = {
            "rings": rings,
            "parts": stage.ring_parts(),
            "cut_up_words": len(stage.cut_up_source_words(stage.CUT_UP_SOURCE)),
            "cut_up_lines": len(stage.cut_up_source_lines(stage.CUT_UP_SOURCE)),
        }
    elif found.slug == "oulipo-machines":
        positions, written = stage.queneau_inventory()
        combinations = stage.queneau_combinations()
        facts = {
            "positions": positions,
            "written": written,
            "combinations": combinations,
            "years": stage.years_of_reading(combinations),
            "queneau_years": stage.years_of_reading(10**14),
            "nouns_en": len(stage.pack("en").nouns()),
            "nouns_de": len(stage.pack("de").nouns()),
            "offset": stage.N_PLUS_7_OFFSET,
        }
    elif found.slug == "the-figure":
        figure = stage.llull_figure_data()
        facts = {
            "letters": stage.llull_alphabet(),
            "levels": stage.LLULL_LEVELS,
            "glosses": stage.LLULL_GLOSSES,
            "figure": figure,
            "chambers": stage.llull_chamber_counts(),
            # With no key the whole section is absent rather than disabled, the
            # same way the Witz control is — a form that cannot be submitted is
            # a promise the install cannot keep.
            "ars_available": ars.available(),
        }
    elif found.slug == "the-automat":
        lines, modules, flaps = stage.automat_inventory()
        board = stage.flap_board()
        facts = {
            "lines": lines,
            "modules": modules,
            "flaps": flaps,
            "exponent": stage.power_of_ten(board.combinations),
            "columns": stage.BOARD_COLUMNS,
            "flap_cap": stage.FLAP_CAP,
        }
    return page(
        request,
        f"reading/{found.slug}.html",
        reading=found,
        scenes=[stage.scene(name) for name in found.scenes],
        stylesheets=["/static/reading.css"],
        **facts,
    )


@app.get("/stage/denckring", response_class=HTMLResponse)
def stage_denckring(request: Request, chrome: str = "on") -> HTMLResponse:
    # First paint opens on Harsdörffer's own example (`stage.default_reading`,
    # p. 517: "Aas (cadaver) &c.") rather than whatever each ring's own index 0
    # happens to spell — server-rendered through the same `_stage_word.html`
    # partial "Read it"/"Turn them for me"/"Find me one" answer through, so a
    # no-JS viewer sees exactly what a click would report, and the discs (seeded
    # from `pieces` below) can never open disagreeing with the panel beside them.
    word, pieces = stage.default_reading()
    return page(
        request,
        "stage_denckring.html",
        scene=stage.scene("denckring"),
        rings=stage.rings(),
        rhyme_endings=stage.RHYME_ENDINGS,
        word=word,
        pieces=pieces,
        rings_report=denckring_check("denckring", word, lang="de"),
        known_word=stage.german_pack().is_word(word),
        find_failed=False,
        find_attempts=stage.FIND_ATTEMPTS,
        turn_failed=False,
        turn_attempts=stage.TURN_ATTEMPTS,
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
    pieces: list[int] | None = None
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

            # The library chose this word; hand back which position each ring
            # would have to show so the diagram can turn to match, not just the
            # panel — a true index, never text the client would have to search
            # a ring's own parts list for (see `stage.pieces_for`).
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
        # The panel now shows the five parts the word came off, and it reads
        # them out of the same slots the discs are drawn from rather than
        # re-deriving them — one source for what is on the rings and what is
        # printed beside them.
        rings=stage.rings(),
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
    sweep = stage.rhyme_sweep(ending) if ending else None
    return page(
        request,
        "_stage_rhyme.html",
        sweep=sweep,
        hits=[word for word in sweep.words if word] if sweep else [],
    )


def _headwords_for(path: str) -> list[str]:
    """The headwords a corpus files entries under, read fresh from disk.

    Not memoised against `path`: the brief's own warning is that this scene has
    a history of claims that outlived the state they described, and a cached
    list would be exactly that the moment a corpus file changed underneath it.
    An empty or unreadable path answers with no headwords rather than raising —
    the picker offers only paths `stage.corpus_choices` already vouches for, but
    the htmx round-trip below takes `corpus_path` off a request like any other
    form field, so it is checked here rather than trusted.
    """
    if not path:
        return []
    text, problem = corpora.load(path)
    return [] if problem else corpora.headwords_of(text)


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
        default_lang=choices[0].lang if choices else "en",
        # Same rule for the headword picker: first paint shows the first
        # corpus's own headwords, matching what the select above it already
        # pre-selects, until a reader picks a different one.
        headwords=_headwords_for(choices[0].path) if choices else [],
        can_read=witz.available(),
        chrome_off=chrome == "off",
    )


@app.get("/stage/ideenwuerfeln/headword-field", response_class=HTMLResponse)
def stage_ideenwuerfeln_headword_field(request: Request, corpus_path: str = "") -> HTMLResponse:
    """Refill the headword picker for whichever corpus the select now names.

    Its own route rather than folded into the throw itself: switching corpus
    must reload the offered headwords without throwing anything, and the two
    are different requests the picker fires at different moments — this one on
    `change`, `/act` only once "Throw" is pressed.
    """
    return page(request, "_stage_headword_field.html", headwords=_headwords_for(corpus_path))


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
#: else set up. The reel note that used to hang off this exact English pair —
#: the catafalque-to-catacomb story — was cut in round three's cross-scene
#: pass: it was prose about a journey the columns already run.
#: What the scene offers to displace. Real passages, in both languages, all
#: public domain — the rule's whole point is how much of a sentence survives it,
#: and that is invisible on a five-word test sentence. "the cat sat on the
#: table" is still here as the first English one, because *cat → catacomb* is
#: the example this scene is known by and the one the design spec asks it to
#: show; everything else is prose long enough to watch the grammar hold while
#: the subject matter goes.
N_PLUS_7_SOURCES: dict[Lang, list[tuple[str, str]]] = {
    "en": [
        ("the cat sat on the table", "the example, and cat → catacomb"),
        (
            "In the beginning God created the heaven and the earth. And the earth was "
            "without form, and void; and darkness was upon the face of the deep.",
            "Genesis 1, King James Bible, 1611",
        ),
        (
            "Call me Ishmael. Some years ago, never mind how long precisely, having "
            "little or no money in my purse, and nothing particular to interest me on "
            "shore, I thought I would sail about a little and see the watery part of "
            "the world.",
            "Melville, Moby-Dick, 1851",
        ),
        (
            "It is interesting to contemplate an entangled bank, clothed with many "
            "plants of many kinds, with birds singing on the bushes, with various "
            "insects flitting about, and with worms crawling through the damp earth.",
            "Darwin, On the Origin of Species, 1859",
        ),
    ],
    "de": [
        ("die Katze saß auf dem Tisch", "das Beispiel"),
        (
            "Als Gregor Samsa eines Morgens aus unruhigen Träumen erwachte, fand er "
            "sich in seinem Bett zu einem ungeheueren Ungeziefer verwandelt.",
            "Kafka, Die Verwandlung, 1915",
        ),
        (
            "Wer reitet so spät durch Nacht und Wind? Es ist der Vater mit seinem "
            "Kind. Er hat den Knaben wohl in dem Arm, er faßt ihn sicher, er hält ihn "
            "warm.",
            "Goethe, Erlkönig, 1782",
        ),
        (
            "Es war einmal mitten im Winter, und die Schneeflocken fielen wie Federn "
            "vom Himmel herab, da saß eine Königin an einem Fenster, das einen Rahmen "
            "von schwarzem Ebenholz hatte, und nähte.",
            "Grimm, Schneewittchen, 1812",
        ),
    ],
}


@app.get("/stage/n_plus_7", response_class=HTMLResponse)
def stage_n_plus_7(request: Request, chrome: str = "on") -> HTMLResponse:
    lang = stage.N_PLUS_7_DEFAULT_LANG
    source = N_PLUS_7_SOURCES[lang][0][0]
    steps = stage.displacement(source, stage.N_PLUS_7_OFFSET, lang=lang)
    looked_up = steps[0].word if steps else ""
    return page(
        request,
        "stage_n_plus_7.html",
        scene=stage.scene("n_plus_7"),
        source=source,
        steps=steps,
        looked_up=looked_up,
        entries=stage.dictionary_page(looked_up, stage.N_PLUS_7_OFFSET, lang),
        default_lang=lang,
        offset=stage.N_PLUS_7_OFFSET,
        reach=stage.N_PLUS_7_REACH,
        examples=N_PLUS_7_SOURCES,
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
    offset = stage.n_plus_7_offset(str(form.get("offset", "")))
    chosen = stage.pack(lang)
    # The pair comes from `resolve_dictionary` rather than being read off the
    # pack here, because that is the seam ADR 0029 put it behind: `nouns` and
    # `noun_index` are resolved together precisely so two call sites cannot come
    # to disagree about which list was walked. This scene has no dictionary of
    # its own to pass, so it asks for the pack's the same way `apply` does.
    if source:
        nouns, noun_index = resolve_dictionary(chosen, None)
        produced = displace(source, chosen, nouns, noun_index, offset)
    else:
        produced = ""
    # The offset travels into `check` too, not only into `displace`. The
    # checker's own `offset` parameter is what decides which replacement it
    # expects, so a scene that displaced by one and checked against seven
    # would put a red verdict under a perfectly good N+1.
    report = (
        denckring_check("n_plus_7", produced, source=source, lang=lang, offset=offset)
        if source
        else None
    )
    steps = stage.displacement(source, offset, lang=lang)
    # Which noun the page is open at. The first the list knows, unless the
    # viewer asked for another — the scene lists them all and lets you choose,
    # because the whole argument is that the list decides the result and a page
    # open at one arbitrary word does not show that.
    wanted = str(form.get("word", ""))
    looked_up = (
        wanted if any(step.word == wanted for step in steps) else (steps[0].word if steps else "")
    )
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
        # band; see `_stage_displaced.html`. Built at the same offset the text
        # was displaced by — a reel that walked seven while the result moved
        # The open page is part of what this action changed, so it is swapped
        # out of band from the source that was actually posted — every other
        # scene on this stage re-renders everything its action touched, and a
        # page still open at "cat" beside a panel displacing something else
        # would be this scene's own version of describing what it did not do.
        # Opened at the same offset the text was displaced by: a page showing a
        # seven-entry journey beside a result that moved three would be a
        # picture of a substitution that did not happen.
        steps=steps,
        looked_up=looked_up,
        entries=stage.dictionary_page(looked_up, offset, lang),
        offset=offset,
        reach=stage.N_PLUS_7_REACH,
        default_lang=lang,
    )


@app.get("/stage/cent_mille_milliards", response_class=HTMLResponse)
def stage_cent_mille_milliards(
    request: Request, lang: str = "en", chrome: str = "on"
) -> HTMLResponse:
    lang_ = stage.queneau_lang(lang)
    state = stage.queneau_initial_state(lang_)
    poem = stage.queneau_poem(state, lang_)
    report = denckring_check(
        "cent_mille_milliards", poem.text, lang=lang_, source=stage.queneau_source(lang_)
    )
    return page(
        request,
        "stage_cent_mille_milliards.html",
        scene=stage.scene("cent_mille_milliards"),
        poem=poem,
        state=stage.queneau_state_to_text(state),
        lang=lang_,
        report=report,
        ordinal=stage.queneau_ordinal(state, lang_),
        address=stage.queneau_address(state),
        combinations=stage.queneau_combinations(lang_),
        chrome_off=chrome == "off",
    )


@app.get("/stage/cent_mille_milliards/set", response_class=HTMLResponse)
def stage_cent_mille_milliards_set(request: Request, lang: str = "en") -> HTMLResponse:
    """Switch strip sets: the picker's own `change` fires this, and first
    paint of whichever set it now names comes back — the same reset
    `queneau_initial_state` gives the scene's own first load, so the poem,
    the count and the verdict all follow the chosen set together rather than
    carrying over indices that might run past its own positions.
    """
    lang_ = stage.queneau_lang(lang)
    state = stage.queneau_initial_state(lang_)
    poem = stage.queneau_poem(state, lang_)
    report = denckring_check(
        "cent_mille_milliards", poem.text, lang=lang_, source=stage.queneau_source(lang_)
    )
    return page(
        request,
        "_stage_queneau_scene.html",
        poem=poem,
        state=stage.queneau_state_to_text(state),
        lang=lang_,
        report=report,
        ordinal=stage.queneau_ordinal(state, lang_),
        address=stage.queneau_address(state),
        combinations=stage.queneau_combinations(lang_),
    )


@app.post("/stage/cent_mille_milliards/deal", response_class=HTMLResponse)
async def stage_cent_mille_milliards_deal(request: Request) -> HTMLResponse:
    """Redraw every position at once — a fresh poem, not the one-line change a
    flip makes. Checked exactly like a flip's own result, against the same
    source, so a viewer sees a real verdict on whichever poem is on screen
    rather than a claim carried over from before the deal. `lang` comes off
    the deal form's own hidden field, the picker's current value carried
    along with it, so a deal always redraws the set actually on screen.
    """
    form = dict(await request.form())
    lang_ = stage.queneau_lang(str(form.get("lang", "")))
    state = stage.queneau_deal(lang_)
    poem = stage.queneau_poem(state, lang_)
    report = denckring_check(
        "cent_mille_milliards", poem.text, lang=lang_, source=stage.queneau_source(lang_)
    )
    return page(
        request,
        "_stage_deal.html",
        poem=poem,
        state=stage.queneau_state_to_text(state),
        lang=lang_,
        report=report,
        ordinal=stage.queneau_ordinal(state, lang_),
        address=stage.queneau_address(state),
        combinations=stage.queneau_combinations(lang_),
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
    `lang` comes off the same shared field `state` does (`#poem-lang`,
    `_stage_poem.html`) and picks which set both the redraw and the fallback
    read from, so a flip on the German strips can never land on the English
    sheet underneath them.
    """
    form = dict(await request.form())
    lang_ = stage.queneau_lang(str(form.get("lang", "")))
    current = stage.queneau_state_from_text(str(form.get("state", "")), lang_)
    if current is None:
        current = stage.queneau_initial_state(lang_)
    offered = stage.queneau_offered(lang_)
    try:
        position = int(str(form.get("position", "")))
    except ValueError:
        position = 0
    if not (0 <= position < len(offered)):
        position = 0
    new_state = stage.queneau_flip(current, position, lang_)
    poem = stage.queneau_poem(new_state, lang_)
    report = denckring_check(
        "cent_mille_milliards", poem.text, lang=lang_, source=stage.queneau_source(lang_)
    )
    return page(
        request,
        "_stage_flip.html",
        strip=poem.strips[position],
        state=stage.queneau_state_to_text(new_state),
        report=report,
        # The address changes with every flip, so it travels back out of band
        # beside the state field and the verdict. One digit moves; leaving the
        # old one on screen would be this scene describing the poem before the
        # flip while showing the poem after it.
        ordinal=stage.queneau_ordinal(new_state, lang_),
        address=stage.queneau_address(new_state),
        combinations=stage.queneau_combinations(lang_),
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


#: English only — the row declares `[en]` (see `catalogue.yaml`), so unlike
#: N+7's and the word ladder's own, this scene carries no language toggle at
#: all. Widening it is not this task's to do (see the brief's own ruling).
CUT_UP_LANG: Lang = "en"


@app.get("/stage/calculator_word", response_class=HTMLResponse)
def stage_calculator_word(request: Request, chrome: str = "on") -> HTMLResponse:
    lang = stage.CALCULATOR_WORD_DEFAULT_LANG
    digits = stage.CALCULATOR_WORD_EXAMPLES[lang]
    reading = stage.calculator_word(digits, lang)
    report = (
        denckring_check("calculator_word", reading.word, lang=lang, digits=digits)
        if not reading.problem
        else None
    )
    return page(
        request,
        "stage_calculator_word.html",
        scene=stage.scene("calculator_word"),
        segments=stage.SEGMENTS,
        reading=reading,
        report=report,
        digits=digits,
        default_lang=lang,
        examples=stage.CALCULATOR_WORD_EXAMPLES,
        chrome_off=chrome == "off",
    )


@app.post("/stage/calculator_word/act", response_class=HTMLResponse)
async def stage_calculator_word_act(request: Request) -> HTMLResponse:
    """Decode the posted digits, then check the reading independently — both
    halves of the round trip, run here exactly as the library runs them, the
    same shape the word ladder's own action route uses.

    `stage.calculator_word` already tells the two failure modes apart, so this
    route only reads back which one happened rather than re-deriving it from an
    exception message.
    """
    form = dict(await request.form())
    digits = str(form.get("digits", ""))
    lang = bench.as_lang(str(form.get("lang", "")))
    reading = stage.calculator_word(digits, lang)
    report = (
        denckring_check("calculator_word", reading.word, lang=lang, digits=reading.digits)
        if not reading.problem
        else None
    )
    return page(
        request,
        "_stage_display.html",
        segments=stage.SEGMENTS,
        reading=reading,
        report=report,
        digits=digits,
        lang=lang,
    )


@app.get("/stage/cut_up", response_class=HTMLResponse)
def stage_cut_up(request: Request, chrome: str = "on") -> HTMLResponse:
    """First paint: the page, uncut, and nothing else — no cut has run yet,
    so there is no result and no verdict to show (the same choice N+7's own
    `#displaced` opens empty on, for the same reason: "scenes do not
    autoplay. The recording is a person using the thing")."""
    source = stage.CUT_UP_SOURCE
    return page(
        request,
        "stage_cut_up.html",
        scene=stage.scene("cut_up"),
        source_lines=stage.cut_up_source_lines(source, lang=CUT_UP_LANG),
        # The second page is on the table from first paint rather than
        # appearing when the fold-in is picked. A page cannot be folded onto
        # something that is not there yet, and a viewer who has not pressed
        # "Fold-in" should still be able to see what the fold would be against.
        page_b_lines=stage.cut_up_source_lines(stage.CUT_UP_SOURCE_B, lang=CUT_UP_LANG),
        methods=stage.CUT_METHODS,
        method=stage.CUT_METHODS[0],
        max_column=stage.cut_up_max_column(),
        chrome_off=chrome == "off",
    )


@app.post("/stage/cut_up/act", response_class=HTMLResponse)
async def stage_cut_up_act(request: Request) -> HTMLResponse:
    """Check the arrangement the page is showing, against the shipped source.

    The text arrives from the client because it *has* to: the cut is made in
    the browser, by two blades a viewer positions by hand, and the four
    quarters that result are what the page displays. `stage_cut_up.html`
    reads that text back out of the quarters themselves and posts it here, so
    what `check` is given is what is on screen, character for character. A
    route that recomputed the arrangement from `CUT_UP_SOURCE` would be
    checking a second, invisible cut-up that merely resembled the one the
    viewer made.

    Deliberately **not** `cut_up.apply`. `apply` shuffles the source's
    individual words, which is a different method from the one this scene
    depicts — Gysin's quadrant cut moves words in blocks, and only ever the
    blocks two straight cuts produce. `check` is what this scene
    demonstrates, and it accepts a quadrant rearrangement: a clean cut of
    this source is 47 words against 47 source words with no violations, and
    a cut through a word is caught by name (both measured — see the task
    report). Please do not "fix" this back to `apply`.
    """
    form = await request.form()
    text = str(form.get("text", ""))
    method = stage.cut_method(str(form.get("method", "")))
    if method.procedure is None:
        # The word bag, and the only place on the stage where the honest
        # answer is that there is no answer. `dada_poem` is catalogued
        # `checkability: none`: every order a bag can produce is a correct
        # draw, so there is no property a report could hold this text
        # against. Checking it against `cut_up` instead — the same words,
        # rearranged, which it *would* pass — would be a verdict about a
        # method the viewer did not perform.
        return page(request, "_stage_cutup.html", report=None, method=method, text=text)
    if method.id == "fold":
        report = denckring_check(
            method.procedure, text, lang=CUT_UP_LANG, source=stage.fold_in_source()
        )
    elif method.id == "column":
        report = denckring_check(
            method.procedure,
            text,
            lang=CUT_UP_LANG,
            source=stage.CUT_UP_SOURCE,
            column=stage.cut_up_column(str(form.get("column", ""))),
        )
    else:
        report = denckring_check(
            method.procedure, text, lang=CUT_UP_LANG, source=stage.CUT_UP_SOURCE
        )
    return page(request, "_stage_cutup.html", report=report, method=method, text=text)


@app.get("/stage/llull_figure", response_class=HTMLResponse)
def stage_llull_figure(request: Request, chrome: str = "on") -> HTMLResponse:
    """First paint: the alphabet's own first chamber at arity 3 — B, C, D —
    deterministic the way every other scene's own first paint is (see
    `stage.llull_default_letters`)."""
    arity = 3
    letters = stage.llull_default_letters(arity)
    chamber = stage.llull_chamber(letters, arity)
    report = denckring_check(
        "llull_figure", chamber.text, lang="en", figure=stage.LLULL_FIGURE_ID, arity=arity
    )
    return page(
        request,
        "stage_llull_figure.html",
        scene=stage.scene("llull_figure"),
        alphabet=stage.llull_alphabet(),
        chamber=chamber,
        report=report,
        positions=stage.llull_positions(chamber.letters),
        llull_data_json=json.dumps(stage.llull_client_data()),
        chrome_off=chrome == "off",
    )


@app.post("/stage/llull_figure/act", response_class=HTMLResponse)
async def stage_llull_figure_act(request: Request) -> HTMLResponse:
    """Read the wheels exactly as they now stand, turn them to a fresh random
    chamber, or switch how many principles a chamber holds — one form, three
    named buttons, the same shape `stage_denckring_act` already answers for
    "Read it"/"Turn them for me"/"Find me one".

    A hold-to-turn release on the client (see the scene's own script)
    submits this same form programmatically once the last held wheel stops,
    so the "read" branch below is reached exactly as often by a hand-turned
    chamber as by a plain click of "Read it" — the panel a viewer watches
    during a hold is a client-side preview (`stage.llull_client_data`); this
    route is what turns it into a real, checked verdict.
    """
    form = dict(await request.form())
    positions: list[int] | None = None

    if form.get("set_arity"):
        arity = stage.llull_arity(str(form["set_arity"]))
        letters = stage.llull_default_letters(arity)
        positions = stage.llull_positions(letters)
    else:
        arity = stage.llull_arity(str(form.get("arity", "3")))
        if form.get("turn"):
            letters = stage.llull_random_letters(arity)
            positions = stage.llull_positions(letters)
        else:
            parsed = stage.llull_letters_from_text(str(form.get("chamber", "")))
            if parsed is not None and len(parsed) == arity:
                letters = parsed
            else:
                # A stale or malformed hidden field — never one this page's
                # own script sends — falls back to the arity's own default
                # chamber, and the discs are told to sync back to it rather
                # than left showing whatever they actually had.
                letters = stage.llull_default_letters(arity)
                positions = stage.llull_positions(letters)

    chamber = stage.llull_chamber(letters, arity)
    report = denckring_check(
        "llull_figure", chamber.text, lang="en", figure=stage.LLULL_FIGURE_ID, arity=arity
    )
    return page(
        request,
        "_stage_llull_reading.html",
        chamber=chamber,
        report=report,
        positions=positions,
    )


@app.get("/stage/poesie_automat", response_class=HTMLResponse)
def stage_poesie_automat(
    request: Request, chrome: str = "on", device: str | None = None
) -> HTMLResponse:
    """First paint: a board at rest, every module on its own first flap, and a
    real `check()` verdict for the poem those flaps spell.

    Deterministic, the way every other scene's first paint is — the press of
    the button is the thing a viewer does on camera, not something the page
    has already done for them.

    `device` names which cartridge the board opens on. It exists so a
    reproduction or a screenshot can open straight onto either one; the
    switcher itself does not use it, because both cartridges go over in the
    page and the swap is local. `stage.automat_cartridge` refuses an id this
    scene does not carry rather than handing it to `device.load`.
    """
    cartridge = stage.automat_cartridge(device)
    positions = stage.automat_default_positions(cartridge.device_id)
    board = stage.flap_board(cartridge.device_id)
    report = denckring_check(
        "poesie_automat",
        stage.automat_poem(positions, cartridge.device_id),
        lang=stage.POESIE_AUTOMAT_LANG,
        device=cartridge.device_id,
    )
    return page(
        request,
        "stage_poesie_automat.html",
        scene=stage.scene("poesie_automat"),
        board=board,
        rows=stage.automat_rows(board, positions),
        columns=stage.BOARD_COLUMNS,
        positions=positions,
        cartridges=[stage.automat_payload(c) for c in stage.AUTOMAT_CARTRIDGES],
        device=cartridge.device_id,
        note=cartridge.note,
        kicker=cartridge.kicker,
        credit=cartridge.credit,
        report=report,
        text=None,
        exponent=stage.power_of_ten(board.combinations),
        chrome_off=chrome == "off",
    )


@app.post("/stage/poesie_automat/act", response_class=HTMLResponse)
async def stage_poesie_automat_act(request: Request) -> HTMLResponse:
    """Two branches, one form, the shape `stage_llull_figure_act` already has.

    **Press the button.** `apply` composes a poem — the library's own choice,
    under its own seed — and the reply carries nothing but the 36 flap indices
    that spell it and the placeholder. No verdict: the cells have not turned
    yet, and a verdict printed here would stand over a board still showing the
    previous poem for the whole length of the clatter.

    **Read the board.** The text arrives from the client because it has to:
    the cells are turned in the browser, by a clatter and by hand, and what
    `check` is given must be what is on the board. `stage_poesie_automat.html`
    reads it character by character out of the cells themselves and posts it
    here (see `readBoard`). A route that recomputed the poem from the seed
    would be checking a second, invisible board that merely resembled the one
    on screen — and would have nothing at all to say about a module a viewer
    turned by hand afterwards.

    Both branches take the **cartridge the board is currently showing** from
    the form. A verdict is only honest about the device it was checked
    against, and a swap is one more way for the board to stop being what a
    standing verdict was about; the client's own token machinery covers the
    staleness, and this covers the *device*. An id the scene does not carry is
    refused by `stage.automat_cartridge` rather than reaching `device.load`.
    """
    form = dict(await request.form())
    cartridge = stage.automat_cartridge(str(form.get("device", "")))
    if form.get("press"):
        _, positions = stage.automat_press(cartridge.device_id)
        return page(request, "_stage_flaps.html", report=None, positions=positions, text=None)
    text = str(form.get("poem", ""))
    report = denckring_check(
        "poesie_automat",
        text,
        lang=stage.POESIE_AUTOMAT_LANG,
        device=cartridge.device_id,
    )
    return page(request, "_stage_flaps.html", report=report, positions=None, text=text)


@app.get("/agent", response_class=HTMLResponse)
def over_mcp(request: Request) -> HTMLResponse:
    """A local model, denckring's own MCP server, and the calls in between.

    The first consumer this repository has for that server: everything else
    here calls the library in-process.
    """
    installed, problem = models.available()
    return page(
        request,
        "agent.html",
        page_id="agent",
        installed=installed,
        problem=problem,
        presets=agent.PRESETS,
        default_model=next((m.name for m in installed if m.tools), ""),
        transcript=None,
    )


@app.post("/agent/ask", response_class=HTMLResponse)
async def over_mcp_ask(request: Request) -> HTMLResponse:
    form = dict(await request.form())
    transcript = await agent.run(str(form.get("question", "")), str(form.get("model", "")))
    return page(request, "_agent_transcript.html", transcript=transcript)


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
        apply_fields=bench.apply_fields_for(procedure_id) if implemented else [],
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
    # The checker's fields plus the ones only `apply` takes. Coercing against
    # the checker's alone is what dropped `seed` on the floor: `coerce` walks
    # the fields it is given, so a parameter absent from that list is absent
    # from the request no matter what the form posted.
    fields = bench.fields_for(procedure_id) + bench.apply_fields_for(procedure_id)
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
        apply_fields=bench.apply_fields_for(procedure_id),
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


@app.post("/p/llull_figure/ars", response_class=HTMLResponse)
async def read_the_chamber(request: Request) -> HTMLResponse:
    """One question put to the fourth figure. Not a verdict — see explorer.ars.

    In the bench's namespace, beside `/p/{procedure_id}/witz`, and rendered onto
    the *reading* page rather than onto scene seven. That is a measurement
    rather than a preference: the scene's content already reaches 677 of its 720
    pixels and `.stage` is `overflow: hidden`, so a form and a five-row table
    added to it would be clipped without saying so. It also settles the honesty
    risk the design spec names — a model's reading cannot appear in a capture
    beside a real verdict if it cannot appear in a capture at all.

    The chamber that comes back is validated against the figure's own letters
    before anything is rendered from it, and the six readings beside it are
    `stage.llull_readings`, the same call the scene's own panel makes. So the
    terms the arguments are built from are the figure's, read off the figure.
    """
    form = dict(await request.form())
    session = ars.interrogate(
        str(form.get("question", "")),
        alphabet=stage.llull_prompt_alphabet(),
        letters=stage.llull_alphabet(),
    )
    return page(
        request,
        "_stage_ars.html",
        session=session,
        problem=session.problem,
        readings=stage.llull_readings(list(session.chamber)) if session.chamber else [],
    )


@app.post("/p/{procedure_id}/witz/stream")
async def read_witz_streamed(request: Request) -> StreamingResponse:
    """The same reading as `/witz`, in the pieces it arrives in.

    Plain text, not HTML and not htmx: the scene's own script reads the body as
    it comes and puts each piece on the page. The paragraph takes the better
    part of half a minute, and the panel used to show nothing at all for the
    whole of it, which reads as a broken bench rather than a slow one.

    `/witz` stays exactly as it was. It is what a viewer with no JavaScript
    gets, and it is what the disclaimer test drives — a second path is only
    honest if the first still works.
    """
    form = dict(await request.form())
    return StreamingResponse(
        witz.stream(
            str(form.get("throw", "")),
            headword=str(form.get("headword", "")),
            lang=str(form.get("lang", "en")),
            register=str(form.get("style", witz.DEFAULT_REGISTER)),
        ),
        media_type="text/plain; charset=utf-8",
        # Nginx and friends buffer a streamed response into one lump by
        # default, which would restore the wait this route exists to remove.
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"},
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
        apply_fields=bench.apply_fields_for(procedure_id),
        languages=bench.languages_for(procedure_id),
        can_apply=bench.can_apply(procedure_id),
        example=example,
    )
