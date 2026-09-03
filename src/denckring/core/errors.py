"""Every failure mode in denckring is one of these. None of them is silent."""

from typing import Any


class DenckringError(Exception):
    """Base class for every error the library raises.

    `code` is a stable string rather than the class name, so renaming a class
    does not break a client reading the JSON. `to_dict` is what an agentic
    caller sees instead of a traceback.
    """

    #: Stable, snake_case, unique across subclasses. Asserted by the suite.
    code: str = ""

    def detail(self) -> dict[str, Any]:
        """Machine-readable specifics. Subclasses override; the base has none."""
        return {}

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "detail": self.detail()}


def _near(procedure_id: str, limit: int = 3) -> list[str]:
    """Ids whose id, name or alias contains the needle, then closest by edit distance.

    Imported lazily because `core.catalogue` imports this module — a module-level
    import would be circular.
    """
    from difflib import get_close_matches

    from denckring.core import catalogue

    needle = procedure_id.casefold()

    def fields(candidate: str) -> list[str]:
        meta = catalogue.get(candidate)
        return [*meta.names.values(), *meta.aliases]

    contains = [
        candidate
        for candidate in catalogue.ids()
        if needle in candidate.casefold()
        or any(needle in field.casefold() for field in fields(candidate))
    ]
    if contains:
        return contains[:limit]
    return get_close_matches(needle, list(catalogue.ids()), n=limit, cutoff=0.7)


class UnknownProcedure(DenckringError):
    code = "unknown_procedure"

    def __init__(self, procedure_id: str) -> None:
        self.procedure_id = procedure_id
        self.suggestions = _near(procedure_id)
        hint = f" Did you mean: {', '.join(self.suggestions)}?" if self.suggestions else ""
        super().__init__(
            f"No procedure with id {procedure_id!r}. "
            f"Run `denckring list` to see the registered procedures.{hint}"
        )

    def detail(self) -> dict[str, Any]:
        return {"procedure_id": self.procedure_id, "suggestions": self.suggestions}


class UnknownLanguage(DenckringError):
    code = "unknown_language"

    def __init__(self, lang: str) -> None:
        self.lang = lang
        super().__init__(
            f"No language pack installed for {lang!r}. "
            f"Install it with `pip install denckring[{lang}]`."
        )

    def detail(self) -> dict[str, Any]:
        return {"lang": self.lang}


#: The languages a data distribution exists for, and so the only ones an install
#: hint can honestly name. Listed rather than read from packaging metadata for the
#: reason `denckring.lang` keeps the packs themselves as built-in defaults: core
#: does not depend on its own installed metadata being readable. ADR 0029 made this
#: matter — French is a built-in pack carrying no lexicon, so every lexicon row fails
#: through here, and at the time `pip install denckring[fr]` named a distribution that
#: had never existed. A remedy nobody can follow is worse than no remedy. ADR 0032
#: shipped `denckring-fr-data`, so `fr` is now a remedy a reader can follow and it is
#: listed; the entry has to be added by hand for each new extra, which is the cost of
#: not reading packaging metadata.
#: Naming a language's extra still assumed that extra supplies the missing
#: capability, which is not always true. Measured on the 2026-09-02 MCP sweep:
#: `denckring[fr]` carries `syllables`, `syllables.dictionary`, `syllables.heuristic`
#: and `phonemes` since ADR 0034, but never `stress` -- French has none, permanently
#: (ADR 0034 D2), so all eighteen `stress` refusals recommended a `pip install` that
#: would run and change nothing. `denckring[de]` never carries `lexicon.graded_words`
#: either -- SCOWL is vendored into `denckring-en-data` alone (ADR 0028) -- so
#: `apply(anagram, lang="de")` recommended reinstalling an extra already installed.
#: `_PERMANENTLY_MISSING` names both so the generic remedy is skipped for them.
_EXTRAS = frozenset({"en", "de", "fr"})

#: `(lang, capability)` pairs no extra for that language will ever supply. Named by
#: hand for the reason `_EXTRAS` itself is: reading capability metadata across every
#: installable extra to answer this generically would make core depend on packaging
#: state it does not otherwise need. Each entry cites the ADR that makes the ceiling
#: permanent rather than an unfinished migration, so a future data chapter that lifts
#: one is a one-line removal, not a guess.
_PERMANENTLY_MISSING = frozenset(
    {
        ("fr", "stress"),  # ADR 0034 D2: French has no lexical stress.
        ("de", "lexicon.graded_words"),  # ADR 0028: SCOWL ships in denckring-en-data only.
    }
)


