"""The stage: what each scene is, and the data it needs.

Preparation only. Nothing here renders, and nothing here touches HTTP — a scene's
route reads from this module and hands the result to a template, so the thing a
scene claims can be tested without a browser.
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass, replace
from functools import lru_cache
from itertools import pairwise
from pathlib import Path
from typing import Any

from denckring import check as denckring_check
from denckring import produce
from denckring.core import device, domain
from denckring.core.calculator import FROM_DIGIT, from_digits
from denckring.core.errors import DenckringError, InvalidParams, NoCandidateWord
from denckring.core.protocol import Constructive, Lang, LanguagePack
from denckring.core.registry import get
from denckring.core.text import line_spans, word_spans
from denckring.lang import get_pack
from denckring.procedures.cent_mille_milliards import alternatives as queneau_alternatives
from denckring.procedures.poesie_automat import SEPARATOR as POESIE_AUTOMAT_SEPARATOR
from explorer import corpora

#: N+7's own default, mirroring `default_lang`'s shape — but with no corpus to
#: read a suggestion from, the toggle simply starts on English every time
#: (the brief's own instruction), so this is a bare constant rather than a
#: style-keyed lookup.
N_PLUS_7_DEFAULT_LANG: Lang = "en"

#: How far down the noun list a noun is displaced, where the reader has not
#: said. Seven, because the procedure is named after it — but `displace` has
#: always taken this by parameter, and the scene's route used to pass a literal
#: 7 twice while `stage.displacement`'s own signature defaulted to it. Named
#: once here so the scene, the reading beside it and the procedure cannot come
#: to disagree about which transformation is being demonstrated.
N_PLUS_7_OFFSET = 7

#: How far the scene's own control will travel, either way.
#:
#: A slider rather than a list of offers, because the point is that N+7 is a
#: *family* and seven is only the member it is named after — and a family is
#: something you sweep, not something you pick from a menu. Fifteen each way
#: because that is far enough for the character of the transformation to change
#: (a neighbour at N+1 is often a compound of the same stem; at N+15 it is
#: another word entirely) and near enough that every step is still a step.
N_PLUS_7_REACH = 15

#: How many entries either side of the travelled span the open page shows, so
#: the noun is not on the first line and its replacement not on the last.
DICTIONARY_MARGIN = 2


def n_plus_7_offset(value: str) -> int:
    """Narrow a posted offset to one the control can actually reach.

    Clamped rather than refused: the slider cannot produce anything outside its
    own range, so a value from outside it is a hand-typed request, and the
    honest answer to one is the nearest thing the scene will show rather than
    an error page.

    Zero is allowed through, and that is deliberate. `displace` at 0 returns the
    source unchanged and `displacement_report` tolerates an unchanged word — so
    N+0 earns a green verdict for a text nothing was done to. A slider that
    silently skipped its own midpoint would be lying about its range; the scene
    says what N+0 is instead (see `_stage_displaced.html`).
    """
    try:
        offset = int(value)
    except ValueError:
        return N_PLUS_7_OFFSET
    return max(-N_PLUS_7_REACH, min(N_PLUS_7_REACH, offset))


@dataclass(frozen=True)
class Entry:
    """One line of the open page: a word, and what it is to this displacement."""

    word: str
    #: 0 for the noun being looked up, `offset` for where it lands, and the
    #: signed distance for everything between and either side.
    at: int
    passed: bool


def dictionary_page(word: str, offset: int = N_PLUS_7_OFFSET, lang: Lang = "en") -> list[Entry]:
    """The list, open at `word`, with everything it travels past.

    The scene's figure used to be a reel per noun — the journey as motion. This
    is the same journey as a page: the entry looked up, the entry landed on, and
    every entry between them, in the order the list has them. It is the same
    walk `displacement` makes, and it exists because the list is the other half
    of the rule and the only direction that puts the list itself on stage.

    Wraps at the ends exactly as `displace` does, so a noun near the start of
    the list displaced backwards shows the entries it really lands among rather
    than none at all. Empty when the list does not know the word.
    """
    chosen = pack(lang)
    nouns = chosen.nouns()
    index = chosen.noun_index(word.lower())
    if index is None:
        return []
    low, high = min(0, offset), max(0, offset)
    return [
        Entry(
            word=nouns[(index + step) % len(nouns)],
            at=step,
            passed=low <= step <= high,
        )
        for step in range(low - DICTIONARY_MARGIN, high + DICTIONARY_MARGIN + 1)
    ]


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
        caption=(
            "Lescure, 1961. Every noun, seven entries down the list: cat \u2192 catacomb, "
            "and catafalque until the Open English WordNet migration moved its neighbours."
        ),
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
    Scene(
        slug="llull_figure",
        title="Llullian figure",
        procedure_id="llull_figure",
        caption="Ramon Llull, 1305-08. Turn the wheels; the same chamber reads six ways.",
    ),
    Scene(
        slug="poesie_automat",
        title="Poesie-Automat",
        procedure_id="poesie_automat",
        caption=(
            "Enzensberger, Landsberg 2000. Press the button; the flaps clatter "
            "into one of 10\u00b3\u2076 poems."
        ),
    ),
    Scene(
        slug="calculator_word",
        title="Taschenrechnerwort",
        caption=(
            "Pocket calculators, from the 1970s. Type the digits, turn the machine "
            "over: 7353 is ESEL."
        ),
        procedure_id="calculator_word",
    ),
    Scene(
        slug="paronomasia",
        title="Die Straße der schlechten Wortspiele",
        procedure_id="paronomasia",
        caption=(
            "The punning shopfront. A word of a known phrase displaced by one that "
            "sounds like it, or spliced inside it \u2014 and every sign checked where "
            "it hangs."
        ),
    ),
]


def scene(slug: str) -> Scene:
    """One scene by slug, or `KeyError`."""
    for candidate in SCENES:
        if candidate.slug == slug:
            return candidate
    raise KeyError(slug)


@dataclass(frozen=True)
class Reading:
    """One companion page: the argument a scene is too small to carry.

    A scene is 1280px by 720px with `overflow: hidden`, driven by hand and recorded.
    That frame holds a machine and a verdict and very little else, which is why
    almost everything this repository knows about these devices lives in
    comments here rather than anywhere a reader can see it. A reading is where
    that goes: scrollable, never in a frame, and reachable only from the chrome
    the recording flag already takes away.

    It is *not* a second stage. Nothing here autoplays, nothing here is
    pre-baked, and every number on one of these pages is computed from the same
    data the scene runs on — the rule ADR 0019 sets for the catalogue applies
    with more force here, because prose is where a quoted count goes to look
    settled.
    """

    slug: str
    title: str
    #: The standfirst under the title. One sentence or two, no more.
    dek: str
    #: The scenes this reading stands behind, in the order it treats them.
    #: Two of them cover a pair, because the pair is the argument: Harsdörffer
    #: cuts paper apart to assemble words and Gysin cuts assembled words apart,
    #: and neither half says much alone.
    scenes: tuple[str, ...]


READINGS: list[Reading] = [
    Reading(
        slug="wheel-and-scissors",
        title="The Wheel and the Scissors",
        dek=(
            "Harsdörffer built a paper computer for the German language and told the "
            "bookbinder to cut it out. Three centuries later the scissors came back, "
            "pointed the other way."
        ),
        scenes=("denckring", "cut_up"),
    ),
    Reading(
        slug="oulipo-machines",
        title="Two Machines from the Ouvroir",
        dek=(
            "Queneau and Le Lionnais set up a workshop to build constraints rather "
            "than poems. One of these assembles; the other dismantles."
        ),
        scenes=("cent_mille_milliards", "n_plus_7"),
    ),
    Reading(
        slug="the-figure",
        title="Nine Letters, Turned",
        dek=(
            "Llull's wheels are the ancestor every other machine on this stage is "
            "measured against — and the first whose limits were argued about in print."
        ),
        scenes=("llull_figure",),
    ),
    Reading(
        slug="the-automat",
        title="Sechs Zeilen, sechs Wortlager",
        dek=(
            "A split-flap board on a square in Landsberg am Lech for three days in "
            "2000, and the one part of it this repository can honestly reproduce."
        ),
        scenes=("poesie_automat",),
    ),
]


def reading(slug: str) -> Reading:
    """One reading by its own slug, or `KeyError`."""
    for candidate in READINGS:
        if candidate.slug == slug:
            return candidate
    raise KeyError(slug)


def reading_for(scene_slug: str) -> Reading | None:
    """The reading that stands behind `scene_slug`, or `None` where none does.

    `None` is a real answer, not a gap to be filled later: the word ladder and
    Ideenwürfeln say what they are on the scene itself, and a companion page
    that had nothing to add would be furniture.
    """
    for candidate in READINGS:
        if scene_slug in candidate.scenes:
            return candidate
    return None


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
#: curation at all — a raw 668,579-word lexicon answers "is this a word", not
#: "is this fit to show on a recording". (That figure is `words.txt`, which is
#: what `is_word` reads. It said 184,040 here until this pass, which is the
#: shipped *noun* list — the number the note below about blocked stems is
#: correctly counting, and the wrong one for a membership test.) See
#: `fit_for_stage` below, and the
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
    """One drawn excerpt: the field it was filed under, whether it is
    genuinely filed under the headword the throw asked for, and where it came
    from.

    All of these are facts about the entry itself, read back after the draw —
    not predictions from the request. `apply` widens a too-thin headword pool
    to the whole corpus without saying so, so a pre-flight guess about the
    headword's own pool can disagree with what was actually drawn; only the
    result can't.

    `source` and `entry_id` are the corpus's own two fields, verbatim and
    unrepaired. Both are `""` where the corpus gives nothing: the Würzburg
    Jean-Paul export carries a `source` on fewer than half its entries, and a
    placeholder standing in for the missing ones would read as a citation this
    project cannot support. `entry_id` is likewise not parsed into anything
    prettier — `Ia-05-reg-1779-0010` plainly *is* a locator in that edition,
    but rendering it as a band and a number would be asserting a reading of a
    scheme nothing here has verified.
    """

    text: str
    domain: str
    filed: bool
    source: str = ""
    entry_id: str = ""


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
        slips.append(
            Slip(
                text=body,
                domain=domain,
                filed=filed,
                source=(entry.source if entry and entry.source else ""),
                entry_id=(entry.id if entry and entry.id else ""),
            )
        )
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


def displacement(source: str, offset: int = N_PLUS_7_OFFSET, lang: Lang = "en") -> list[Step]:
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
    # The reel walks in the direction of travel and wraps at the ends of the
    # list, both because `displace` does: it lands on `(index + offset) %
    # len(nouns)`, and a reel computed any other way would animate a
    # substitution the text beside it did not make.
    #
    # It used to walk `range(index, landing + 1)` and skip any noun whose
    # landing ran past the end of the list. That was two disagreements with
    # `displace` at once — a noun near the end of the list was displaced in the
    # result while its column simply vanished from the figure, and a negative
    # offset produced an empty range, so every column disappeared and the reel
    # said the list knew none of these words.
    direction = 1 if offset >= 0 else -1
    for token in chosen.tokenize(source):
        index = chosen.noun_index(token.lower())
        if index is None:
            continue
        steps.append(
            Step(
                word=token,
                replacement=nouns[(index + offset) % len(nouns)],
                neighbours=[
                    nouns[(index + step * direction) % len(nouns)]
                    for step in range(abs(offset) + 1)
                ],
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


def queneau_ordinal(state: list[int], lang: Lang = "en") -> int:
    """Which of the poems this one is, counting from one.

    A state is a mixed-radix numeral and the book is its own index: with ten
    alternatives at each of fourteen positions, the fourteen indices *are* the
    digits of a number between 1 and 10^14, and that number is the poem's place
    in the total the scene prints beside it. Computed as mixed-radix rather than
    assuming ten, so it stays right if a position ever offers a different count
    — the same rule `queneau_combinations` follows for the total itself.

    This is what makes the count on this scene something other than a boast. A
    hundred million million is not a quantity anybody has an intuition for; a
    fourteen-digit address that changes under your hand when you flip one strip
    is the same fact, arrived at by turning it.
    """
    ordinal = 0
    for index, options in zip(state, queneau_offered(lang), strict=True):
        ordinal = ordinal * len(options) + index
    return ordinal + 1


def queneau_address(state: list[int]) -> list[str]:
    """The state's own digits, grouped the way the sonnet is.

    Four, four, three and three — Queneau's ABAB ABAB CCD EED, so the address
    is broken where the poem is. Digits rather than a single run because the
    point of it is that one flip changes one digit, and a reader should be able
    to see which.
    """
    digits = "".join(str(index) for index in state)
    cuts = (4, 8, 11)
    edges = (0, *cuts, len(digits))
    return [digits[start:end] for start, end in pairwise(edges) if digits[start:end]]


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
# Gysin and Burroughs, Minutes to Go (1960): two straight cuts divide the page
# into four, the quarters are rearranged, and you read across the join.
# `cut_up`'s checker verifies provenance — every word in the result must have
# come from the source, counted with multiplicity
# (`denckring/procedures/cut_up.py`) — and a quadrant rearrangement is a
# provenance-preserving permutation, so a clean cut satisfies it. Put a blade
# *through* a word instead of between two and the pieces are not words any
# more, and the checker names every one of them. Both measured; see the task
# report. That is the whole scene, and it is why nothing here shuffles: the
# cut is made in the browser, by hand, and the server only ever checks what
# the page ended up showing (see `stage_cut_up_act`).

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


# ── scene four's second page, and the family it belongs to ─────────────────

#: The other page the fold-in needs, and the only text on this scene that is
#: quoted rather than written for it. Melville, 1851, public domain — the same
#: passage the N+7 scene offers, so the stage quotes one book once.
#:
#: Six lines, because the fold reads line against line and a page with more of
#: them would simply have its tail folded against nothing (`fold_in._fold_in`
#: stops at the shorter page). Nothing else about it is tuned: the halves fall
#: where each line's own word count puts them.
CUT_UP_SOURCE_B = """Call me Ishmael. Some years ago, never
mind how long precisely, having little
or no money in my purse, and nothing
particular to interest me on shore, I
thought I would sail about a little and
see the watery part of the world."""


def fold_in_source() -> str:
    """The two pages as `fold_in` wants them: one string, two paragraphs.

    `FoldIn._pages` reads page one and page two off `paragraph_spans`, so the
    blank line between them is the whole of the interface — there is no
    two-argument form to call instead.
    """
    return CUT_UP_SOURCE + "\n\n" + CUT_UP_SOURCE_B


@dataclass(frozen=True)
class CutMethod:
    """One operation in the cut-up family, as the scene offers it."""

    id: str
    label: str
    #: The catalogued procedure this method *is*, or None where the catalogue
    #: records that there is nothing to check. Never a near-enough stand-in:
    #: checking a word bag against `cut_up` would be a verdict about a
    #: different method.
    procedure: str | None
    how: str
    #: What the button that performs it says. Four operations, four verbs —
    #: "Cut it" over a fold or a bag would name the wrong act.
    verb: str
    #: Where the method comes from. Shown as the scene's credit, which follows
    #: the method rather than the scene — the four are four attributions.
    credit: str


#: The four, in the order the scene offers them: the one everybody names
#: first, then the one Burroughs put beside it, then the one that came before
#: both, then the one that cuts nothing at all.
#:
#: Three carry a checker and one does not, and that asymmetry is the most
#: interesting thing on the scene. `dada_poem` is catalogued
#: `checkability: none` — a bag of words drawn at random has no property a
#: report could hold a text against, because *any* order is a correct draw.
#: The scene says so where the other three show a verdict, rather than
#: quietly checking it against something else.
CUT_METHODS: tuple[CutMethod, ...] = (
    CutMethod(
        id="quarter",
        label="Quarter cut",
        procedure="cut_up",
        how=(
            "Two straight cuts divide the page into four. The quarters are rearranged "
            "— the bottom-right takes the top-left corner — and you read across the join."
        ),
        verb="Cut it",
        credit="Written for this scene.",
    ),
    CutMethod(
        id="fold",
        label="Fold-in",
        procedure="fold_in",
        how=(
            "A page is folded down its length and laid on another, so the left half of "
            "one line meets the right half of the other. Half of each line is folded "
            "under and gone; that loss is the form, not a defect."
        ),
        verb="Fold it",
        credit="Page A written for this scene. Page B: Melville, Moby-Dick, 1851, public domain.",
    ),
    CutMethod(
        id="bag",
        label="Word bag",
        procedure=None,
        how=(
            "Cut the page into single words, shake them in a bag, and copy them down in "
            "the order they come out. Every order is a correct draw, so there is nothing "
            "for a checker to hold this against."
        ),
        verb="Shake the bag",
        credit="Written for this scene. The method: Tzara, Pour faire un poème dadaïste, 1920.",
    ),
    CutMethod(
        id="column",
        label="Column reading",
        procedure="column_reading",
        how=(
            "Leave every word where it is and read the page down instead of across: the "
            "nth word of every line, in line order. The rule that moves least and reads "
            "most differently."
        ),
        verb="Read it down",
        credit="Written for this scene.",
    ),
)


def cut_up_column(value: str) -> int:
    """Narrow a posted column to one the page actually has a word at.

    Clamped, like `n_plus_7_offset`, and to the same end: the control cannot
    post anything else, so anything else was typed by hand. The upper bound is
    the *longest* line's word count rather than the shortest — `column_reading`
    skips a line too short to reach rather than padding it, so a column past
    some lines is a real reading of this page, and only a column past every
    line reads nothing at all.
    """
    try:
        column = int(value)
    except ValueError:
        return 1
    return max(1, min(cut_up_max_column(), column))


def cut_up_max_column(source: str = CUT_UP_SOURCE) -> int:
    """The last column any line of `source` reaches.

    Computed, never typed: the page is six lines of running English and the
    number is whatever they happen to be. Whitespace-split, because that is
    what `column_reading` itself counts by.
    """
    return max((len(line.split()) for _, line in line_spans(source)), default=1)


def cut_method(method_id: str | None) -> CutMethod:
    """The method `method_id` names, or the quarter cut.

    Falls back rather than refusing, for the reason `n_plus_7_offset` clamps:
    the picker cannot post anything else, so anything else is hand-typed and
    the honest answer is the scene's own default.
    """
    for method in CUT_METHODS:
        if method.id == method_id:
            return method
    return CUT_METHODS[0]


def cut_up_source_words(source: str, lang: Lang = "en") -> list[str]:
    """`source`'s own words, in `word_spans` order — the same call
    `cut_up.check` itself makes. This is state one, "the page, uncut": the
    47 words the four quarters divide between them, whatever the blades do,
    and the list a fragment like "noth" is provably not in."""
    return [word for _, word in word_spans(source, get_pack(lang))]


@dataclass(frozen=True)
class CutUpToken:
    """One piece of a source line: either a word `word_spans` found, or the
    literal gap (space or punctuation) between two of them.

    `source_index` is only meaningful on a word token — the same global
    index `cut_up_source_words` carries, so a word on the page can be named
    by the position `word_spans` gave it. `None` on a gap token.
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
    breaks intact — while still giving every word a span of its own.

    Those spans are load-bearing rather than decorative: the client reads
    their character extents to decide whether the vertical blade landed in a
    gap or inside a word, so "where a word ends" is settled by the same
    `word_spans` call the checker makes and never by re-tokenising in
    JavaScript (see `cut_up_source_words`, whose flat order this function's
    own running `index` reproduces line by line; a test pins the two against
    each other).
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


