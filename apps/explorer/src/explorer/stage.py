"""The stage: what each scene is, and the data it needs.

Preparation only. Nothing here renders, and nothing here touches HTTP — a scene's
route reads from this module and hands the result to a template, so the thing a
scene claims can be tested without a browser.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

from denckring.core import device
from denckring.core.errors import InvalidParams, NoCandidateWord
from denckring.core.protocol import Constructive, Lang, LanguagePack
from denckring.core.registry import get
from denckring.core.text import line_spans, word_spans
from denckring.lang import get_pack
from denckring.procedures.cent_mille_milliards import alternatives as queneau_alternatives
from explorer import corpora

#: N+7's own default, mirroring `default_lang`'s shape — but with no corpus to
#: read a suggestion from, the toggle simply starts on English every time
#: (the brief's own instruction), so this is a bare constant rather than a
#: style-keyed lookup.
N_PLUS_7_DEFAULT_LANG: Lang = "en"


@dataclass(frozen=True)
class Scene:
    """One recordable scene."""

    slug: str
    title: str
    procedure_id: str
    #: One line, shown under the stage and hidden by `?chrome=off`.
    caption: str


SCENES: list[Scene] = [
    Scene(
        slug="denckring",
        title="Der Denckring",
        procedure_id="denckring",
        caption="Harsdörffer, Nürnberg 1651. Turn the rings; read inward to outward.",
    ),
    Scene(
        slug="ideenwuerfeln",
        title="Ideenwürfeln",
        procedure_id="ideenwuerfeln",
        caption="Jean Paul's excerpt books: distant material forced together under one word.",
    ),
    Scene(
        slug="n_plus_7",
        title="N+7",
        procedure_id="n_plus_7",
        caption="Lescure, 1961. Every noun, seven entries further down the dictionary.",
    ),
    Scene(
        slug="cent_mille_milliards",
        title="Cent mille milliards de poèmes",
        procedure_id="cent_mille_milliards",
        caption="Queneau, 1961. Flip a strip; the sonnet survives every combination.",
    ),
    Scene(
        slug="word_ladder",
        title="Word ladder",
        procedure_id="word_ladder",
        caption="Carroll's Doublets. Change one letter, land on a word, until you arrive.",
    ),
    Scene(
        slug="cut_up",
        title="Cut-up",
        procedure_id="cut_up",
        caption="Gysin and Burroughs, 1960. Cut the page; every word must still be the page's own.",
    ),
]


def scene(slug: str) -> Scene:
    """One scene by slug, or `KeyError`."""
    for candidate in SCENES:
        if candidate.slug == slug:
            return candidate
    raise KeyError(slug)


#: The figure the literature repeats for the Denckring. It is not a product of rings of
#: 12 and 120 at all — the catalogue row carries the arithmetic. The scene puts it next
#: to the real number rather than arguing in prose.
CLAIMED_COMBINATIONS = 97_209_600


@dataclass(frozen=True)
class RingSlot:
    """One disc, with everything written on it."""

    name: str
    alternatives: list[str]
    optional: bool


@dataclass(frozen=True)
class Rings:
    """The five discs, and the two counts."""

    slots: list[RingSlot]
    combinations: int
    claimed: int


def rings() -> Rings:
    """Harsdörffer's device as the shipped transcription has it."""
    loaded = device.load("harsdoerffer_1651")
    return Rings(
        slots=[
            RingSlot(name=slot.name, alternatives=list(slot.alternatives), optional=slot.optional)
            for slot in loaded.slots
        ],
        combinations=loaded.combinations,
        claimed=CLAIMED_COMBINATIONS,
    )


def pieces_for(word: str) -> list[int] | None:
    """The five ring *positions* that spell `word`, one true index per slot, or
    `None` if the rings cannot spell it at all.

    Built on the same segmentation `check` itself relies on —
    `denckring.core.device.segment` — but handed back as the index each piece
    sits at on its slot, not the piece's text. Text is not enough to turn a
    ring by: `endbuchstabe`'s 120 parts repeat two of them ('f' and 'ls',
    each twice), so a ring found by searching its parts list for matching
    text (`parts.indexOf(piece)`, the defect this shape replaces) can only
    ever resolve to the first occurrence — sound as far as it goes, but a
    computation the client no longer needs to perform, or risk performing
    differently, once the index is simply the number the server already
    worked out. A skipped optional ring (prefix or suffix) comes back as the
    index one past its last real alternative — the same blank position
    `_label`/the client's own `label()` already treat as blank.
    """
    device_obj = device.load("harsdoerffer_1651")
    text_pieces = device.segment(word, device_obj)
    if text_pieces is None:
        return None
    return [
        len(slot.alternatives) if piece == "" else slot.alternatives.index(piece)
        for slot, piece in zip(device_obj.slots, text_pieces, strict=True)
    ]


#: Harsdörffer's own example, p. 517: turning the rings gives "blinde oder
#: deutunglose Wörter" — blind or meaningless words — until one is not, "Aas
#: (cadaver) &c." His example, not a machine-chosen one, and still both
#: producible and a word German knows, so the scene opens on it rather than
#: on whatever index 0 of every ring happens to spell.
DEFAULT_WORD = "Aas"


def default_reading() -> tuple[str, list[int]]:
    """The word and ring positions the scene opens on — see `DEFAULT_WORD`."""
    positions = pieces_for(DEFAULT_WORD)
    if positions is None:  # pragma: no cover — DEFAULT_WORD is producible by construction
        raise AssertionError(f"{DEFAULT_WORD!r} must be producible by the rings")
    return DEFAULT_WORD, positions