class MissingCapability(DenckringError):
    code = "missing_capability"

    def __init__(self, procedure_id: str, lang: str, capability: str) -> None:
        self.procedure_id = procedure_id
        self.lang = lang
        self.capability = capability
        remedy = (
            f"No data distribution supplies it for {lang!r}."
            if lang not in _EXTRAS or (lang, capability) in _PERMANENTLY_MISSING
            else f"Install the extra that supplies it: `pip install denckring[{lang}]`."
        )
        super().__init__(
            f"Procedure {procedure_id!r} requires the capability {capability!r}, "
            f"which the {lang!r} language pack does not provide. {remedy}"
        )

    def detail(self) -> dict[str, Any]:
        return {
            "procedure_id": self.procedure_id,
            "lang": self.lang,
            "capability": self.capability,
        }


class InvalidParams(DenckringError):
    code = "invalid_params"

    def __init__(self, procedure_id: str, message: str) -> None:
        self.procedure_id = procedure_id
        super().__init__(f"Invalid parameters for procedure {procedure_id!r}: {message}")

    def detail(self) -> dict[str, Any]:
        return {"procedure_id": self.procedure_id}


class DuplicateProcedure(DenckringError):
    code = "duplicate_procedure"

    def __init__(self, procedure_id: str) -> None:
        self.procedure_id = procedure_id
        super().__init__(f"A procedure with id {procedure_id!r} is already registered.")

    def detail(self) -> dict[str, Any]:
        return {"procedure_id": self.procedure_id}


class UnknownDevice(DenckringError):
    code = "unknown_device"

    def __init__(self, device_id: str, available: list[str] | None = None) -> None:
        self.device_id = device_id
        known = ", ".join(available or []) or "none"
        super().__init__(f"No combinatorial device called {device_id!r}. Available: {known}.")

    def detail(self) -> dict[str, Any]:
        return {"device_id": self.device_id}


class UnsettablePhrase(DenckringError):
    code = "unsettable_phrase"

    def __init__(self, syllables: int, covered: list[int]) -> None:
        self.syllables = syllables
        lengths = ", ".join(str(n) for n in covered) or "nothing"
        super().__init__(
            f"No tablet holds a pattern for a phrase of {syllables} syllables. "
            f"This box covers: {lengths}."
        )

    def detail(self) -> dict[str, Any]:
        return {"syllables": self.syllables}


class InputTooLong(DenckringError):
    """A generator that searches refuses input it cannot search in reasonable time.

    Raised rather than returning a poor result, so a caller learns the limit
    instead of silently receiving something the procedure could not really do.
    """

    code = "input_too_long"

    def __init__(self, procedure_id: str, given: int, limit: int, unit: str = "letters") -> None:
        """`unit` names what was counted, and defaults to what every caller
        counted when this was written. `proteus_verse` rearranges *words*, and
        a message telling its caller it can rearrange nine letters would be
        precisely and confidently wrong about the limit it just hit."""
        self.procedure_id = procedure_id
        self.given = given
        self.limit = limit
        self.unit = unit
        super().__init__(
            f"{procedure_id} can rearrange at most {limit} {unit} and was given "
            f"{given}. Shorten the text, or check it instead of generating it."
        )

    def detail(self) -> dict[str, Any]:
        return {"limit": self.limit, "received": self.given, "unit": self.unit}


def counted(count: int, noun: str, plural: str | None = None) -> str:
    """`1 line`, `0 lines`, `2 sentences` — the `found` half of `InputTooShort`.

    Every raise site built its own `f"{n} line"`, which reads "0 line" on empty
    input. Small, but this is the one string whose whole job is to tell a caller
    what they actually handed over, so it should not be visibly wrong about it.
    """
    return f"{count} {noun if count == 1 else (plural or noun + 's')}"


