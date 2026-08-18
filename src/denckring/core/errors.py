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


class MissingCapability(DenckringError):
    code = "missing_capability"

    def __init__(self, procedure_id: str, lang: str, capability: str) -> None:
        self.procedure_id = procedure_id
        self.lang = lang
        self.capability = capability
        super().__init__(
            f"Procedure {procedure_id!r} requires the capability {capability!r}, "
            f"which the {lang!r} language pack does not provide. Install the "
            f"extra that supplies it: `pip install denckring[{lang}]`."
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

    def __init__(self, procedure_id: str, given: int, limit: int) -> None:
        self.procedure_id = procedure_id
        self.given = given
        self.limit = limit
        super().__init__(
            f"{procedure_id} can rearrange at most {limit} letters and was given "
            f"{given}. Shorten the text, or check it instead of generating it."
        )

    def detail(self) -> dict[str, Any]:
        return {"limit": self.limit, "received": self.given}


class NoCandidateWord(DenckringError):
    """A generator that needs a real word to swap into refuses when none exists.

    Raised rather than returning text with no swap in it: silence there would
    let a caller believe a pair had been produced when the lexicon offered
    nothing for any word in the text.
    """

    code = "no_candidate_word"

    def __init__(self, procedure_id: str) -> None:
        self.procedure_id = procedure_id
        super().__init__(
            f"{procedure_id} found no one-letter swap of any word into a word "
            f"the lexicon knows. Try a different text, or check it instead of "
            f"generating from it."
        )

    def detail(self) -> dict[str, Any]:
        return {"procedure_id": self.procedure_id}


class MalformedTable(DenckringError):
    code = "malformed_table"

    def __init__(self, reason: str) -> None:
        super().__init__(f"That numbered vocabulary cannot be read: {reason}")


class MalformedCorpus(DenckringError):
    code = "malformed_corpus"

    def __init__(self, reason: str) -> None:
        super().__init__(f"That corpus cannot be read: {reason}")


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
