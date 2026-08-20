"""The stage: what each scene is, and the data it needs.

Preparation only. Nothing here renders, and nothing here touches HTTP — a scene's
route reads from this module and hands the result to a template, so the thing a
scene claims can be tested without a browser.
"""

from __future__ import annotations

from dataclasses import dataclass

from denckring.core import device
from denckring.core.protocol import Lang, LanguagePack
from denckring.lang import get_pack
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


def pieces_for(word: str) -> list[str] | None:
    """The five ring pieces that spell `word`, one per slot, or `None` if the rings
    cannot spell it at all.

    The same segmentation `check` itself relies on — `denckring.core.device.segment`
    — so that when the library turns the rings for the scene (rather than a person
    clicking them), the diagram can be walked to the position that actually produced
    the word instead of leaving it wherever it happened to be. A skipped optional
    ring (prefix or suffix) comes back as `""`.
    """
    return device.segment(word, device.load("harsdoerffer_1651"))


def german_pack() -> LanguagePack:
    """The German pack, with the lexicon `is_word` and rhyme mode both need."""
    return get_pack("de")


#: Stems, not whole words: one entry also catches every inflected form the
#: rings can assemble around it ("fick" -> Ficken, fickst, gefickt, ...)
#: without enumerating each by hand. Matched against a casefolded word —
#: Python's own `casefold` already turns "ß" into "ss", so "Scheiße" and
#: "scheisse" match the same stem without this list carrying both spellings.
#:
#: This is the actual safety mechanism for every word this scene can put on
#: screen, not `RHYME_ENDINGS`'s curation: a hand-read pass over the -acken
#: sweep missed "Kacken", and `find_word` went through no curation at all —
#: a raw 184,040-word lexicon answers "is this a word", not "is this fit to
#: show on a recording". See `fit_for_stage` below, which every path onto
#: this stage now calls.
#:
#: Covers, deliberately: sexual vulgarities (fick, fotz/votz, muschi, wichs,
#: bums, hure, nutte, titt, möse, pimmel); scatological ones (scheiss/schiss
#: — both stems needed, since "beschissen" carries the strong verb's past
#: stem "schiss" rather than "scheiss"; kack; piss; kotz); and slurs (neger,
#: zigeuner, kanak, spast).
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
#: this list to cover. "hure" is kept despite also catching "nachschüren"/
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
        # slurs
        "neger",
        "zigeuner",
        "kanak",
        "spast",
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
#: (sloppy) and "verschlampen" survive. The next entry that needs this same
#: precision — a slur reachable only in one exact inflected form, inside a
#: longer ordinary word as a stem — belongs here, not in `_BLOCKED_STEMS`.
_BLOCKED_EXACT = frozenset(
    {
        "schlampen",
    }
)


def fit_for_stage(word: str) -> bool:
    """Whether `word` is fit to appear on a recorded stage.

    The one predicate every path that can put a word on screen — `find_word`,
    `rhyme_sweep`, and "turn them for me" in `app.py` — calls before it does,
    so a word this scene shows is filtered exactly once, in exactly one
    place, rather than trusted to whichever curation a given path happened
    to build for itself.
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


def find_word(attempts: int = FIND_ATTEMPTS) -> tuple[str, list[str]] | None:
    """Turn the rings at random, server-side, until `is_word` recognises the
    result and `fit_for_stage` accepts it, or say the search failed rather
    than hang a recording on it.

    A viewer will not sit through the ~4,900 tries a random turn needs on
    average, so the search happens here in one request rather than one click
    at a time in the browser. `pieces_for` re-derives the ring pieces from
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


def rhyme_sweep(ending: RhymeEnding) -> list[str]:
    """One entry per position on the initial disc, in ring order: the word
    that position spells against the locked ending, or `""` where `is_word`
    rejects it or `fit_for_stage` does.

    This is the quotation turned into a search rather than an instruction:
    "seek the rhyme syllables on the third and fourth ring [and turn] the
    rhyme letters of the second ring to them." The medial, final and suffix
    rings are the ones `ending` already locked; this walks every letter the
    second ring (`anfangsbuchstabe`) offers and reads off what comes out. The
    full sweep, blanks included, so the scene can walk the disc through every
    position in order rather than only the hits.
    """
    initial = next(slot for slot in rings().slots if slot.name == "anfangsbuchstabe")
    german = german_pack()
    swept = []
    for letters in initial.alternatives:
        word = letters + ending.mittelbuchstabe + ending.endbuchstabe + ending.nachsylbe
        swept.append(word if german.is_word(word) and fit_for_stage(word) else "")
    return swept


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
    """One corpus, offered to the scene."""

    path: str
    name: str
    entries: int
    style: str
    register: str


def corpus_choices() -> list[CorpusChoice]:
    """Whatever is in `DENCKRING_CORPORA`, with its register resolved."""
    return [
        CorpusChoice(
            path=item.path,
            name=item.name,
            entries=item.entries,
            style=item.style,
            register=register_for(item.style),
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
    neighbours a viewer watches it pass."""
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