def german_pack() -> LanguagePack:
    """The German pack, with the lexicon `is_word` and rhyme mode both need."""
    return get_pack("de")


#: Stems, not whole words: one entry also catches every inflected form the
#: rings can assemble around it ("fick" -> Ficken, fickst, gefickt, ...)
#: without enumerating each by hand. Matched against a casefolded word —
#: Python's own `casefold` already turns "ß" into "ss", so "Scheiße" and
#: "scheisse" match the same stem without this list carrying both spellings.
#:
#: This is the actual safety mechanism for the words the *Denckring* scene
#: puts on screen by machine, not `RHYME_ENDINGS`'s curation: a hand-read pass
#: over the -acken sweep missed "Kacken", and `find_word` went through no
#: curation at all — a raw 184,040-word lexicon answers "is this a word", not
#: "is this fit to show on a recording". See `fit_for_stage` below, and the
#: note above it for the two scenes it deliberately does not cover.
#:
#: Covers, deliberately: sexual vulgarities (fick, fotz/votz, muschi, wichs,
#: bums, hure, nutte, titt, möse, pimmel); scatological ones (scheiss/schiss
#: — both stems needed, since "beschissen" carries the strong verb's past
#: stem "schiss" rather than "scheiss"; kack; piss; kotz; strull); and slurs
#: (neger, zigeuner, kanak, spast, untermensch).
#:
#: "untermensch" and "strull" are the round-two additions, and both cost
#: nothing at all: the whole shipped lexicon holds two forms containing
#: "untermensch" (the slur and its plural, both producible) and thirteen
#: containing "strull" (every one of them the vulgar verb, three producible).
#: They are stems rather than `_BLOCKED_EXACT` entries because they take no
#: ordinary word down with them — which is the only reason that list exists.
#:
#: Deliberately excludes some stems that looked relevant and were checked
#: against the shipped lexicon and rejected as too broad for this device:
#: "schei" alone catches "bescheiden" (modest), "entscheiden" (decide),
#: "erscheinen" (appear) and 100+ other ordinary words, all sharing the
#: syllable but none the vulgarity; "arsch" catches "Marsch", "Barsch" and
#: "harsch" (marching, perch, harsh) and nothing this device can actually
#: spell that means what "Arsch" means, since no ring offers a bare "r" as
#: a medial letter; "muff" catches "Muffin"; "sack" catches the ordinary
#: word "Sack" (bag) and its "sacken" (sink/drop) family; "hoden" and
#: "sperma" are the clinical terms, not the crude register the brief asked
#: this list to cover; "dirne" is the archaic literary word for a prostitute
#: rather than a current insult (the crude register is already covered by
#: "hure" and "nutte"), and on a 1651 device it reads as period vocabulary;
#: "rotz" catches "Trotz", "Protz", "strotzen" and 24 other producible
#: ordinary words, and blocking only "anrotzen" as an exact form would leave
#: "Rotz", "rotzen", "rotzig" and "hinrotzen" reachable, which is a gesture
#: rather than a safety property. "hure" is kept despite also catching "nachschüren"/
#: "vollschüren" (to stoke a fire further) — a false positive judged worth
#: the true ones alongside it, on the reasoning that a lost word is a minor
#: cost and a missed vulgarity is not. Audited in full in the task report.
#:
#: Ruling made after that audit (see the task report's "Ruling 1"): "spast"
#: is blocked as a stem even though it also costs "spastisch" (a genuine
#: clinical adjective, and likewise producible) — in German "Spast" itself
#: is an ableist slur with no innocent reading, so the trade favours
#: blocking the stem: a missing adjective in a demo costs nothing, a slur
#: in a recording costs a great deal.
_BLOCKED_STEMS = frozenset(
    {
        # sexual
        "fick",
        "fotz",
        "votz",
        "muschi",
        "wichs",
        "bums",
        "hure",
        "nutte",
        "titt",
        "möse",
        "pimmel",
        # scatological
        "scheiss",
        "schiss",
        "kack",
        "piss",
        "kotz",
        "strull",
        # slurs
        "neger",
        "zigeuner",
        "kanak",
        "spast",
        "untermensch",
    }
)

#: Exact whole words, not stems — matched only when the entire casefolded
#: word equals an entry, for a case a stem would take ordinary words down
#: with it. "schlampen" started life as a "Ruling 2" *stem* entry, on the
#: claim that it "catches the plural without touching schlampig, so nothing
#: is lost". That claim was wrong: as a substring, "schlampen" also matches
#: inside "verschlampen" (to mislay something through carelessness — an
#: entirely ordinary, producible verb, and one this project's own audit had
#: already named worth keeping when the broader "schlamp" stem was first
#: rejected). Matched as a whole word instead, "Schlampen" is still blocked
#: — "Schlampe", the singular, is not producible by this device at all, so
#: the plural/verb form is the one that matters — while both "schlampig"
#: (sloppy) and "verschlampen" survive. An entry that needs this same
#: precision — a word reachable only in particular forms, and inside ordinary
#: words as a stem — belongs here, not in `_BLOCKED_STEMS`.
#:
#: "poppen" is the second such case, and the round-two addition. It sits in
#: exactly the crude register the blocked "bums" does, but a "popp" stem would
#: also take "poppig" (garish), "aufpoppen" (to jazz something up) and
#: "verpoppen" with it — all ordinary and all producible. The three entries
#: below are every form of the verb *the shipped lexicon carries* that these
#: rings can spell, which is what was audited; the ordinary neighbours are
#: untouched, since none of them *equals* an entry. "Popper" was checked and
#: rejected: in German it names a 1980s youth subculture, and is a common
#: surname besides — not a vulgarity at all.
#:
#: What an exact list cannot do, said plainly rather than left to be found:
#: it does not cover every producible *string* carrying the stem, only the
#: dictionary forms. 2,400 of these rings' 103,680,000 readings contain
#: "popp", and "gepopp" (ge|P|o|pp|) is one of them and passes. That gap is
#: accepted, not overlooked: the same property already holds for "schlampen",
#: the stem is still the wrong trade (it would cost "poppig", "aufpoppen" and
#: "verpoppen"), and the only path that draws unfiltered strings rather than
#: dictionary words is "turn them for me", where 2,400 in 103,680,000 is
#: ~0.002% of draws. The honest fix for a known gap this size is wording, not
#: a filter that takes ordinary words with it.
_BLOCKED_EXACT = frozenset(
    {
        "schlampen",
        "popp",
        "poppen",
        "poppet",
    }
)


