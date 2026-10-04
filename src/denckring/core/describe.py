"""The catalogue as a machine reads it.

Four callers need this assembly — the CLI's `show`, the explorer, the MCP
server and the skill — so it lives here rather than in any one of them.
Computing it four times is how four copies drift apart.
"""

from __future__ import annotations

from typing import Any, Literal, get_args

from pydantic import BaseModel, Field

from denckring.core import catalogue
from denckring.core.base import ConstructiveProcedure, RhymeParams
from denckring.core.errors import UnknownLanguage
from denckring.core.hints import rendered_with_defaults
from denckring.core.protocol import Constructive, Lang, LanguagePack, Meta
from denckring.core.registry import all_procedures, get
from denckring.core.text import UNIT_ENDS


class Scholarly(BaseModel):
    """Where a procedure comes from. Returned only when asked for."""

    source: str
    attribution: str
    attested: str
    aliases: list[str]
    notes: str | None


class Summary(BaseModel):
    """One catalogue row, compact enough to list eighty of."""

    id: str
    name: str
    definition: str
    family: str
    kind: str
    runnable: bool
    constructive: bool


#: Capabilities whose answers a pack may have to estimate. A row requiring any of
#: them can have its verdict rest on a guess; a row requiring none of them cannot.
#:
#: `pos` belongs here for a stronger reason than the rest (ADR 0045). The others
#: *may* estimate — `syllables.dictionary` looks a word up and falls back only
#: when the dictionary misses. A tagger never looks anything up: every answer it
#: gives is a model's, including for a word it has seen a thousand times. So a
#: `pos` row can no more be `exact` than a syllabic one, and calling it exact
#: would be the overclaim this field exists to prevent — `describe()` would tell
#: a caller that `verbless_prose`'s verdict is certain when its own ADR puts
#: finite-verb recall at 0.9498.
#:
#: `lexicon.glosses` joined in 0.4.0 (ADR 0054). A gloss lookup guesses nothing, but
#: a word no gloss resolves is left unjudged, and `Report.estimated` says so: the two
#: `definitional_*` rows called themselves `exact` while their reports could say
#: `estimated`. With `_reading`'s one other reason for `heuristic` (a row whose
#: parameters name its capabilities), an `exact` row is never `estimated`.
_SOFT = frozenset(
    {
        "syllables",
        "syllables.heuristic",
        "syllables.dictionary",
        "stress",
        "phonemes",
        "pos",
        "lexicon.glosses",
    }
)

#: What folding does, stated once. `BasePack.fold_diacritics` case-folds and strips
#: combining marks, so `ß` becomes `ss` and the result can be longer than its input;
#: `letter_spans` composes a base character with its marks first, so the answer does
#: not depend on whether the text arrived in NFC or NFD.
_FOLD_POLICY = (
    "NFC composition of each base character with its combining marks, then NFKD "
    "case-folding with marks stripped: 'ä' reads as 'a' and 'ß' as 'ss'. Turn it off "
    "with fold_diacritics=false, which lowercases only."
)
_NO_FOLD_POLICY = "Case only. This procedure does not compare letters, so nothing folds."

#: How each language's pack keys a rhyme, the half of `Reading.rhyme` that differs by
#: language. Held to the packs by `tests/test_rhyme_variants.py`, since no one reads
#: these sentences back out of the code they describe.
_RHYME_KEYS: dict[Lang, str] = {
    "en": (
        "A line ending's rhyme key is its sounds from the last primary-stressed vowel to the "
        "end, one key per listed pronunciation. Secondary stress does not key a rhyme: "
        "'someday' rhymes from its 'some', so it does not rhyme with 'day'. A word with no "
        "primary stress keys from its last vowel ('the' keys 'AH0')."
    ),
    "de": (
        "A line ending's rhyme key is its sounds from the last primary-stressed vowel to the "
        "end, read from the word's first transcription only: the dictionary's list mixes "
        "in inflected forms ('du' lists 'dich'). Secondary stress does not key a rhyme. A "
        "word with no primary stress keys from its last vowel."
    ),
    "fr": (
        "A line ending's rhyme key is its sounds from the last vowel to the end; French has "
        "no lexical stress, and the dictionary holds one transcription per spelling."
    ),
}
#: How a scheme reads the keys, the half that is the same in every language (ADR 0057).
_RHYME_PAIRS = (
    " Lines the scheme pairs rhyme when some reading of each shares a key. Lines it keeps "
    "apart fail when every reading of each shares the key, or when the two words have the "
    "same keys, since then every reader rhymes them ('fog' and 'bog'). Otherwise a word "
    "with two readings passes if one keeps the pair apart ('gone' and 'on'). Each pair is "
    "judged on its own: one reading may keep one pair apart while another makes a second "
    "pair rhyme."
)