# ── scene seven: Llull's rotating figure ─────────────────────────────────────
# Ramon Llull, Ars generalis ultima (1305-08): nine letters, B to K — J is
# skipped — each carrying six tables at once. Turning three concentric wheels
# aligns one letter across all of them; the same chamber of letters reads six
# different ways depending on which table is consulted. This is the ancestor
# of scene one — both are volvelles, and the catalogue's own `ars_combinatoria`
# row lists `llull_figure` and `denckring` as its instances.

#: The one figure this scene ever reads. `figure` is a real parameter of
#: `llull_figure` — the procedure can read any shipped figure — but this
#: scene only ever turns the wheels of its one, so the id is a constant here
#: rather than a control on the page.
LLULL_FIGURE_ID = "llull_ternary"

#: The only two arities this scene's own toggle offers, narrowed the same way
#: `queneau_lang` narrows a strip-set request to a value the picker actually
#: sends, so a stale or hand-crafted request can never reach `Figure.chambers`
#: as anything else.
LLULL_ARITIES: tuple[int, ...] = (3, 2)

#: The six tables, in the order the brief's own comparison sets them out — not
#: `Figure.level_names()`'s alphabetical order (`absolute, questions,
#: relative, subjects, vices, virtues`), which would split the two principle
#: tables apart and read as a shuffled deck rather than the brief's own table.
LLULL_LEVELS: tuple[str, ...] = (
    "absolute",
    "relative",
    "questions",
    "subjects",
    "virtues",
    "vices",
)