#: Scope, stated once so no comment has to guess at it again. `fit_for_stage`
#: covers the three paths on which *this machine* chooses a German word to
#: show — `find_word`, `rhyme_sweep`, and "turn them for me" in `app.py`. It
#: does not cover the whole stage, and two scenes are outside it on purpose:
#:
#: - **N+7** puts machine-selected German nouns on screen — the replacement
#:   and the eight-entry reel of neighbours it travels past — unfiltered. Of
#:   the 184,040 nouns in the shipped list, 186 are blocked; 150 otherwise
#:   clean nouns have one as their `+7` replacement and 567 pass one somewhere
#:   in the reel (measured; "Kachel" -> "Kackbeutel", "Scheitern" ->
#:   "Scheiße"). These three figures are a function of the list above, not
#:   constants: they were first written as 149/560/185, which was the count
#:   before three entries were added to that list in the same commit. Recount
#:   them against the list as it stands whenever it changes — they moved
#:   upward, and understating this exposure is the direction that matters.
#: - **The word ladder** searches its intermediate rungs through that same
#:   raw lexicon, and a rung can land on a blocked word. Rare, but not as rare
#:   as one might guess: 3 of 120 German ladders between ordinary four- and
#:   five-letter nouns passed one (measured — "zack" to "maki" climbs through
#:   "kack"), against the 1 in 120 the branch review sampled.
#:
#: Filtering either would be worse than the exposure. The noun at index+7 is
#: what N+7 *is* — skip it and the scene is performing something else while
#: claiming to perform N+7 — and a ladder with a rung dropped out of it is no
#: longer a ladder `check` would accept, so the scene would be handing its own
#: checker something it made up. A scene that lied about its procedure to keep
#: a word off screen would break the one promise this stage exists to keep, so
#: the exposure is accepted and written down instead.
#:
#: What makes that safe to record: both scenes ship scripted, deterministic
#: defaults that are clean — `die Katze saß auf dem Tisch` (see
#: `app.py`'s `N_PLUS_7_SOURCES`) and `kalt -> warm` (`WORD_LADDER_EXAMPLES`)
#: — so a recording of either scene as it loads shows the same clean output
#: every time. Only a recorder who types something else into the box can
#: reach the rest of the lexicon, and that is their own choice, made on
#: camera, not something the page did behind them.
def fit_for_stage(word: str) -> bool:
    """Whether `word` is fit to appear on a recorded stage.

    The one predicate every *Denckring* path that can put a machine-chosen
    word on screen — `find_word`, `rhyme_sweep`, and "turn them for me" in
    `app.py` — calls before it does, so a word that scene shows is filtered
    exactly once, in exactly one place, rather than trusted to whichever
    curation a given path happened to build for itself. Its reach stops
    there; see the note above for the two scenes outside it and why.
    """
    folded = word.casefold()
    if folded in _BLOCKED_EXACT:
        return False
    return not any(stem in folded for stem in _BLOCKED_STEMS)


#: "Turn them for me" does not need a real word — that is the whole point of
#: the "off the rings" verdict — so it only ever retries a draw
#: `fit_for_stage` itself rejects, which is a needle in the full combination
#: space: of the ~21,000 real words these rings can spell, well under 100
#: match `_BLOCKED_STEMS`, and almost every draw is not a real word at all.
#: A bound this small (rather than `FIND_ATTEMPTS`'s 20,000) is still several
#: orders of magnitude more headroom than that rarity needs.
TURN_ATTEMPTS = 50

#: ~1 turn in 4,900 lands on a word `is_word` recognises (measured). 20,000
#: attempts (~4x that mean) measured a ~0.3% failure rate in this fix round
#: — rare, but rare enough to show up as test flakiness once a test session
#: calls `find_word` a few dozen times, which is exactly what happened here.
#: 60,000 (~12x the mean) measured zero failures in 50 runs with the same
#: ~0.1-0.8s per call a viewer would wait on the button — see the task
#: report for both sets of numbers.
FIND_ATTEMPTS = 60_000


def find_word(attempts: int = FIND_ATTEMPTS) -> tuple[str, list[int]] | None:
    """Turn the rings at random, server-side, until `is_word` recognises the
    result and `fit_for_stage` accepts it, or say the search failed rather
    than hang a recording on it.

    A viewer will not sit through the ~4,900 tries a random turn needs on
    average, so the search happens here in one request rather than one click
    at a time in the browser. `pieces_for` re-derives the ring positions from
    the word that was found, rather than keeping the ones `device.spin`
    happened to draw, so the discs turn to the exact segmentation `check`
    itself would find — the same reason "turn them for me" does not just
    keep its own draw either.
    """
    machine = device.load("harsdoerffer_1651")
    german = german_pack()
    for _ in range(attempts):
        turned = device.spin(machine)
        word = "".join(turned)
        if word and german.is_word(word) and fit_for_stage(word):
            pieces = pieces_for(word)
            if pieces is not None:
                return word, pieces
    return None