#: Strings whose tokenization answers the questions a word count turns on: both
#: apostrophes (an English contraction, a French elision), a hyphen, a digit.
WORD_PROBES = ("don't", "l’âme", "well-known", "route66")  # noqa: RUF001


class Reading(BaseModel):
    """How a checker turns text into the units it judges, and how firm the answer is.

    The three things the developer feedback of 2026-09-07 asked a specification to
    record that `describe` did not: what normalisation is applied, what counts as a
    word, and whether the answer is exact or may rest on an estimate.

    `determinacy` is a property of the *row*, not of a run: `heuristic` means the
    verdict can rest on a guess, or on words left unjudged, not that it did.
    `Report.estimated` is what says whether it actually did on a given call, and
    `Report.evidence` which words. An `exact` row's report is never `estimated`.

    A row is `heuristic` when its `requires` name a capability a pack may estimate,
    or when its parameters rather than its `requires` decide what it needs
    (`requires_from_params`): `multiple_constraint` may compose any row, so a
    description of the row cannot know whether a call's entries estimate, and reads
    it `heuristic` even though a composite of exact rows never is (ruling R-F5).
    """

    determinacy: Literal["exact", "heuristic"]
    normalization: str
    #: The pack's word pattern, for the language asked about. A caller comparing its
    #: own tokenisation against a verdict needs to know what this one counted. Kept a
    #: pattern rather than prose, so a caller can run it; what it makes of a hyphen is
    #: `word_examples`, and whether `y` is a vowel is `vowels` (audit A10, ADR 0058).
    tokenization: str
    #: The characters that end a line, a clause and a sentence, as the checkers split
    #: them (`core.text.UNIT_ENDS`). The same for every row: a row that reads no clause
    #: still says what one would be, so a caller can build a prompt or a guard on the
    #: published marks rather than on a private constant. Punctuation only, as the
    #: splitters are: `Mr.` ends a sentence. Each entry is a set of characters, and a
    #: break may take two of them: `\r\n` ends one line, as `str.splitlines` reads it,
    #: so count line ends by splitting, not by counting members of `units["line"]`.
    units: dict[str, str] = Field(default_factory=lambda: dict(UNIT_ENDS))
    #: What `tokenization` makes of an apostrophe, a hyphen and a digit, shown by running
    #: it on `WORD_PROBES`: each probe maps to the words it yields. An apostrophe between
    #: letters stays inside a word, though a word's length counts only its letters
    #: (`snowball` reads `I'm` as two, ADR 0058); a hyphen splits a word in two, so a
    #: sentence's word count reads `well-known` as two; a digit is no part of one.
    #: Derived by running the pattern rather than written down, so it cannot drift from
    #: it (audit E6).
    word_examples: dict[str, list[str]]
    #: The letters `univocalic`, `bivocalic`, `monoconsonantal` and `homovocalism` read
    #: as vowels in this language, as the pack lists them; the text's letters are folded
    #: before they are compared. `y` is among them in French and not in English or
    #: German. `supervocalic` reads a narrower inventory, the five vowels, with `y` left
    #: out in every language (ADR 0035, D1).
    vowels: str
    #: What makes two line endings rhyme, on a row that judges a rhyme (its parameters
    #: take `RhymeParams`), and `None` on every other row. The key a pack reads and
    #: how a scheme reads several of them, which a writer told two lines rhyme
    #: against the scheme needs and the verdict alone does not say (ADR 0057).
    rhyme: str | None = None