#: English glosses for every letter at every level — collated against the
#: Stanford Encyclopedia of Philosophy's own table (see the task's
#: `primary-source.md`) and held here, not in the library's figure YAML:
#: `apply`/`check` read the Latin names alone, and an unused `gloss` field on
#: published data would raise a question ("which language? does `check`
#: accept a gloss?") this task is not scoped to answer. A test asserts this
#: table covers exactly the figure's own nine letters at all six levels, so a
#: future change to the figure data cannot silently leave a term untranslated.
LLULL_GLOSSES: dict[str, dict[str, str]] = {
    "absolute": {
        "B": "goodness",
        "C": "greatness",
        "D": "eternity",
        "E": "power",
        "F": "wisdom",
        "G": "will",
        "H": "virtue",
        "I": "truth",
        "K": "glory",
    },
    "relative": {
        "B": "difference",
        "C": "concordance",
        "D": "contrariety",
        "E": "beginning",
        "F": "middle",
        "G": "end",
        "H": "majority",
        "I": "equality",
        "K": "minority",
    },
    "questions": {
        "B": "whether?",
        "C": "what?",
        "D": "of what?",
        "E": "why?",
        "F": "how much?",
        "G": "of what quality?",
        "H": "when?",
        "I": "where?",
        "K": "how, and with what?",
    },
    "subjects": {
        "B": "God",
        "C": "angel",
        "D": "heaven",
        "E": "man",
        "F": "the imaginative",
        "G": "the sensitive",
        "H": "the vegetative",
        "I": "the elemental",
        "K": "the instrumental",
    },
    "virtues": {
        "B": "justice",
        "C": "prudence",
        "D": "fortitude",
        "E": "temperance",
        "F": "faith",
        "G": "hope",
        "H": "charity",
        "I": "patience",
        "K": "compassion",
    },
    "vices": {
        "B": "avarice",
        "C": "gluttony",
        "D": "lust",
        "E": "pride",
        "F": "sloth",
        "G": "envy",
        "H": "wrath",
        "I": "lying",
        "K": "inconstancy",
    },
}


def llull_figure_data() -> device.Figure:
    """The one figure this scene reads — cached by the library itself
    (`device.load_figure`'s own `lru_cache`), so calling this freely costs
    nothing."""
    return device.load_figure(LLULL_FIGURE_ID)


def llull_alphabet() -> list[str]:
    """The figure's own nine letters, B to K, in the fixed order every wheel
    carries them — every wheel shows the same alphabet; a chamber is which
    letter each wheel shows, not where in its own ring that letter sits."""
    return list(llull_figure_data().letters)


def llull_arity(value: str) -> int:
    """Narrow a request string to an arity this scene's own toggle actually
    offers — 3 for anything else, the same fallback `queneau_lang` gives an
    unrecognised strip set."""
    try:
        parsed = int(value)
    except ValueError:
        return 3
    return parsed if parsed in LLULL_ARITIES else 3


@dataclass(frozen=True)
class LlullTerm:
    """One letter of a chamber, read at one level: the Latin the figure's own
    data carries, and the English gloss `LLULL_GLOSSES` holds beside it."""

    letter: str
    latin: str
    gloss: str


@dataclass(frozen=True)
class LlullReading:
    """One table's own reading of a chamber — one term per letter, in
    chamber order."""

    level: str
    terms: list[LlullTerm]


@dataclass(frozen=True)
class LlullChamber:
    """A chamber, prepared for the page: the letters the wheels show, and the
    readings each of `LLULL_LEVELS` gives them. Carries no verdict of its
    own — `app.py` calls a real `check()` against `.text`, the same
    "prepare here, check there" split every other scene's own route keeps."""

    letters: list[str]
    arity: int
    readings: list[LlullReading]

    @property
    def text(self) -> str:
        """The chamber exactly as the wheels show it — what `check` reads.
        Bare letters, not one of the six spelled-out readings: the verdict
        this earns is the wheels' own claim, not a claim about any one
        table."""
        return "".join(self.letters)


def llull_readings(letters: list[str]) -> list[LlullReading]:
    """`letters`, read at each of `LLULL_LEVELS` in turn — the six-ways-at-
    once the scene exists to show. Works even when `letters` repeats one (a
    hand-turned chamber can): each position is looked up on its own, so a
    repeated letter simply repeats its own row rather than raising."""
    figure = llull_figure_data()
    return [
        LlullReading(
            level=level,
            terms=[
                LlullTerm(
                    letter=letter,
                    latin=figure.levels[level][letter],
                    gloss=LLULL_GLOSSES[level][letter],
                )
                for letter in letters
            ],
        )
        for level in LLULL_LEVELS
    ]


def llull_chamber(letters: list[str], arity: int) -> LlullChamber:
    """One chamber, prepared for the page: its letters and their six
    readings."""
    return LlullChamber(letters=letters, arity=arity, readings=llull_readings(letters))


def llull_positions(letters: list[str]) -> list[int]:
    """Each letter's own true index on a wheel — every wheel carries the
    figure's full nine-letter alphabet in the same order (`figure.letters`),
    so a wheel is positioned by this index, never by searching a wheel's own
    parts for matching text. The same rule `pieces_for` keeps for the
    Denckring's own rings (`endbuchstabe` repeats two of its 120 parts, so a
    ring positioned by matching text can only ever land on the first
    occurrence) — nothing on this figure's nine letters repeats, but the rule
    the client script follows is the same rule either way, not a coincidence
    that happens to also hold here."""
    figure = llull_figure_data()
    return [figure.letters.index(letter) for letter in letters]


def llull_default_letters(arity: int) -> list[str]:
    """First paint: the alphabet's own first chamber — B, C[, D] —
    deterministic, the way every other scene's own first paint is (see
    `DEFAULT_WORD`, `queneau_initial_state`), rather than a draw a test would
    have to pin against randomness."""
    figure = llull_figure_data()
    return list(figure.chambers(arity)[0])


def llull_random_letters(arity: int, rng: random.Random | None = None) -> list[str]:
    """Turn the wheels: one of the figure's own registered chambers at
    `arity`, drawn at random — always `arity` distinct letters, by
    construction (`Figure.chambers` is `itertools.combinations`)."""
    figure = llull_figure_data()
    chooser = rng if rng is not None else random.Random()
    return list(chooser.choice(figure.chambers(arity)))


def llull_letters_from_text(text: str) -> list[str] | None:
    """Parse a hand-turned chamber back from the wheels' own hidden field —
    the letters exactly as the discs show them, duplicates and all: a hand
    turn can land two wheels on the same letter, and that is a real chamber
    `check` correctly refuses, not a state this parser should hide. `None`
    for anything that is not letters drawn from the figure's own alphabet —
    a stale or hand-crafted request, never one this page's own script
    sends."""
    figure = llull_figure_data()
    letters = [ch for ch in text.upper() if ch.isalpha()]
    if not letters or any(letter not in figure.letters for letter in letters):
        return None
    return letters