class InputTooShort(DenckringError):
    """The input could not feed the procedure.

    The counterpart to `InputTooLong`, and the honest form of what four
    generators used to do instead: return the input unchanged, which reads
    exactly like a procedure that ran and had no effect. `needed` and `found`
    are separate fields rather than one sentence, so a caller reading the JSON
    learns what to change without parsing English out of `message`.

    Raised wherever a generator has too few units to work on, whatever the unit
    is — lines, sentences, words, slots, entries. That is deliberately one code
    rather than a per-procedure choice: a caller retrying on `input_too_short`
    should not have to know that `spoonerism` once called two-few-words
    something else. `NoCandidateWord` keeps the narrower meaning it was built
    for: enough units were present and none of them was suitable.
    """

    code = "input_too_short"

    def __init__(self, procedure_id: str, needed: str, found: str) -> None:
        self.procedure_id = procedure_id
        self.needed = needed
        self.found = found
        super().__init__(
            f"{procedure_id!r} needs {needed}; found {found}. Give it more text, "
            f"or check a text instead of generating from one."
        )

    def detail(self) -> dict[str, Any]:
        return {
            "procedure_id": self.procedure_id,
            "needed": self.needed,
            "found": self.found,
        }


class DegenerateOutput(DenckringError):
    """`apply` produced its own input, or nothing at all.

    Raised rather than returned, for the reason `diastic` raises
    `NoCandidateWord` rather than returning "": handing back text that
    misrepresents what the procedure did is the failure, not a mild version of
    success. Usually it means the input could not feed the procedure.

    One error for these observations, because a caller cannot act very
    differently on them — each means the returned text says nothing about what
    the procedure did. `IDENTICAL` and `EMPTY` are waived by the same
    `allow_identity`; `NOTHING` is not — see below. The empty case is the more
    dangerous of the two waivable ones: `BaseProcedure._report` scores an empty
    text 1.0, so `melting_text` returning `""` was a satisfied report on a text
    that was never written.

    The message says what was observed and stops there. It does not say the
    procedure did not run, because the guard cannot tell that from a procedure
    that ran and drew the identity — which is not a corner case:
    `recombination` on two sentences draws the identity permutation for half of
    all seeds, and `boustrophedon` turning `'aba'` recovers `'aba'`. Claiming
    the stronger thing would be this class committing the fault it exists to
    catch.

    `NOTHING` is the one exception to that carefulness, and to the waiver:
    `_produce` returning `[]` is not a candidate the procedure judged and
    rejected, it is the procedure returning no candidate at all, so `apply`
    raises this directly rather than through `_guard_degenerate` — before
    `allow_identity` is even consulted. `allow_identity` exists for a caller
    who wants the degenerate-but-real result a procedure found; an empty list
    is not a result, so there is nothing for that flag to waive.
    """

    code = "degenerate_output"

    #: The shapes the guard can see, as `observed` reads in the message and in
    #: `detail()` — so a caller distinguishing them reads a stable string
    #: rather than parsing English, and one that does not can ignore the field.
    IDENTICAL = "text identical to its input"
    EMPTY = "empty text from input that was not empty"
    #: `_produce` returned no candidate at all — not one judged empty or
    #: identical, none offered in the first place. See the class docstring for
    #: why this is the one shape `allow_identity` cannot waive.
    NOTHING = "nothing at all"

    def __init__(self, procedure_id: str, observed: str = IDENTICAL) -> None:
        self.procedure_id = procedure_id
        self.observed = observed
        # `NOTHING` gets no `allow_identity` hint: unlike the other two shapes,
        # that flag cannot waive it, and offering it here would tell a caller a
        # retry could work when it cannot.
        hint = (
            ""
            if observed == self.NOTHING
            else " Pass allow_identity=true if the degenerate case is wanted."
        )
        super().__init__(f"{procedure_id!r} produced {observed}.{hint}")

    def detail(self) -> dict[str, Any]:
        return {"procedure_id": self.procedure_id, "observed": self.observed}