class Description(BaseModel):
    """Everything a model needs to use one procedure."""

    id: str
    name: str
    definition: str
    prompt_hints: str | None
    family: str
    kind: str
    #: Whether *this install* has a generator. Distinct from `kind`, which says
    #: whether the form admits one at all: nine rows are honestly `both` and
    #: honestly have no `apply` here, and a single field could not say both.
    constructive: bool
    checkability: str
    languages: list[str]
    #: Which languages this install can actually check the row in, computed from
    #: the packs' capabilities. `languages` above is authored editorial scope —
    #: `wechselsatz` is German by nature and not merely by capability — and the
    #: two answer different questions. Derived rather than authored so it cannot
    #: drift into the false claim a `[en]` row made once French began working.
    runs_in: list[str]
    requires: list[str]
    runnable: bool
    missing: list[str]
    apply_requires: list[str]
    apply_missing: list[str]
    params: dict[str, Any]
    #: JSON Schema for the parameters `apply` accepts, empty for a row with no
    #: generator to pass any to. Distinct from `params`, which is the checker's
    #: model and does not carry `seed` — so a caller that never touches Python
    #: could not see it, and the developer feedback that
    #: started this chapter was largely that the MCP surface does not say
    #: things. `params` is not merely a subset of this one: `source` is supplied
    #: by `apply` from the text it transforms, and passing it as a parameter is
    #: refused. Both may carry `allow_identity`, under one name with two
    #: meanings: here, permit output that is the input again (on a source row,
    #: its letters in order) or empty (default false); in `params`, on the
    #: source rows that declare it, accept the source back unchanged as an
    #: answer (default false since 0.4.0, ADR 0055).
    apply_params: dict[str, Any]
    #: `Meta.unique_answer`: `check` passes only the text `apply` returns.
    unique_answer: bool = False
    #: `Meta.hidden_material`: what the verdict reads that a prompt does not show.
    hidden_material: list[str] = Field(default_factory=list)
    #: Every `violation.rule` the row's checker can emit, sorted: `denckring.rules`,
    #: carried here so a caller of the CLI or the MCP server reads the vocabulary the
    #: README promises without Python (ruling R-F6). `multiple_constraint` answers with
    #: every other row's rules, as `denckring.rules` does. Added in 0.4.0.
    rules: list[str] = Field(default_factory=list)
    #: Which of `name`, `definition` and `prompt_hints` are not in the language
    #: asked for but in a substitute. Localisation has always fallen back to
    #: English, silently and per field, so a French caller received English prose
    #: in a field typed as French with nothing marking it: measured over 155 rows
    #: on 2026-09-04, `names` de 95 / fr 98, `definitions` de 95 / fr 95, and
    #: `prompt_hints` de 4 / fr 0. Empty means everything present is in `lang`.
    #: The fallback itself is unchanged — a substitute beats a blank field — this
    #: only stops it being invisible.
    untranslated: list[str]
    #: Normalisation, tokenisation and whether the answer can rest on an estimate.
    #: Always present: these are properties of the row, not opt-in scholarship.
    reading: Reading
    scholarly: Scholarly | None = None


def runnable(meta: Meta, lang: Lang = "en") -> tuple[bool, list[str]]:
    """Whether this install can run the procedure, and what it lacks.

    Returns rather than raises for a genuine capability gap. A plugin/import
    error is not a capability gap — it is a broken install, and letting it
    surface is what tells a caller the two apart (P2-03); `describe.runnable`
    used to catch bare `Exception` here, which hid `DuplicatePack` and any
    third-party entry-point failure behind an ordinary-looking "not runnable".
    """
    from denckring.lang import get_pack

    try:
        pack = get_pack(lang)
    except UnknownLanguage:
        return False, list(meta.requires)
    missing = [cap for cap in meta.requires if cap not in pack.capabilities]
    return not missing, missing


def apply_runnable(
    meta: Meta, lang: Lang = "en", *, pack: LanguagePack | None = None
) -> tuple[bool, list[str]]:
    """Whether this install can *generate* with the procedure, and what it lacks.

    Separate from `runnable` because the two halves have different costs: a
    core-only install checks an anagram perfectly well and cannot generate one.
    Takes an optional pack so a test can ask about an install it is not running.
    """
    if pack is None:
        from denckring.lang import get_pack

        try:
            pack = get_pack(lang)
        except UnknownLanguage:
            return False, [*meta.requires, *meta.apply_requires]
    missing = [
        capability
        for capability in (*meta.requires, *meta.apply_requires)
        if capability not in pack.capabilities
    ]
    return not missing, missing


def _text(mapping: dict[Lang, str], lang: Lang) -> str:
    """The requested language, falling back to English, then to anything."""
    if lang in mapping:
        return mapping[lang]
    if "en" in mapping:
        return mapping["en"]
    return next(iter(mapping.values()), "")


def _fell_back(mapping: dict[Lang, str], lang: Lang) -> bool:
    """Whether `_text` substituted another language for `lang`.

    An *empty* mapping is not a fallback: a row carrying no `prompt_hints` at all
    has none to translate, and `prompt_hints` is already `None` to say so.
    Reporting it as untranslated would say a row was mistranslated when it is
    merely silent, which is the error this field exists to avoid making.

    No catalogue row reaches that branch today — all 155 carry at least one
    `prompt_hints` entry, measured 2026-09-04 — but `prompt_hints` is optional in
    `Meta`, so the case is reachable by the next row added and is covered by a
    test against the mapping rather than against a row.
    """
    return bool(mapping) and lang not in mapping