def llull_prompt_alphabet() -> str:
    """The figure's whole alphabet as one block of text, for `ars.py`.

    Prepared here, from the shipped figure and the shipped glosses, rather than
    written into the prompt: the terms a model argues from have to be the ones
    the scene beside it reads off the same YAML, or the reading and the figure
    are describing two different devices. The Latin is the figure's own; the
    English is the gloss table `LLULL_GLOSSES` holds.
    """
    figure = llull_figure_data()
    lines = []
    for level in LLULL_LEVELS:
        terms = ", ".join(
            f"{letter} = {figure.levels[level][letter]} ({LLULL_GLOSSES[level][letter]})"
            for letter in figure.letters
        )
        lines.append(f"{level.upper()}: {terms}")
    return "\n".join(lines)


def llull_client_data() -> dict[str, Any]:
    """Every letter's Latin and English at every level, as one JSON-ready
    structure — embedded once on the page so a held wheel can redraw the
    reading panel locally, on every step, without a round trip for each one.
    A held control repeats roughly five times a second (see the task report
    for the measured rate); a real network request per step would leave the
    panel chasing a queue of stale responses rather than showing the wheel
    actually on screen right now. The verdict is never approximated this
    way — it always comes from a real `check()` call, deferred to release;
    see the scene's own script."""
    figure = llull_figure_data()
    return {
        "levels": {
            level: {
                letter: {
                    "latin": figure.levels[level][letter],
                    "gloss": LLULL_GLOSSES[level][letter],
                }
                for letter in figure.letters
            }
            for level in LLULL_LEVELS
        },
        "levelOrder": list(LLULL_LEVELS),
    }


# ── scene eight: Enzensberger's Poesie-Automat ────────────────────────────────
# Hans Magnus Enzensberger, "Einladung zu einem Poesie-Automaten" (conceived
# 1974); the machine was built for *Lyrik am Lech* and stood in Landsberg am
# Lech from 30 June to 2 July 2000. It is an electromechanical split-flap
# display of the railway-platform kind: six lines of six modules, ten flaps
# each, so one press of the button composes one of 10^36 poems.
#
# The board renders **letter by letter into character cells** — Enzensberger's
# own description, and what every split-flap display in the field does. A line
# costs six flaps plus the five spaces between them, no flap is wider than
# eleven characters, and so a line is at most 71 columns. That figure is the
# whole geometry of the scene and it is derived here rather than quoted.
#
# The board is data and the data is not Enzensberger's — he died in 2022 and
# his word lists are in copyright until 2092. The 360 fillers in
# `denckring/data/devices/poesieautomat_2000.yaml` were written for this
# project; the catalogue row and the device file both say so, and so does the
# scene's own credit line.

#: The row is `languages: [de]`, so there is no toggle and nothing to narrow.
POESIE_AUTOMAT_LANG: Lang = "de"

#: Character cells per line, and the cap on one flap that produces it: six
#: flaps of at most eleven characters, plus the five spaces between them. Both
#: cartridges are written to the same cap, so both play on the same board.
#: `test_no_flap_is_wider_than_the_board` in the root suite holds the packaged
#: device to it and `test_both_cartridges_fit_the_same_71_column_board` holds
#: the explorer's own.
FLAP_CAP = 11
BOARD_COLUMNS = 71

#: What a cell shows in place of nothing. A real board's unset flap is blank,
#: and blank is a position on the drum like any other — it is the first
#: character of the alphabet below, so a cell can roll to it and away from it.
BLANK = " "

# What stands between two modules on a line is the procedure's own `SEPARATOR`,
# imported at the top of this file rather than retyped: a board whose flaps ever
# ran together without a space would otherwise leave this module reading the
# device differently from the checker that judges it.


#: The machine, which is Enzensberger's whichever cartridge is in it, and is
#: credited identically on both. Only the lexicon changes, and only the lexicon
#: half of the attribution changes with it.
POESIE_AUTOMAT_MACHINE = "Hans Magnus Enzensberger \u00b7 Landsberger Poesieautomat, 2000"


@dataclass(frozen=True)
class Cartridge:
    """One set of flaps this scene can load into the board.

    `device_id` is the only thing that reaches the library; everything else is
    the page's. A cartridge is *named here* rather than accepted from the
    client, so the switcher cannot be pointed at an arbitrary device by editing
    a form value — see `automat_cartridge`.

    `lexicon` and `credit` are the attribution, and they belong to the
    cartridge rather than to the scene because **the words are not the
    machine's**. The scene shipped for one round with a fixed eyebrow reading
    `Hans Magnus Enzensberger · Landsberger Poesieautomat, 2000` over whichever
    cartridge was loaded, so with the Pokemon flaps on the board the page
    credited Enzensberger for a lexicon that is not his and that he would not
    recognise. Every other scene's credit describes what is actually on screen;
    this one now does too.
    """

    device_id: str
    label: str
    note: str
    #: Whose words these are, in a few words — the second half of the eyebrow.
    lexicon: str
    #: The footnote under the panel, in full.
    credit: str

    @property
    def kicker(self) -> str:
        """The eyebrow: the machine, then the lexicon.

        The machine half is identical on both cartridges because the mechanism
        really is Enzensberger's in both cases. The lexicon half is what has to
        differ, and `test_the_credit_follows_the_cartridge` fails if the whole
        line comes out the same for two cartridges.
        """
        return f"{POESIE_AUTOMAT_MACHINE} \u00b7 {self.lexicon}"


#: The two sets of flaps, in the order the switcher shows them. The first is
#: the machine that actually stood in Landsberg and is what the scene opens on.
#:
#: The second lives under `apps/explorer` and is found through
#: `DENCKRING_DEVICE_PATH` (see `explorer.env`), never through the packaged
#: device directory: its subjects are Pokemon creature names, which are
#: third-party trademarks, and the catalogue's data ships under CC BY 4.0. The
#: device file's own header carries that reasoning at length.
AUTOMAT_CARTRIDGES = (
    Cartridge(
        device_id="poesieautomat_2000",
        label="Landsberg 2000",
        note="the machine's own flaps",
        lexicon="360 flaps written for this project",
        credit=(
            "Enzensberger's mechanism, not his words. He died in 2022 and his lists are in "
            "copyright until 2092, so the 360 flaps on this cartridge were written for this "
            "project; the catalogue's poesie_automat row and the device file both say so."
        ),
    ),
    Cartridge(
        device_id="poesieautomat_pokemon",
        label="Pokémon-Kassette",
        note="a second cartridge, explorer-only",
        lexicon="Pokémon flaps, the explorer's own",
        # Kept to four rendered lines. At five it took the scene's content
        # extent to 684.72px against the 720px the stage has, a tighter margin
        # than any other scene runs — the tightest, `cent_mille_milliards`,
        # sits at 679.28px. The Landsberg credit beside this one renders three
        # lines and 654.97px; this one renders four and 669.84px, so the extent
        # is cartridge-dependent. `flap-board.mjs widths` gates the blank at
        # 40px for exactly that reason. (An earlier version of this comment
        # said three and four; both were off by one, measured off the rendered
        # box at a 14.88px line height.)
        credit=(
            "Enzensberger's mechanism; the words are neither his nor Müller's. The subjects "
            "are German Pokémon names — third-party trademarks, which is why this cartridge "
            "is explorer-only and never packaged. The rest is Heiner Müller's register (he "
            "died in 1995) as individual common words, not anything he wrote."
        ),
    ),
)

#: What the scene opens on, and what a request naming no cartridge gets.
POESIE_AUTOMAT_DEVICE = AUTOMAT_CARTRIDGES[0].device_id


def automat_cartridge(device_id: str | None) -> Cartridge:
    """The cartridge `device_id` names, or the default.

    An id the scene does not offer is refused rather than passed through to
    `device.load`. The switcher is a control on a page and its value arrives
    from a client, and `device.load` will happily read any YAML file sitting in
    a directory on the search path — so the set of loadable boards is fixed
    here, in the server, where a client cannot widen it.
    """
    for cartridge in AUTOMAT_CARTRIDGES:
        if cartridge.device_id == device_id:
            return cartridge
    if device_id is None or device_id == "":
        return AUTOMAT_CARTRIDGES[0]
    raise InvalidParams(
        "poesie_automat",
        f"{device_id!r} is not a cartridge this scene carries; "
        f"try one of {[c.device_id for c in AUTOMAT_CARTRIDGES]}",
    )


@dataclass(frozen=True)
class FlapModule:
    """One module of the board: ten flaps, and where they will stand.

    `name` is the module's own part of speech from the device file
    (`Zeitangabe`, `Adverb`, five different `Adjunkt`s on one line), which is
    why nothing addresses a module by name — the position within the line is
    the identity, here and in the scene's own markup.

    `alternatives` are the device's own strings and `flaps` are the same
    strings as the board shows them, in capitals. Both are kept: the capitals
    are what goes into the cells and therefore what is checked, and the
    device's own case is what a screen reader is given.
    """

    name: str
    alternatives: list[str]

    @property
    def flaps(self) -> list[str]:
        return [automat_display(alternative) for alternative in self.alternatives]