@dataclass(frozen=True)
class RhymeEnding:
    """One locked reading of the medial, final and suffix rings — Harsdörffer's
    "Reimsilbe" — offered to rhyme mode. The initial ring (`anfangsbuchstabe`)
    is what sweeps; the prefix ring (`vorsylbe`) stays blank throughout, as
    the quotation names only the second, third and fourth rings."""

    label: str
    mittelbuchstabe: str
    endbuchstabe: str
    nachsylbe: str


#: A presentation choice, not a safety mechanism: `fit_for_stage` is what
#: keeps every word this scene shows clean, on every path, so an ending does
#: not need curating to be safe to offer. These five are offered because
#: they give a good yield to watch accumulate, measured against the shipped
#: lexicon after `fit_for_stage` runs (see the task report): -acken 23,
#: -ecken 23, -allen 17, -eck 22, -ein 21. A hand-read pass over -acken once
#: missed "Kacken" here (23 real words, not the 24 an unfiltered count
#: would show) — exactly the failure mode that made curation the wrong
#: mechanism to rely on in the first place.
RHYME_ENDINGS: list[RhymeEnding] = [
    RhymeEnding("-acken", "a", "ck", "en"),
    RhymeEnding("-ecken", "e", "ck", "en"),
    RhymeEnding("-allen", "a", "ll", "en"),
    RhymeEnding("-eck", "e", "ck", ""),
    RhymeEnding("-ein", "ei", "n", ""),
]


def rhyme_ending(label: str) -> RhymeEnding | None:
    """One curated ending by its label, or `None` for anything else."""
    for ending in RHYME_ENDINGS:
        if ending.label == label:
            return ending
    return None


@dataclass(frozen=True)
class RhymeSweep:
    """One full sweep of the initial ring against one locked ending.

    `mittelbuchstabe_index`, `endbuchstabe_index` and `nachsylbe_index` are
    the true positions the medial, final and suffix rings must be set to —
    numbers the client uses directly, never text it would have to find on a
    ring by searching for it. That search is exactly what `endbuchstabe`'s
    two repeated parts ('f' and 'ls', each twice among its 120) make
    unsound: a ring positioned by matching text can only ever land on the
    first occurrence of a repeated part, whichever one was actually meant.
    None of `RHYME_ENDINGS`' own values happen to repeat, so this never
    bites the five curated endings in practice — but the position is still
    carried as the index it always was, not re-derived by the client from
    text, so the class of bug closes everywhere, not only where it was
    caught. `words` is the sweep itself: one entry per position on the
    initial ring, in ring order, the word found there or `""` — position i
    is always the initial ring's true index i, by construction, so nothing
    about walking it needs finding either.
    """

    label: str
    mittelbuchstabe_index: int
    endbuchstabe_index: int
    nachsylbe_index: int
    words: list[str]


def rhyme_sweep(ending: RhymeEnding) -> RhymeSweep:
    """One entry per position on the initial disc, in ring order: the word
    that position spells against the locked ending, or `""` where `is_word`
    rejects it or `fit_for_stage` does — alongside the true positions the
    other three locked rings must show.

    This is the quotation turned into a search rather than an instruction:
    "seek the rhyme syllables on the third and fourth ring [and turn] the
    rhyme letters of the second ring to them." The medial, final and suffix
    rings are the ones `ending` already locked; this walks every letter the
    second ring (`anfangsbuchstabe`) offers and reads off what comes out. The
    full sweep, blanks included, so the scene can walk the disc through every
    position in order rather than only the hits.
    """
    slots = rings().slots
    initial = next(slot for slot in slots if slot.name == "anfangsbuchstabe")
    mittelbuchstabe = next(slot for slot in slots if slot.name == "mittelbuchstabe")
    endbuchstabe = next(slot for slot in slots if slot.name == "endbuchstabe")
    nachsylbe = next(slot for slot in slots if slot.name == "nachsylbe")
    german = german_pack()
    swept = []
    for letters in initial.alternatives:
        word = letters + ending.mittelbuchstabe + ending.endbuchstabe + ending.nachsylbe
        swept.append(word if german.is_word(word) and fit_for_stage(word) else "")
    return RhymeSweep(
        label=ending.label,
        mittelbuchstabe_index=mittelbuchstabe.alternatives.index(ending.mittelbuchstabe),
        endbuchstabe_index=endbuchstabe.alternatives.index(ending.endbuchstabe),
        nachsylbe_index=(
            len(nachsylbe.alternatives)
            if ending.nachsylbe == ""
            else nachsylbe.alternatives.index(ending.nachsylbe)
        ),
        words=swept,
    )


#: A corpus's own `style` marker decides how the scene looks. Jean Paul's excerpts are
#: paper and copperplate; anything else is a modern card.
REGISTERS = {"jean_paul": "baroque"}


def register_for(style: str) -> str:
    """The visual register a corpus's `style` marker asks for."""
    return REGISTERS.get(style, "modern")


#: The same marker, this time suggesting which language the throw and the Witz
#: reading default to — Jean Paul's excerpts want German, everything else English.
#: A default only: the scene's language toggle can always override it, and a corpus
#: is free to be in any language regardless of what its own register implies.
LANG_DEFAULTS = {"jean_paul": "de"}