def _reading(meta: Meta, procedure: Any, lang: Lang) -> Reading:
    """Derived, never authored, for the reason `runs_in` is: a hand-written answer
    drifts from the code it describes and nothing notices."""
    from denckring.lang import get_pack

    folds = "fold_diacritics" in procedure.params_model().model_fields
    pack = get_pack(lang)
    return Reading(
        determinacy=(
            "heuristic" if procedure.requires_from_params or _SOFT & set(meta.requires) else "exact"
        ),
        normalization=_FOLD_POLICY if folds else _NO_FOLD_POLICY,
        tokenization=pack.word_re.pattern,
        word_examples={probe: pack.word_re.findall(probe) for probe in WORD_PROBES},
        vowels="".join(sorted(pack.vowels())),
        rhyme=(
            _RHYME_KEYS[lang] + _RHYME_PAIRS
            if issubclass(procedure.params_model(), RhymeParams)
            else None
        ),
    )


def describe(procedure_id: str, *, lang: Lang = "en", scholarly: bool = False) -> Description:
    """One procedure, in full. Raises `UnknownProcedure` for an unknown id."""
    from denckring import rules

    meta = catalogue.get(procedure_id)
    procedure = get(procedure_id)
    is_constructive = isinstance(procedure, Constructive)
    ok, missing = runnable(meta, lang)
    _, apply_missing = apply_runnable(meta, lang)
    return Description(
        id=meta.id,
        name=_text(meta.names, lang),
        definition=_text(meta.definitions, lang),
        # Rendered from defaults where they fill every placeholder, so this and
        # every surface reading it show a hint a model can act on (ADR 0050).
        prompt_hints=(
            rendered_with_defaults(
                meta.id,
                _text(meta.prompt_hints, lang),
                procedure.params_model(),
                lang if lang in meta.prompt_hints else "en",
            )
            or None
        ),
        family=meta.family,
        kind=meta.kind,
        constructive=is_constructive,
        checkability=meta.checkability,
        languages=list(meta.languages),
        runs_in=[lang for lang in get_args(Lang) if runnable(meta, lang)[0]],
        requires=list(meta.requires),
        runnable=ok,
        missing=missing,
        apply_requires=list(meta.apply_requires),
        apply_missing=apply_missing,
        untranslated=[
            field
            for field, mapping in (
                ("name", meta.names),
                ("definition", meta.definitions),
                ("prompt_hints", meta.prompt_hints),
            )
            if _fell_back(mapping, lang)
        ],
        reading=_reading(meta, procedure, lang),
        params=procedure.params_model().model_json_schema(),
        # Asked of the spine rather than the `Constructive` protocol, which
        # declares `apply` alone. The two cannot disagree: every procedure that
        # defines `apply` inherits `ConstructiveProcedure`, which
        # `test_apply_spine.py::test_every_generator_is_on_the_spine` pins.
        apply_params=(
            procedure.apply_params_model().model_json_schema()
            if isinstance(procedure, ConstructiveProcedure)
            else {}
        ),
        unique_answer=meta.unique_answer,
        hidden_material=list(meta.hidden_material),
        rules=list(rules(procedure_id)),
        scholarly=(
            Scholarly(
                source=meta.source,
                attribution=meta.attribution,
                attested=meta.attested,
                aliases=list(meta.aliases),
                notes=meta.notes,
            )
            if scholarly
            else None
        ),
    )


def _matches(meta: Meta, needle: str) -> bool:
    haystack = [meta.id, *meta.names.values(), *meta.aliases]
    return any(needle in field.casefold() for field in haystack)


def summaries(
    *,
    query: str | None = None,
    family: str | None = None,
    runnable_only: bool = False,
    lang: Lang = "en",
) -> list[Summary]:
    """The implemented procedures, filtered. `query` subsumes search.

    Only implemented rows appear: the other 66 catalogued forms have no checker,
    so offering them would be offering something that cannot run.
    """
    needle = query.casefold() if query else None
    rows: list[Summary] = []
    for procedure_id in all_procedures():
        meta = catalogue.get(procedure_id)
        if needle and not _matches(meta, needle):
            continue
        if family and meta.family != family:
            continue
        ok, _ = runnable(meta, lang)
        if runnable_only and not ok:
            continue
        rows.append(
            Summary(
                id=meta.id,
                name=_text(meta.names, lang),
                definition=_text(meta.definitions, lang),
                family=meta.family,
                kind=meta.kind,
                runnable=ok,
                constructive=isinstance(get(procedure_id), Constructive),
            )
        )
    return rows