@dataclass(frozen=True)
class FlapLine:
    """One line of the board: its number, 0-5, and its six modules in order."""

    number: int
    modules: list[FlapModule]


@dataclass(frozen=True)
class FlapBoard:
    """The whole board, and the count it admits."""

    lines: list[FlapLine]
    #: `Device.combinations`, an exact `int`. Never `metrics["combinations"]`,
    #: which is the same number through a float and comes out `1e+36`.
    combinations: int

    @property
    def modules(self) -> list[FlapModule]:
        """Every module in slot order — the order `positions` is indexed in."""
        return [module for line in self.lines for module in line.modules]


def flap_board(device_id: str | None = None) -> FlapBoard:
    """The board as the named cartridge has it."""
    machine = device.load(automat_cartridge(device_id).device_id)
    return FlapBoard(
        lines=[
            FlapLine(
                number=number,
                modules=[
                    FlapModule(name=slot.name, alternatives=list(slot.alternatives))
                    for slot in machine.for_line(number).slots
                ],
            )
            for number in machine.lines
        ],
        combinations=machine.combinations,
    )


def automat_display(text: str) -> str:
    """`text` as the board shows it: capitals, and the same number of columns.

    `"ß".upper()` is `"SS"` — two characters — which would make a flap wider on
    the board than it is in the device file and push a line past its column
    count. So the sharp s becomes the capital sharp s, U+1E9E, which is one
    character and is what German capital-setting does. It costs nothing at the
    other end: `"ẞ".casefold()` and `"ß".casefold()` are both `"ss"`, so a
    board showing `REGELMÄẞIG` submits a word `check` still reads as
    `regelmäßig` — which is the whole requirement, that what is checked is what
    is on screen. `test_the_board_shows_capitals_without_widening_a_flap` pins
    both halves.
    """
    return text.replace("ß", "ẞ").upper()


def automat_alphabet(device_id: str | None = None) -> str:
    """Every character the named cartridge's flaps can put in a cell, in order.

    Computed from the device rather than assumed: the packaged board's fillers
    contain no C, Q, X or Y and the Pokemon cartridge's do, so a hardcoded A-Z
    would give both boards drums with characters on them that no flap can ever
    ask for — and the roll between two characters passes through every
    character in between, so the alphabet is not decoration, it is what the
    animation walks.

    Blank first, because a blank is where a cell rests when its line's text
    does not reach it, and because a space sorts first by code point anyway —
    the ordering is `sorted`, not a table, so a filler that ever introduced a
    hyphen or a digit would take its place in it without this function being
    edited.
    """
    machine = device.load(automat_cartridge(device_id).device_id)
    characters = {BLANK}
    for slot in machine.slots:
        for alternative in slot.alternatives:
            characters.update(automat_display(alternative))
    return "".join(sorted(characters))


def automat_line(flaps: list[str]) -> tuple[str, list[tuple[int, int]]]:
    """One line's 71 cells, and which cells each of its six modules owns.

    The six flaps are joined by the separator `check` itself walks and the
    result is centred in the board — a real letter board writes a string into
    a row of cells, and a poem centred in the row is what that looks like. A
    module's flap is a run of consecutive cells inside it, and the run moves
    when a neighbouring module turns to a longer or shorter flap, which is why
    the spans are computed here for whatever the board is showing rather than
    fixed once.

    Returns the row exactly `BOARD_COLUMNS` wide. A line the modules cannot
    fit is a device that broke the cap, and it is refused rather than clipped:
    a board silently dropping the end of a line is the failure this whole
    geometry exists to prevent.
    """
    text = POESIE_AUTOMAT_SEPARATOR.join(flaps)
    if len(text) > BOARD_COLUMNS:
        raise InvalidParams(
            "poesie_automat",
            f"{text!r} needs {len(text)} columns and the board has {BOARD_COLUMNS}",
        )
    # Padded by hand rather than by `str.center`, and that is not fussiness:
    # CPython's `center` puts the odd extra space on the *left* when both the
    # margin and the width are odd (`left = marg // 2 + (marg & width & 1)`),
    # and the board is 71 columns wide. The client centres the same line as
    # flaps turn and does it with a plain floor, so a row laid out here would
    # have sat one cell off from the same row laid out there for every flap of
    # odd length. `test_the_board_lays_out_a_row_the_same_on_both_sides` walks
    # every flap of every module through both.
    left = (BOARD_COLUMNS - len(text)) // 2
    spans: list[tuple[int, int]] = []
    at = left
    for flap in flaps:
        spans.append((at, len(flap)))
        at += len(flap) + len(POESIE_AUTOMAT_SEPARATOR)
    return BLANK * left + text + BLANK * (BOARD_COLUMNS - left - len(text)), spans


@dataclass(frozen=True)
class BoardRow:
    """What one line of the board is showing: 71 characters and six spans."""

    number: int
    cells: str
    spans: list[tuple[int, int]]


def automat_rows(board: FlapBoard, positions: list[int]) -> list[BoardRow]:
    """The six rows of cells those 36 flaps spell, ready to render.

    The server's own first paint goes through here, and so does every
    measurement a test makes of it — the client recomputes the same rows as
    flaps turn, and `test_the_board_lays_out_the_same_row_in_both_languages`
    holds the two implementations to the same answer.
    """
    flaps = iter(positions)
    rows: list[BoardRow] = []
    for line in board.lines:
        showing = [module.flaps[next(flaps)] for module in line.modules]
        cells, spans = automat_line(showing)
        rows.append(BoardRow(number=line.number, cells=cells, spans=spans))
    return rows


def automat_payload(cartridge: Cartridge) -> dict[str, Any]:
    """Everything the page needs to drive one cartridge, as plain JSON.

    Both cartridges are handed over at first paint and the switcher is then a
    local swap. That is a deliberate choice and it is what makes the swap read
    as *loading different flaps into the same machine*: the 426 cells are
    already on the page and stay there, and what changes is which words the
    modules can show. The check that follows is still a real round trip against
    the device the board is now showing — see `stage_poesie_automat_act`.

    Flaps go over in capitals, which is what the cells display and therefore
    what is submitted; the device's own case goes over beside them for the
    accessible tree. Nothing here sends a poem: the client composes rows out of
    flap indices exactly as `automat_rows` does.
    """
    board = flap_board(cartridge.device_id)
    return {
        "id": cartridge.device_id,
        "label": cartridge.label,
        "note": cartridge.note,
        # The attribution travels with the flaps, because the switcher changes
        # the board without a round trip and a credit left behind would be
        # describing the previous cartridge.
        "kicker": cartridge.kicker,
        "credit": cartridge.credit,
        "columns": BOARD_COLUMNS,
        "alphabet": automat_alphabet(cartridge.device_id),
        "exponent": power_of_ten(board.combinations),
        "combinations": f"{board.combinations:,}",
        "lines": [[module.name for module in line.modules] for line in board.lines],
        "modules": [
            {
                "line": line.number,
                "name": module.name,
                "flaps": module.flaps,
                "words": module.alternatives,
            }
            for line in board.lines
            for module in line.modules
        ],
        "positions": automat_default_positions(cartridge.device_id),
    }


def power_of_ten(count: int) -> int | None:
    """`count` as an exponent of ten, or `None` if it is not one.

    The board's own count is 10^36 exactly, and thirty-seven digits on a
    stage read as a smear rather than a number — so the page renders it as a
    power. This asks whether that rendering is *true* of the count it was
    given rather than assuming it: a board whose modules were ever edited to
    something other than ten alternatives would fall out of this and the page
    would print the digits instead of a power that had quietly become a lie.
    """
    if count <= 0:
        return None
    exponent = len(str(count)) - 1
    return exponent if 10**exponent == count else None


def automat_positions(poem: str, device_id: str | None = None) -> list[int] | None:
    """The 36 flap indices that spell `poem`, one per module in slot order, or
    `None` if the board cannot show it.

    An *index* per module, never the flap's text: the same rule `pieces_for`
    keeps for the Denckring's rings and `llull_positions` for Llull's wheels.
    Nothing on either board repeats a flap within a module (a test pins that),
    so a text lookup would in fact land right here today — the rule is the
    rule either way, and the client is handed the number the server already
    worked out rather than a string to go searching for.

    Built on the same `device.segment` walk `poesie_automat._reading` makes,
    with the procedure's own separator, so a poem this accepts is exactly a
    poem `check` accepts. Case is folded inside `segment`, so the board's own
    capitals read back as the device's mixed case.
    """
    machine = device.load(automat_cartridge(device_id).device_id)
    found = line_spans(poem)
    if len(found) != len(machine.lines):
        return None
    positions: list[int] = []
    for number, (_, line) in zip(machine.lines, found, strict=True):
        board = machine.for_line(number)
        pieces = device.segment(
            POESIE_AUTOMAT_SEPARATOR.join(line.split()),
            board,
            separator=POESIE_AUTOMAT_SEPARATOR,
        )
        if pieces is None:
            return None
        for slot, piece in zip(board.slots, pieces, strict=True):
            positions.append(slot.alternatives.index(piece))
    return positions