def default_lang(style: str) -> str:
    """The language a corpus's own `style` marker suggests, before the toggle
    overrides it. Independent of `register_for` — a register is how the page
    looks, a language is what `apply` and the Witz reading are asked for — so
    the two are kept as separate lookups even though they share a source."""
    return LANG_DEFAULTS.get(style, "en")


@dataclass(frozen=True)
class CorpusChoice:
    """One corpus, offered to the scene.

    `register` and `lang` are both resolved from `style` here, on the server,
    rather than left for the page to work out: the scene's picker writes
    `lang` onto each option so the shared toggle-sync script can read it
    without re-running `default_lang`'s rule in JavaScript, which is what it
    used to do from `data-style`. One rule, in one place.
    """

    path: str
    name: str
    entries: int
    style: str
    register: str
    lang: str


def corpus_choices() -> list[CorpusChoice]:
    """Whatever is in `DENCKRING_CORPORA`, with its register and language
    suggestion resolved."""
    return [
        CorpusChoice(
            path=item.path,
            name=item.name,
            entries=item.entries,
            style=item.style,
            register=register_for(item.style),
            lang=default_lang(item.style),
        )
        for item in corpora.available()
    ]


@dataclass(frozen=True)
class Slip:
    """One drawn excerpt: the field it was filed under, and whether it is
    genuinely filed under the headword the throw asked for.

    Both are facts about the entry itself, read back after the draw — not
    predictions from the request. `apply` widens a too-thin headword pool to
    the whole corpus without saying so, so a pre-flight guess about the
    headword's own pool can disagree with what was actually drawn; only the
    result can't.
    """

    text: str
    domain: str
    filed: bool


def slips_of(corpus_text: str, throw: str, headword: str = "") -> list[Slip]:
    """Match each line a throw produced back to the entry it came from.

    The scene's whole point is a collision *across* fields, which is invisible
    in the prose alone — a viewer has to be able to see the field each slip
    was filed under, not just take `distinct_domains=True` on faith. Likewise
    whether a slip is actually filed under `headword`: when the headword's own
    pool was too thin, `apply` draws from the whole corpus instead, and a slip
    from that wider draw may not carry the headword at all.
    """
    from denckring.core import corpus as denckring_corpus
    from denckring.core.errors import MalformedCorpus

    try:
        parsed = denckring_corpus.parse(corpus_text)
    except MalformedCorpus:
        return []
    by_text = {entry.text.strip(): entry for entry in parsed.entries()}
    wanted = headword.casefold() if headword else None
    slips = []
    for line in throw.split("\n"):
        body = line.strip()
        if not body:
            continue
        entry = by_text.get(body)
        domain = entry.domain if entry and entry.domain else "unfiled"
        filed = bool(entry and wanted and any(hw.casefold() == wanted for hw in entry.headwords))
        slips.append(Slip(text=body, domain=domain, filed=filed))
    return slips


@dataclass(frozen=True)
class Step:
    """One noun's journey down the list."""

    word: str
    replacement: str
    neighbours: list[str]


def pack(lang: Lang = "en") -> LanguagePack:
    """The pack whose noun list the N+7 scene walks — English by default, so
    every other caller (`displacement`'s own default, the golden fixtures the
    scene's tests pin) keeps behaving exactly as it did before the toggle."""
    return get_pack(lang)


def displacement(source: str, offset: int = 7, lang: Lang = "en") -> list[Step]:
    """Each noun of `source`, with the entries it passes on the way to its
    replacement — walked through whichever language's noun list `lang` names,
    since that is what actually decides both the replacement and the reel of
    neighbours a viewer watches it pass.

    Deliberately unfiltered: `fit_for_stage` is not applied here and must not
    be. See the note above it for the measured exposure, why filtering would
    make this scene lie about the procedure it demonstrates, and why the
    scripted default is safe to record anyway.
    """
    chosen = pack(lang)
    nouns = chosen.nouns()
    steps: list[Step] = []
    for token in chosen.tokenize(source):
        index = chosen.noun_index(token.lower())
        if index is None:
            continue
        landing = index + offset
        if landing >= len(nouns):
            continue
        steps.append(
            Step(
                word=token,
                replacement=nouns[landing],
                neighbours=[nouns[i] for i in range(index, landing + 1)],
            )
        )
    return steps


# ── scene four: Cent mille milliards de poèmes ──────────────────────────────
# Queneau's own ten sonnets are still in copyright (he died in 1976) and are
# not shipped and never will be. Two sets of fourteen strips, three
# alternatives each, were written for this scene instead — English and
# German, see the task report for the attribution the page itself carries —
# and both are read with the library's own `alternatives()`, the exact
# parser `check` runs against them, so the scene and the checker can never
# read two different sheets, for either set.

#: Shipped as data alongside the scene rather than through any library
#: capability — the brief asks for "no new library capability", and the
#: procedure's own generality (one line per position, `|`-separated) already
#: covers a strip sheet that lives anywhere.
_QUENEAU_STRIPS_PATHS: dict[Lang, Path] = {
    "en": Path(__file__).parent / "data" / "queneau_strips.txt",
    "de": Path(__file__).parent / "data" / "queneau_strips_de.txt",
}

#: The strip sets this scene actually ships, in the order the picker offers
#: them — the only values its own `lang` field can carry, and what
#: `queneau_lang` narrows a request down to.
QUENEAU_SETS: tuple[Lang, ...] = ("en", "de")