class NoCandidateWord(DenckringError):
    """A generator that needs a real word refuses rather than returning none.

    Raised rather than returning text with no candidate in it: silence there
    would let a caller believe something had been produced when nothing was
    available to produce it from. `reason` names what, specifically, offered
    nothing — a lexicon swap for `paragram`, a source word for `diastic` and
    `mesostic` — because "no candidate word" alone does not say what a caller
    should do differently. Left unset, the message is `paragram`'s original
    one, the first and for a while the only caller.
    """

    code = "no_candidate_word"

    #: What the message says when no caller supplies a reason — `paragram`'s
    #: original wording, kept so that row's behaviour is untouched. Stored on the
    #: instance like any other reason, so `detail()` never has to say `None`.
    LEXICON_DEFAULT = (
        "found no one-letter swap of any word into a word the lexicon knows. "
        "Try a different text, or check it instead of generating from it."
    )

    def __init__(self, procedure_id: str, reason: str | None = None) -> None:
        self.procedure_id = procedure_id
        self.reason = reason or self.LEXICON_DEFAULT
        super().__init__(
            f"{procedure_id}: {reason}" if reason else f"{procedure_id} {self.LEXICON_DEFAULT}"
        )

    def detail(self) -> dict[str, Any]:
        """`reason` is in here, not only inside `message`.

        The whole point of giving this error a reason was that an agentic caller
        learns the true cause — a source word for `diastic`, a lexicon swap for
        `paragram` — and a caller reading the JSON could reach it only by parsing
        English out of `message`, which is the thing `to_dict` exists to avoid.
        """
        return {"procedure_id": self.procedure_id, "reason": self.reason}


class MalformedTable(DenckringError):
    code = "malformed_table"

    def __init__(self, reason: str) -> None:
        super().__init__(f"That numbered vocabulary cannot be read: {reason}")


class MalformedCorpus(DenckringError):
    code = "malformed_corpus"

    def __init__(self, reason: str) -> None:
        super().__init__(f"That corpus cannot be read: {reason}")


class MalformedDevice(DenckringError):
    """A device file exists under a valid id, but its content cannot be read.

    Raised instead of letting the underlying YAML or Pydantic error escape.
    Both quote fragments of the file's own content in their default message
    — harmless for a device this package ships, not harmless for one read
    from `DENCKRING_DEVICE_PATH`, which is arbitrary user-authored YAML.
    `reason` is deliberately short and holds nothing read from the file
    itself: a parser exception's class name, or a count of validation
    errors, never a value out of the document.
    """

    code = "malformed_device"

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        super().__init__(f"The device at {path!r} cannot be read: {reason}")

    def detail(self) -> dict[str, Any]:
        return {"path": self.path}


class MalformedFigure(DenckringError):
    """The same failure mode as `MalformedDevice`, for a figure file."""

    code = "malformed_figure"

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        super().__init__(f"The figure at {path!r} cannot be read: {reason}")

    def detail(self) -> dict[str, Any]:
        return {"path": self.path}


class UnknownFigure(DenckringError):
    code = "unknown_figure"

    def __init__(self, figure_id: str, available: list[str] | None = None) -> None:
        self.figure_id = figure_id
        known = ", ".join(available or []) or "none"
        super().__init__(f"No combinatory figure called {figure_id!r}. Available: {known}.")

    def detail(self) -> dict[str, Any]:
        return {"figure_id": self.figure_id}


class UnknownLevel(DenckringError):
    code = "unknown_level"

    def __init__(self, figure_id: str, level: str, available: list[str]) -> None:
        self.level = level
        super().__init__(
            f"Figure {figure_id!r} has no level {level!r}. It reads at: {', '.join(available)}."
        )

    def detail(self) -> dict[str, Any]:
        return {"level": self.level}


class DuplicatePack(DenckringError):
    code = "duplicate_pack"

    def __init__(self, lang: str, first: str, second: str) -> None:
        self.lang = lang
        super().__init__(
            f"Two language packs claim {lang!r}: {first} and {second}. "
            f"Uninstall one — silently choosing between them would make the "
            f"answers depend on installation order."
        )

    def detail(self) -> dict[str, Any]:
        return {"lang": self.lang}


class NotConstructive(DenckringError):
    """Asked to generate with a procedure that only checks.

    The MCP tool built this dict by hand and returned it, which meant one
    failure mode in this package was not a `DenckringError` and could not be
    caught with the others. `kind` says whether the *form* admits a generator;
    `constructive` in `describe` says whether this install has one.
    """

    code = "not_constructive"

    def __init__(self, procedure_id: str) -> None:
        self.procedure_id = procedure_id
        super().__init__(
            f"{procedure_id!r} only checks; it has no generator in this install. "
            f"Read `constructive` in describe({procedure_id!r}) before generating."
        )

    def detail(self) -> dict[str, Any]:
        return {"procedure_id": self.procedure_id}