def automat_poem(positions: list[int], device_id: str | None = None) -> str:
    """The poem those 36 flaps spell, as six lines, in the device's own case.

    The inverse of `automat_positions`. What the *cells* show is this run
    through `automat_display` and centred (see `automat_rows`); this is the
    poem itself, which is what a first-paint `check()` is asked about.

    Every flap index is checked against its own module rather than folded into
    range: a `10` on a ten-flap drum is a caller that has miscounted, and
    rendering flap 0 for it would turn that into a poem that looks fine and is
    about a board nobody asked for.
    """
    machine = device.load(automat_cartridge(device_id).device_id)
    if len(positions) != len(machine.slots):
        raise InvalidParams(
            "poesie_automat",
            f"the board has {len(machine.slots)} modules, not {len(positions)} flaps",
        )
    for slot, flap in zip(machine.slots, positions, strict=True):
        if not 0 <= flap < len(slot.alternatives):
            raise InvalidParams(
                "poesie_automat",
                f"module {slot.name!r} on line {slot.line + 1} has "
                f"{len(slot.alternatives)} flaps, so there is no flap {flap}",
            )
    flaps = iter(positions)
    return "\n".join(
        POESIE_AUTOMAT_SEPARATOR.join(
            slot.alternatives[next(flaps)] for slot in machine.for_line(number).slots
        )
        for number in machine.lines
    )


def automat_default_positions(device_id: str | None = None) -> list[int]:
    """First paint: every module on its own first flap.

    Deterministic, the way every other scene's first paint is (see
    `llull_default_letters`, `queneau_initial_state`) — the recording starts
    from a board at rest, and pressing the button is the thing a viewer does,
    not something the page has already done for them. A cartridge swap lands on
    the same resting board for the same reason.
    """
    machine = device.load(automat_cartridge(device_id).device_id)
    return [0] * len(machine.slots)


def automat_press(device_id: str | None = None, seed: int | None = None) -> tuple[str, list[int]]:
    """Press the button: the poem the library's own `apply` composes, and the
    36 flaps that spell it.

    `apply` is what makes the choice — this scene demonstrates the procedure,
    so the poem is the procedure's, not a draw made here. The flaps come back
    from reading that poem against the board, which is the only way the client
    can be told where to send its cells; the *verdict* is never taken from
    here, it is a separate `check()` of the text read back off the cells once
    they have stopped (see the scene's own script and `stage_poesie_automat`'s
    two branches).
    """
    cartridge = automat_cartridge(device_id)
    procedure = get("poesie_automat")
    assert isinstance(procedure, Constructive)
    poem = procedure.apply("", lang=POESIE_AUTOMAT_LANG, seed=seed, device=cartridge.device_id)
    positions = automat_positions(poem, cartridge.device_id)
    if positions is None:
        # Unreachable by construction: `apply` selects one alternative per
        # module and joins them with the same separator `automat_positions`
        # walks. Raised rather than silently defaulted, because a board that
        # cannot read back its own output is a broken device file, not a case
        # the scene should paper over.
        raise InvalidParams("poesie_automat", f"the board cannot read back its own poem: {poem!r}")
    return poem, positions


# ── the readings' arithmetic ────────────────────────────────────────────────
#
# Every number a companion page states, computed here from the same data the
# scene beside it runs on. They are gathered rather than scattered so that the
# whole of what those pages assert numerically can be read in one screen and
# audited against the device files.
#
# The rule is ADR 0019's — *counts are computed, never quoted* — and prose is
# where it is easiest to break, because a figure set in a sentence looks
# settled in a way the same figure in a legend does not. The four mockups these
# pages are drawn from break it in exactly that way: one of them multiplies the
# Denckring's printed caption out to "roughly 83 million words" and calls the
# plate's inventory 254 parts, both of which are arithmetic on numbers
# Harsdörffer printed rather than on the parts the transcription carries.


def ring_parts() -> int:
    """How many word-parts the shipped transcription of the Denckring carries.

    264, and it is worth saying why the figure has to be computed rather than
    read off Harsdörffer's own caption. The plate announces 48 · 60 · 12 · 120 ·
    24, which sums to 264 as well — but the transcription carries 49 · 60 · 12 ·
    120 · 23, and the two agree on the total only by accident, disagreeing about
    where the boundary between the prefix and suffix rings falls (ADR 0017,
    which records both and adjusts neither). A page that typed 264 would be
    right today and silently wrong the moment either count moved.
    """
    return sum(len(slot.alternatives) for slot in rings().slots)


def queneau_inventory(lang: Lang = "en") -> tuple[int, int]:
    """`(positions, lines actually written)` for a set of strips.

    The second number is the one that carries the argument: the machine's
    output is astronomical and its inventory is small enough to print, and the
    gap between them is the whole of Queneau's joke.
    """
    offered = queneau_offered(lang)
    return len(offered), sum(len(alternatives) for alternatives in offered)


#: Minutes in a year, for `years_of_reading`. Named rather than inlined so the
#: assumption behind the figure is visible: 365 days, no leap correction, which
#: is well inside the precision anything on this scale deserves.
MINUTES_IN_A_YEAR = 60 * 24 * 365


def years_of_reading(combinations: int) -> int:
    """How long a set of strips takes to read out at one poem a minute, without
    stopping.

    Queneau's own jacket note makes this move, and it is the reason the book is
    a machine rather than a novelty: the number is only legible once it is
    converted into a span nobody has. Round the clock, deliberately — a figure
    computed against a working day would be larger and would smuggle in an
    assumption about the reader.
    """
    return combinations // MINUTES_IN_A_YEAR


def llull_chamber_counts() -> dict[int, int]:
    """How many chambers each arity the scene offers admits, keyed by arity.

    Falls out of nine letters: 84 of three and 36 of two. ADR 0019 permits
    exactly these two figures on a page and refuses a third that circulates
    with them — the number of entries in the printed *Tabula generalis* — which
    stays unchecked until somebody reads a facsimile.
    """
    figure = llull_figure_data()
    return {arity: len(figure.chambers(arity)) for arity in LLULL_ARITIES}


def automat_inventory(device_id: str | None = None) -> tuple[int, int, int]:
    """`(lines, modules, flaps)` for a cartridge.

    Six, thirty-six and three hundred and sixty on the shipped one. The third
    is what the credit on the scene is counting when it says how much of this
    machine was written for this project rather than taken from Enzensberger.
    """
    board = flap_board(device_id)
    modules = board.modules
    return len(board.lines), len(modules), sum(len(m.alternatives) for m in modules)


#: Which of the seven segments each digit lights, in the standard labelling:
#: `a` top, `b` top-right, `c` bottom-right, `d` bottom, `e` bottom-left,
#: `f` top-left, `g` middle. The template draws these as real polygons and
#: rotates the whole display, so a viewer reads the digits and the letters off
#: the same marks — which is the scene's whole claim, and would be a lie if the
#: letters were substituted text. Rotating swaps a<->d, b<->e, c<->f and fixes
#: g, which is where ADR 0037's table comes from.
SEGMENTS = {
    "0": "abcdef",
    "1": "bc",
    "2": "abdeg",
    "3": "abcdg",
    "4": "bcfg",
    "5": "acdfg",
    "6": "acdefg",
    "7": "abc",
    "8": "abcdefg",
    "9": "abcdfg",
}

#: The digits the scene opens on, and the language they are read in. German
#: because `Esel` is the example the practice is known by here, and because it
#: is the one reading that needs no gloss on a recorded stage.
CALCULATOR_WORD_DEFAULT = "7353"
CALCULATOR_WORD_DEFAULT_LANG: Lang = "de"

#: The languages the scene offers. All three, unlike the word ladder's two: the
#: row declares `[en, de, fr]` and runs in each without new data.
CALCULATOR_WORD_EXAMPLES: dict[Lang, str] = {
    "en": "07734",
    "de": CALCULATOR_WORD_DEFAULT,
    "fr": "713705",
}


@dataclass(frozen=True)
class CalculatorReading:
    """What the display shows, and whether it is a word.

    `problem` is `""` for a real calculator word, `"invalid"` for an entry the
    display cannot read at all (a digit outside the table — `2` shows no
    letter), and `"not_a_word"` when the letters are legible but the language
    does not know them. Three answers rather than one, for the reason
    `Ladder.problem` gives: "the display shows GLOSE and that is not a word" is
    a different and more interesting fact than "you typed a 2".
    """

    digits: str
    word: str
    problem: str
    message: str


def calculator_word(digits: str, lang: Lang = "de") -> CalculatorReading:
    """Decode `digits` and say whether the display's reading is a word.

    Reads `core.calculator` directly rather than going through the procedure,
    which is why that table is not inside the procedure module: a scene must not
    import a procedure's internals, and both need the same eight letters.

    The lexicon is asked here rather than by catching the procedure's own
    exception, the same choice `word_ladder` above makes and for the same
    reason: matching English prose in an error message to tell two failure modes
    apart breaks the moment either wording changes.
    """
    cleaned = digits.strip()
    if not cleaned or not cleaned.isdigit():
        return CalculatorReading(cleaned, "", "invalid", "Type digits to read them back.")
    unreadable = sorted({ch for ch in cleaned if ch not in FROM_DIGIT})
    if unreadable:
        # `2` is rotationally symmetric on a seven-segment display and shows no
        # letter at all — ADR 0037 D2. Named rather than silently dropped, or
        # the reader sees a shorter word than they typed and no reason why.
        shown = " and ".join(unreadable)
        return CalculatorReading(
            cleaned, "", "invalid", f"{shown} shows no letter when the display is turned over."
        )
    word = from_digits(cleaned)
    if not get_pack(lang).is_word(word):
        return CalculatorReading(
            cleaned, word, "not_a_word", f"The display reads {word.upper()}, which is not a word."
        )
    return CalculatorReading(cleaned, word, "", "")