def queneau_lang(value: str) -> Lang:
    """Narrow a request string to a strip set this scene actually ships.

    Not `bench.as_lang`: that narrows to any of `Lang`'s three values, and
    this scene has strips behind only two of them — a request naming the
    third, or nothing this picker itself would ever send, falls back to
    English exactly as `bench.as_lang` falls back for an unrecognised value.
    """
    return value if value in QUENEAU_SETS else "en"


def queneau_source(lang: Lang = "en") -> str:
    """The strip sheet itself, byte for byte, for whichever set `lang` names."""
    return _QUENEAU_STRIPS_PATHS[lang].read_text(encoding="utf-8")


def queneau_offered(lang: Lang = "en") -> list[list[str]]:
    """One list of alternatives per position, parsed fresh each call with the
    same `alternatives()` `check` itself runs — so a claim this scene makes
    about what a position offers can never drift from what the checker reads."""
    return queneau_alternatives(queneau_source(lang))


def queneau_combinations(lang: Lang = "en") -> int:
    """Three alternatives per position to the fourteenth power — computed
    from what actually loaded, never typed in, so a strip added or removed
    could not leave a stale figure on screen. Per set: German's own count is
    a fresh product over the German file, not the English constant reused.

    Deliberately not cached, for the same reason `queneau_offered` itself
    is not: this number is a claim about that same file, computed by
    reading it, and the two can never be allowed to drift apart. Caching
    this alone (an earlier version of this function did, briefly) would
    split the file into a live path and a cached path reading the same
    source — edit the strip file without restarting the process, and the
    page would render fresh lines from `queneau_offered` while reporting a
    stale count from here. Fourteen lines is not enough text for the
    re-read to cost anything worth trading that guarantee for, in either
    set.
    """
    total = 1
    for options in queneau_offered(lang):
        total *= len(options)
    return total


@dataclass(frozen=True)
class QueneauStrip:
    """One position on the sheet: what it offers, and which one is showing."""

    position: int
    alternatives: list[str]
    index: int

    @property
    def line(self) -> str:
        return self.alternatives[self.index]


@dataclass(frozen=True)
class QueneauPoem:
    """Fourteen strips read top to bottom, plus the count every combination
    of them makes."""

    strips: list[QueneauStrip]
    combinations: int

    @property
    def lines(self) -> list[str]:
        return [strip.line for strip in self.strips]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


def queneau_poem(state: list[int], lang: Lang = "en") -> QueneauPoem:
    """The poem `state` reads off `lang`'s own strips — one chosen index per
    position, and a combination count computed from that same set."""
    offered = queneau_offered(lang)
    strips = [
        QueneauStrip(position=i, alternatives=options, index=state[i])
        for i, options in enumerate(offered)
    ]
    return QueneauPoem(strips=strips, combinations=queneau_combinations(lang))


def queneau_initial_state(lang: Lang = "en") -> list[int]:
    """First paint: the first alternative at every position — deterministic,
    the way Denckring's own rings start every disc at index 0, so first paint
    is the same poem every time the scene loads, or the picker switches sets,
    rather than a draw a test would have to pin against randomness."""
    return [0 for _ in queneau_offered(lang)]


def queneau_deal(lang: Lang = "en", rng: random.Random | None = None) -> list[int]:
    """A fresh index for every position of `lang`'s own strips — the deal
    control's whole job."""
    chooser = rng if rng is not None else random.Random()
    return [chooser.randrange(len(options)) for options in queneau_offered(lang)]


def queneau_flip(
    state: list[int], position: int, lang: Lang = "en", rng: random.Random | None = None
) -> list[int]:
    """Redraw one position only, landing on a different alternative from the
    one already showing — the other thirteen positions untouched.

    Excluding the current index is deliberate: a flip that happened to redraw
    the same line again would look, on camera, like nothing had happened at
    all, even though the draw was genuine.
    """
    offered = queneau_offered(lang)
    chooser = rng if rng is not None else random.Random()
    options = offered[position]
    remaining = [i for i in range(len(options)) if i != state[position]]
    new_state = list(state)
    new_state[position] = chooser.choice(remaining) if remaining else state[position]
    return new_state


def queneau_state_from_text(raw: str, lang: Lang = "en") -> list[int] | None:
    """Parse the hidden `state` field a form posted back, against `lang`'s own
    strips, or `None` if it does not describe a poem that set could show — a
    hand-crafted or stale request, never one this page's own markup would
    send."""
    offered = queneau_offered(lang)
    parts = raw.split(",")
    if len(parts) != len(offered):
        return None
    try:
        indices = [int(part) for part in parts]
    except ValueError:
        return None
    if any(
        not (0 <= index < len(options)) for index, options in zip(indices, offered, strict=True)
    ):
        return None
    return indices


def queneau_state_to_text(state: list[int]) -> str:
    """The hidden field's own format — the inverse of `queneau_state_from_text`."""
    return ",".join(str(index) for index in state)


# ── scene five: word ladder ─────────────────────────────────────────────────
# Carroll's Doublets: change one letter, land on a word, repeat until the
# target is reached. `apply` does the searching; `check` does the confirming
# — both real, both shown, per the brief's own "What it does".
#
# The intermediate rungs come out of the raw lexicon, unfiltered, and that is
# deliberate: `fit_for_stage` is not applied here and must not be — a ladder
# with a rung taken out of it is not a ladder `check` would accept. See the
# note above `fit_for_stage` for the measured exposure and the whole argument.