# ---------------------------------------------------------------------------
# scene ten: the street of bad puns
# ---------------------------------------------------------------------------

#: Trades the street can be dressed as, in the order the picker offers them.
#: Read from the library rather than typed, so a domain added to the package
#: appears here without this file changing — the mistake `stage_index` made
#: once by announcing three scenes while rendering six.
STREET_TRADES: tuple[str, ...] = domain.ids()

#: The band the street sweeps, left to right. Not the procedure's default
#: (0.0-0.5): the street's whole argument is that distance is a *dial*, so it
#: opens on the full range and lets the reader close it.
STREET_BAND = (0.0, 1.0)

#: How many houses fit. Five at 1280px leaves each shopfront 232px of fascia,
#: which is the narrowest a sign can be and still set a seven-word phrase at a
#: readable size. Measured against `Site for Sore Eyes`, the longest phrase any
#: shipped trade offers.
STREET_HOUSES = 5


#: The sign styles the shopfront can be painted in. Each is a *look*, not a
#: layout — the drawing is one shopfront either way — so a style can never
#: change what the sign says or whether it checks. That separation is the point:
#: the picture varies, the claim underneath it does not.
SIGN_STYLES: tuple[str, ...] = ("fascia", "hanging", "painted", "neon", "enamel")


@dataclass(frozen=True)
class Shopfront:
    """One shop, and the claim its sign makes."""

    #: What the sign reads.
    sign: str
    #: The phrase or word it was made from, so the joke can be explained below.
    source: str
    #: The word that landed, and the word it pushed out. For a blend the second
    #: is the host, because nothing was pushed out — the host is still there.
    landed: str
    displaced: str
    #: 0.0 is a homophone; 1.0 shares nothing.
    distance: float
    #: Whether the word that landed belongs to the trade whose sign it is.
    in_trade: bool
    #: The checker's verdict, from the row named below. Every sign on this stage
    #: is checked, never assumed: a drawn shopfront is persuasive and the verdict
    #: is not visible in it.
    satisfied: bool
    #: Which row decided it — `paronomasia` for a displacement, `portmanteau`
    #: for a blend. Shown on the scene, because they are different figures and a
    #: reader should be told which one they are looking at.
    figure: str
    #: Which of `SIGN_STYLES` to paint it in.
    style: str
    #: Whether the generator made this sign, rather than it coming from the
    #: shipped data. A separate field and not a suffix on `figure`, which names
    #: the row that checked it: an earlier draft wrote `"portmanteau (invented)"`
    #: and two tests asking whether the figure was a real row went red for a
    #: reason that had nothing to do with them.
    invented: bool = False

    @property
    def is_blend(self) -> bool:
        return self.figure == "portmanteau"

    @property
    def font_size(self) -> float:
        """Type size for the sign, in the shopfront's own viewBox units.

        The board is 560 units wide with room either side for the paint, and the
        display face sets at roughly 0.6 em per character. Capped at 92 so
        `Do or Dye` does not fill the board, floored at 22 so the longest phrase
        any trade ships is legible rather than merely present.
        """
        return max(22.0, min(92.0, 520.0 / (0.6 * max(len(self.sign), 1))))


def street_trade(raw: str | None) -> str:
    """A trade id the street can be dressed as, defaulting to the salon.

    The salon, not the bakery, and the bakery was wrong twice over. This scene
    is titled in German and the punning *Friseursalon* is the best-attested
    habitat the figure has; opening on an English bakery made the title a
    non-sequitur. Worse, `bakery` ships no German — so `de` was not even in the
    language picker until the reader thought to change trade first, which is a
    poor way to hide the one language the scene is named in.
    """
    if raw in STREET_TRADES:
        return str(raw)
    return "hair"


def street_ceiling(raw: str) -> float:
    """The band's upper edge, from a form field, clamped to what the slider offers.

    Narrowed here rather than trusted, for the reason every control on this
    stage is narrowed here: a posted value is a string from outside, and
    `paronomasia` would raise `InvalidParams` on anything above 1.0 — which is
    the right behaviour for the library and the wrong one for a drag that
    overshot. Anything unreadable falls back to the open band, so a broken post
    shows the whole street rather than none of it.
    """
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return STREET_BAND[1]
    return min(max(value, 0.05), STREET_BAND[1])


#: How deep into the ranking a roll may reach. Three, not "any in-trade
#: candidate": the ranking is good and the tail is not. Measured on the shipped
#: phrases, the in-trade lists run from 1 to 12 long, and past about third place
#: they start displacing articles — `Haar Wille` for `Der Wille`, `le pâte bain`
#: for `le petit bain` — which is the function-word problem the phrase lists were
#: chosen to avoid arriving by a different door. Three keeps every roll a pun
#: while still giving a phrase up to three different shopfronts.
STREET_ROLL_DEPTH = 3


def street_lang(trade_id: str, raw: str | None) -> Lang:
    """A language the trade actually speaks.

    A trade is not padded into a language it has nothing for — `optician` ships
    English only — so asking for `optician` in German must fall back rather than
    render an empty street.
    """
    trade = domain.load(trade_id)
    if raw in ("en", "de", "fr"):
        candidate: Lang = raw  # type: ignore[assignment]
        if trade.speaks(candidate):
            return candidate
    for candidate in ("de", "en", "fr"):
        typed: Lang = candidate  # type: ignore[assignment]
        if trade.speaks(typed):
            return typed
    raise KeyError(trade_id)


def street_langs(trade_id: str) -> tuple[Lang, ...]:
    """Which languages this trade can be shown in, for the picker."""
    trade = domain.load(trade_id)
    return tuple(lang for lang in ("de", "en", "fr") if trade.speaks(lang))  # type: ignore[misc]


def _displacement(sign: str, source: str, lang: Lang) -> tuple[str, str]:
    """The word that landed and the word it pushed out.

    Read off the two texts by position rather than recomputed, because the
    generator already decided it and a second derivation is a second chance to
    disagree. Falls back to empty strings rather than raising: a caption is not
    worth an exception.
    """
    here = [word for _, word in word_spans(sign, get_pack(lang))]
    there = [word for _, word in word_spans(source, get_pack(lang))]
    # `strict=False`: the two texts can differ in word count when a caption is
    # built for a pair `check` would reject with `length_mismatch`, and a
    # caption is not worth an exception.
    for landed, displaced in zip(here, there, strict=False):
        if landed.casefold() != displaced.casefold():
            return landed, displaced
    return "", ""


@lru_cache(maxsize=512)
def _street_candidates(
    phrase: str, lang: Lang, trade_id: str, ceiling: float, wanted: int
) -> tuple[tuple[str, float, float], ...]:
    """One phrase's displacements, cached on exactly what decides them.

    Cached *here* rather than in the library, and that is the point. Scanning a
    lexicon honestly costs real time — 69,090 edit-distance comparisons for a
    two-word German phrase, measured — because the prefilter in front of it is
    now sound where it used to be fast and wrong. The right answer to that is
    not to make the library guess again; it is for the one caller that asks the
    same eight questions on every page load to stop asking them twice.

    Keyed on the parameters that change the answer and nothing else, so a roll
    (which changes only which of the returned candidates is chosen) is free
    after the first draw of that band.
    """
    try:
        production = produce(
            "paronomasia",
            phrase,
            lang=lang,
            domain=trade_id,
            # Only the trade's own words. The street hangs nothing else — a sign
            # outside the trade is dropped a few lines below — so searching the
            # rest of the lexicon was work whose every result was discarded. The
            # winner is identical either way, verified in `test_stage.py`.
            domain_only=True,
            max_distance=ceiling,
            max_results=wanted,
        )
    except NoCandidateWord:
        return ()
    return tuple(
        (candidate.text, candidate.metrics["distance"], candidate.metrics["in_trade"])
        for candidate in production.candidates
    )


def _blend_shopfronts(trade_id: str, lang: Lang, ceiling: float) -> list[Shopfront]:
    """The trade's coinages, each checked by `portmanteau`.

    A blend's distance is between the spliced word and the stretch of host it
    covers, which is a different measurement from a displacement's — but it is
    the same scale, so the dial governs both. An earlier draft exempted blends,
    on the reasoning that they are the other figure; the effect was that closing
    the band to 0.05 still hung `Haarmonie` at 0.333, and a reader who has just
    asked for homophones only has been told no. One dial, everything it shows.
    """
    trade = domain.load(trade_id)
    out: list[Shopfront] = []
    for blend in trade.blends(lang):
        if not fit_for_stage(blend.coinage):
            continue
        # A blend may name its own splice language, for the `-hair` family that
        # is English inside French. It may no longer name its own ceiling: that
        # existed for two "visual" blends which turned out to be resting on a
        # phantom window in `_closest_window`, and both are gone.
        report = denckring_check(
            "portmanteau",
            blend.coinage,
            lang=lang,
            source=blend.host,
            splice=blend.splice,
            splice_lang=blend.splice_lang,
            max_distance=ceiling,
        )
        if not report.satisfied:
            continue
        out.append(
            Shopfront(
                sign=blend.coinage,
                source=blend.host,
                landed=blend.splice,
                # Nothing was pushed out of a blend — the host is still there,
                # which is what makes it a blend rather than a displacement.
                displaced=blend.host,
                distance=report.metrics.get("distance", 0.0),
                in_trade=True,
                satisfied=report.satisfied,
                figure="portmanteau",
                style="",
            )
        )
    return out