#: One pair per language the toggle offers, both landing on "warm" — the
#: brief's own instruction that the pair is worth showing off together, the
#: same destination reached two different ways. Mirrors `N_PLUS_7_SOURCES`'
#: shape (a dict keyed by `Lang`) rather than `N_PLUS_7_DEFAULT_LANG`'s bare
#: constant, because this toggle needs two words per language, not one
#: sentence.
WORD_LADDER_EXAMPLES: dict[Lang, tuple[str, str]] = {
    "en": ("cold", "warm"),
    "de": ("kalt", "warm"),
}

#: English first, the same rule `N_PLUS_7_DEFAULT_LANG` follows and the brief
#: asks this scene to match rather than invent its own.
WORD_LADDER_DEFAULT_LANG: Lang = "en"


@dataclass(frozen=True)
class Rung:
    """One word of the ladder, and the one letter that changed to reach it.

    `changed` is the index into the word of the letter that differs from the
    rung above — `None` for the first rung, which changed nothing to get
    there. That marking is the scene's whole explanatory burden (see the
    brief), so it is a fact this dataclass carries rather than something the
    template infers by eye.
    """

    word: str
    changed: int | None


@dataclass(frozen=True)
class Ladder:
    """A search's own report: the ladder it found, or which of the two
    distinct reasons it found none.

    `problem` is `""` for a real ladder, `"unknown_word"` when the lexicon
    does not know one of the two endpoints (so no search was even run), and
    `"no_ladder"` when both endpoints are real words but no path between them
    was found within the search's own bounds. These are different answers —
    "there is no ladder from here to there" is true and interesting, not a
    dressed-up version of "that is not a word" — so the scene must be able to
    tell them apart, not fold them into one generic failure.
    """

    rungs: list[Rung]
    problem: str
    message: str

    @property
    def text(self) -> str:
        """Space-joined, the exact shape `apply` returns and `check` reads —
        so a ladder this dataclass reports as real is provably the same text
        the library itself produced, not a reconstruction from the rungs."""
        return " ".join(rung.word for rung in self.rungs)


def _changed_letter(previous: str, word: str) -> int | None:
    """The one index where `word` differs from `previous`, or `None` if they
    agree everywhere (never true of a real ladder step, but a defensive
    answer beats an `IndexError` on any input this scene did not itself
    produce).

    Compared letter by letter on the raw strings, not folded: `apply`'s own
    search substitutes exactly one character at a time (see
    `word_ladder._substitutions`), so the raw strings already differ at
    exactly one position for any ladder it actually returns — folding, which
    exists so a German step through a diacritic still counts as one letter,
    is `check`'s own concern when judging a ladder typed by hand, not a
    ladder this scene generated itself.
    """
    for index, (before, after) in enumerate(zip(previous, word, strict=True)):
        if before != after:
            return index
    return None


def word_ladder(start: str, target: str, lang: Lang = "en") -> Ladder:
    """Search a ladder from `start` to `target`, distinguishing the two ways
    the search can come back empty.

    The lexicon check happens here, before `apply` is ever called, rather
    than by parsing which of `apply`'s own `NoCandidateWord` messages came
    back — `apply` folds "endpoint unknown" and "search exhausted" into the
    same exception with two different `reason` strings, and matching English
    prose to tell them apart would break the moment either wording changed.
    Checking `pack.is_word` directly here means the two failure modes are two
    branches of this function, not two readings of one string.
    """
    cleaned_start = start.strip().lower()
    cleaned_target = target.strip().lower()
    if (
        not cleaned_start
        or not cleaned_target
        or not cleaned_start.isalpha()
        or not cleaned_target.isalpha()
        or len(cleaned_start) != len(cleaned_target)
    ):
        return Ladder(
            rungs=[],
            problem="invalid",
            message="both words must be the same length, letters only.",
        )

    chosen = get_pack(lang)
    unknown = [w for w in (cleaned_start, cleaned_target) if not chosen.is_word(w)]
    if unknown:
        return Ladder(
            rungs=[],
            problem="unknown_word",
            message=f"the lexicon does not have {unknown[0]!r} — try a word it knows.",
        )

    procedure = get("word_ladder")
    # `get` is typed as the base class, which has no `apply` — ADR 0002 keeps it
    # off `BaseProcedure` because it is optional. Narrow once, here.
    assert isinstance(procedure, Constructive)
    try:
        text = procedure.apply(cleaned_start, lang=lang, target=cleaned_target)
    except NoCandidateWord:
        return Ladder(
            rungs=[],
            problem="no_ladder",
            message=f"there is no ladder from {cleaned_start!r} to {cleaned_target!r} "
            "within the search's own bounds.",
        )
    except InvalidParams as exc:
        # Both endpoints are known words of equal length — the branch above
        # already refused anything else — so this is unreachable in practice,
        # but caught rather than left to become a 500 if `apply`'s own
        # validation ever grows a check this function does not yet share.
        return Ladder(rungs=[], problem="invalid", message=str(exc))

    words = text.split()
    rungs = [Rung(word=words[0], changed=None)]
    for previous, word in pairwise(words):
        rungs.append(Rung(word=word, changed=_changed_letter(previous, word)))
    return Ladder(rungs=rungs, problem="", message="")


# ── scene six: cut-up ────────────────────────────────────────────────────────
# Gysin and Burroughs, Minutes to Go (1960): cut the page into fragments,
# reassemble them in a new order. `cut_up`'s checker verifies provenance —
# every word in the result must have come from the source, counted with
# multiplicity (`denckring/procedures/cut_up.py`) — which gives this scene
# something none of the other five have: a demonstration that can be made to
# fail on purpose. See `CUT_UP_SMUGGLE` below, and `cut_up_smuggled`.