#: Hosts the blend generator is pointed at, per trade and language. Ordinary
#: words, not names — the generator splices the trade into them and the checker
#: throws out what is not a blend, so what comes back is a coinage nobody wrote
#: down. Kept here rather than in the domain files because these are not data
#: about the trade; they are a handful of words to aim at, and the shipped
#: `blends` remain the attested ones.
#: Curated, and the curation is honest work rather than cheating: the generator's
#: rank-1 answer is good for most hosts and a seam stutter for some
#: (`Wellensittich` gives `WWellensittich`), which is the weakness ADR 0043
#: records. A stage is not the place to demonstrate a known failure mode on
#: every fourth press, so the hosts here are ones whose best answer was checked
#: by eye. No host that already has an attested blend in the domain files, so
#: what comes back is a coinage nobody wrote down: `Kamera` gives `Kammera`,
#: `airline` gives `hairline`, `curtain` gives `curltain`.
INVENTED_HOSTS: dict[tuple[str, str], tuple[str, ...]] = {
    ("hair", "de"): ("Kamera", "Harfe", "Kaminfeuer", "Kamin", "Harmlos", "Kabarett", "Karneval"),
    ("hair", "en"): ("airline", "curtain", "comparison"),
    ("bakery", "en"): ("granite", "royalty"),
    ("optician", "en"): ("spectacle",),
}


def invented(trade_id: str, lang: Lang, ceiling: float, rng: random.Random) -> Shopfront | None:
    """A blend the generator made, rather than one anybody recorded.

    This is the scene's strongest claim and the reason it is worth wiring the
    generator in at all: everything else on the stage is a name from the shipped
    data, checked live. This one did not exist until the button was pressed, and
    it is checked by exactly the same call.

    Returns `None` rather than raising when a host yields nothing inside the
    band, which a tight dial does routinely.
    """
    hosts = INVENTED_HOSTS.get((trade_id, lang), ())
    if not hosts:
        return None
    host = rng.choice(hosts)
    try:
        production = produce(
            "portmanteau",
            host,
            lang=lang,
            domain=trade_id,
            max_distance=ceiling,
            max_results=1,
        )
    except DenckringError:
        return None
    # Rank one only. The generator's first answer is the measured-good one — the
    # attested name for ten hosts in twelve — and everything behind it is where
    # the stutters live.
    candidate = production.candidates[0]
    report = denckring_check(
        "portmanteau",
        candidate.text,
        lang=lang,
        source=host,
        splice=_splice_of(candidate.text, host, trade_id, lang),
        max_distance=ceiling,
    )
    if not fit_for_stage(candidate.text) or not report.satisfied:
        return None
    return Shopfront(
        sign=candidate.text,
        source=host,
        landed=_splice_of(candidate.text, host, trade_id, lang),
        displaced=host,
        distance=candidate.metrics["distance"],
        in_trade=True,
        satisfied=True,
        figure="portmanteau",
        style="",
        invented=True,
    )


def _splice_of(coinage: str, host: str, trade_id: str, lang: Lang) -> str:
    """Which trade word the generator put in. Recovered by looking, not guessed.

    `produce` does not say which word it spliced — `Candidate` carries metrics
    and text — so the shortest trade word present in the coinage and absent from
    the host is the answer. Shortest because a longer one containing it would
    also be present.
    """
    folded = coinage.casefold()
    present = [
        word
        for word in domain.load(trade_id).words(lang)
        if word.casefold() in folded and word.casefold() not in host.casefold()
    ]
    return min(present, key=len) if present else ""


#: Where the shopfront scene looks for phrases. Overridable, because a corpus
#: belongs to whoever assembled it (ADR 0020) and a reader with better phrases
#: than these should be able to say so:
#:
#:     DENCKRING_PHRASES_PATH=~/my-phrases uv run explorer
#:
#: A directory of `<trade>_<lang>.txt`, one phrase per line. Read fresh on every
#: call rather than cached at import, so pointing the variable somewhere else
#: between two calls actually changes the answer — the same rule `device.load`
#: follows for `DENCKRING_DEVICE_PATH`.
PHRASES_ENV = "DENCKRING_PHRASES_PATH"
SHIPPED_PHRASES = Path(__file__).resolve().parent / "data" / "phrases"


def phrase_corpus(trade_id: str, lang: Lang) -> tuple[str, ...]:
    """Phrases for this trade, from the corpus if there is one.

    Falls back to the trade's own `phrases` list, which is small and was written
    by hand. The corpus is preferred because the hand-written list was chosen for
    *reachability* — does a trade word land inside the band? — and that produced
    phrases like `Alles klar`, which are real German and not things anybody would
    put over a shop. The corpus is film titles people know.

    A missing or unreadable directory falls back quietly rather than raising: a
    stale environment variable should not stop the scene rendering.
    """
    for directory in (os.environ.get(PHRASES_ENV), SHIPPED_PHRASES):
        if not directory:
            continue
        path = Path(directory) / f"{trade_id}_{lang}.txt"
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        phrases = tuple(line.strip() for line in lines if line.strip())
        if phrases:
            return phrases
    return domain.load(trade_id).phrases(lang)


def shop_options(trade_id: str, lang: Lang, ceiling: float = STREET_BAND[1]) -> list[Shopfront]:
    """Every sign this trade can hang inside the band, closest first.

    Separate from `shop` so the *offering* can be tested apart from the draw.
    Monotonicity — that closing the band only ever removes signs — is a property
    of this list; it is not a property of what a seeded draw returns, because a
    shorter list makes the same seed choose a different element. An earlier test
    asserted it of the draw and failed for that reason, which is the test being
    wrong rather than the scene.
    """
    offered: list[Shopfront] = []
    for phrase in phrase_corpus(trade_id, lang):
        found = _street_candidates(phrase, lang, trade_id, ceiling, STREET_ROLL_DEPTH * 4)
        in_trade = [item for item in found if item[2]]
        if not in_trade:
            continue
        # Each phrase offers its BEST displacement and no other. With five houses
        # a weaker second choice was variety; with one sign it is just a worse
        # sign, and there is no better one beside it to make the point. Variety
        # comes from which of the trade's shops is drawn — fourteen for the
        # German salon, across two figures — and from the paint.
        text, distance, _ = in_trade[0]
        if not fit_for_stage(text):
            continue
        landed, displaced = _displacement(text, phrase, lang)
        offered.append(
            Shopfront(
                sign=text,
                source=phrase,
                landed=landed,
                displaced=displaced,
                distance=distance,
                in_trade=True,
                satisfied=denckring_check(
                    "paronomasia", text, lang=lang, source=phrase, max_distance=ceiling
                ).satisfied,
                figure="paronomasia",
                style="",
            )
        )
    offered.extend(_blend_shopfronts(trade_id, lang, ceiling))
    offered.sort(key=lambda house: (house.distance, house.sign))
    return offered


def shop(
    trade_id: str,
    lang: Lang,
    ceiling: float = STREET_BAND[1],
    rng: random.Random | None = None,
) -> Shopfront | None:
    """One shop, drawn from everything this trade can put on a sign.

    The scene was five small houses in a row, and that row's argument was that
    distance became *spatial* — shops vanished left to right as the band closed.
    One sign gives that up and buys the whole stage for the pun, which is what a
    shopfront is for. The band keeps its meaning twice over: as the number on the
    sign, and as which signs remain drawable at all.

    Both figures are eligible, and the scene says which it is showing. A
    displacement (`paronomasia`, `Kamm rein`) and a blend (`portmanteau`,
    `Haarmonie`) are different operations checked by different rows; blurring
    them would be the drift the catalogue's own rules exist to prevent, and
    leaving blends out was leaving out the half of the tradition a reader
    actually recognises.

    Returns `None` when the trade has nothing inside the band — which a closed
    band is supposed to produce, and the template says so.
    """
    draw = rng or random.Random(0)
    offered = shop_options(trade_id, lang, ceiling)
    if not offered:
        return None
    # One draw in four is a coinage the generator made rather than one anybody
    # wrote down. Only on a roll: first paint and every recording stay
    # deterministic, and an invented sign that failed to appear would otherwise
    # make the scene look broken rather than empty.
    if rng is not None and draw.random() < 0.25:
        made = invented(trade_id, lang, ceiling, draw)
        if made is not None:
            return replace(made, style=draw.choice(SIGN_STYLES))
    chosen = draw.choice(offered) if rng is not None else offered[0]
    # The style is drawn separately from the sign, so pressing the button on a
    # trade with one shop still changes something. It is paint and never
    # content: a test pins that the verdict is identical whichever style is used.
    return replace(chosen, style=draw.choice(SIGN_STYLES))