#: Written for this scene, not quoted — see `stage_cut_up.html`'s own
#: attribution. Reused byte for byte from the scene this one replaces (this
#: project's former `HAIKUIZATION_SOURCE`): six lines about the Denckring's
#: own paper discs, which ties the stage's last scene back to its first.
CUT_UP_SOURCE = """Five discs of nothing more than cut-out paper,
and each of them, whenever someone turns,
will bring together parts that spell a word
no hand set down, and yet the strange thing stands
as evidence of everything a language
can hold inside one folded paper sheet."""

#: The tamper control's own word. Picked and pinned because it is not one of
#: `CUT_UP_SOURCE`'s own 47 words — verified by tokenising the shipped source
#: with this same pack rather than assumed (see the task report) — so
#: appending it to a genuine cut-up is guaranteed to trip `word_not_in_source`
#: rather than depend on the source happening to read a particular way today.
CUT_UP_SMUGGLE = "helicopter"


def cut_up_source_words(source: str, lang: Lang = "en") -> list[str]:
    """`source`'s own words, in `word_spans` order — the same call
    `cut_up.apply` and `cut_up.check` themselves make, and the fixed array
    every result word below ties back to by index. This list never
    reshuffles; it is state one, "the page, uncut"."""
    return [word for _, word in word_spans(source, get_pack(lang))]


@dataclass(frozen=True)
class CutUpToken:
    """One piece of a source line: either a word `word_spans` found, or the
    literal gap (space or punctuation) between two of them.

    `source_index` is only meaningful on a word token — the same global
    index `cut_up_source_words` and a genuine result word's own
    `CutUpWord.source_index` carry, so the client can find the exact span a
    travelling word came from. `None` on a gap token.
    """

    text: str
    is_word: bool
    source_index: int | None


@dataclass(frozen=True)
class CutUpLine:
    """One line of the source, as the literal text between and around its
    words plus the words themselves — enough to render the line exactly as
    typed, with only its words individually addressable."""

    tokens: list[CutUpToken]


def cut_up_source_lines(source: str, lang: Lang = "en") -> list[CutUpLine]:
    """`source`'s own lines, tokenised so state one, "the page, uncut", can
    render exactly as typed — six lines, their own punctuation and line
    breaks intact — while still giving every word a span the animation can
    measure a journey from (see `cut_up_source_words`, whose flat order this
    function's own running `index` reproduces line by line; a test pins the
    two against each other).
    """
    pack = get_pack(lang)
    lines: list[CutUpLine] = []
    index = 0
    for _, line_text in line_spans(source):
        spans = word_spans(line_text, pack)
        tokens: list[CutUpToken] = []
        cursor = 0
        for offset, word in spans:
            if offset > cursor:
                tokens.append(CutUpToken(line_text[cursor:offset], False, None))
            tokens.append(CutUpToken(word, True, index))
            index += 1
            cursor = offset + len(word)
        if cursor < len(line_text):
            tokens.append(CutUpToken(line_text[cursor:], False, None))
        lines.append(CutUpLine(tokens=tokens))
    return lines


@dataclass(frozen=True)
class CutUpWord:
    """One word of a cut-up result, and where it came from.

    `source_index` is the position this word held in `cut_up_source_words`'s
    own array — not a text match, which a repeated word (this source repeats
    "paper" and "of") would leave ambiguous about which occurrence travelled
    where. `None` marks the one word that has no such position: the tamper
    control's own smuggled word, which was never cut from the page at all.
    """

    text: str
    source_index: int | None


@dataclass(frozen=True)
class CutUp:
    """One cut-up run: the source's own words, unreshuffled, and the result
    words read back from the shuffle actually performed."""

    source_words: list[str]
    result_words: list[CutUpWord]

    @property
    def text(self) -> str:
        """Space-joined, the exact shape `apply` returns and `check` reads."""
        return " ".join(word.text for word in self.result_words)


def cut_up(source: str, lang: Lang = "en", seed: int | None = None) -> CutUp:
    """Shuffle `source`'s own words, the way `cut_up.apply` does, but keep
    each result word tied to the source position it travelled from.

    Reimplements the shuffle rather than calling `apply` and matching text
    back onto the source afterwards: `apply` returns text alone, and a
    repeated word would make that matching ambiguous about which occurrence
    moved where (see `CutUpWord`). Shuffling a parallel array of indices under
    the same seed is `random.shuffle`'s own guarantee, not a coincidence —
    Fisher-Yates only ever consumes randomness keyed to the sequence's
    *length*, never its content, so shuffling `range(n)` and shuffling the
    words themselves under one seed produce the identical permutation. A test
    pins this function's own `.text` against `cut_up.apply`'s for a spread of
    seeds, so the two can never quietly drift apart.
    """
    words = cut_up_source_words(source, lang)
    indices = list(range(len(words)))
    random.Random(seed).shuffle(indices)
    result = [CutUpWord(text=words[i], source_index=i) for i in indices]
    return CutUp(source_words=words, result_words=result)


def cut_up_smuggled(source: str, lang: Lang = "en", seed: int | None = None) -> CutUp:
    """The same cut-up, with `CUT_UP_SMUGGLE` appended — one word the
    scissors could not have produced, so `check` fails it by name (see the
    brief's own "the validator is the eval"). The failing report this
    produces runs through the exact same `check` call the genuine cut does;
    nothing about the verdict itself is special-cased."""
    genuine = cut_up(source, lang, seed)
    tampered = [*genuine.result_words, CutUpWord(text=CUT_UP_SMUGGLE, source_index=None)]
    return CutUp(source_words=genuine.source_words, result_words=tampered)
