"""Every failure mode in denckring is one of these. None of them is silent."""


class DenckringError(Exception):
    """Base class for every error the library raises."""


class UnknownProcedure(DenckringError):
    def __init__(self, procedure_id: str) -> None:
        self.procedure_id = procedure_id
        super().__init__(
            f"No procedure with id {procedure_id!r}. "
            f"Run `denckring list` to see the registered procedures."
        )


class UnknownLanguage(DenckringError):
    def __init__(self, lang: str) -> None:
        self.lang = lang
        super().__init__(
            f"No language pack installed for {lang!r}. "
            f"Install it with `pip install denckring[{lang}]`."
        )


class MissingCapability(DenckringError):
    def __init__(self, procedure_id: str, lang: str, capability: str) -> None:
        self.procedure_id = procedure_id
        self.lang = lang
        self.capability = capability
        super().__init__(
            f"Procedure {procedure_id!r} requires the capability {capability!r}, "
            f"which the {lang!r} language pack does not provide."
        )


class InvalidParams(DenckringError):
    def __init__(self, procedure_id: str, message: str) -> None:
        self.procedure_id = procedure_id
        super().__init__(f"Invalid parameters for procedure {procedure_id!r}: {message}")


class DuplicateProcedure(DenckringError):
    def __init__(self, procedure_id: str) -> None:
        self.procedure_id = procedure_id
        super().__init__(f"A procedure with id {procedure_id!r} is already registered.")


class UnknownDevice(DenckringError):
    def __init__(self, device_id: str, available: list[str] | None = None) -> None:
        self.device_id = device_id
        known = ", ".join(available or []) or "none"
        super().__init__(f"No combinatorial device called {device_id!r}. Available: {known}.")


class UnsettablePhrase(DenckringError):
    def __init__(self, syllables: int, covered: list[int]) -> None:
        self.syllables = syllables
        lengths = ", ".join(str(n) for n in covered) or "nothing"
        super().__init__(
            f"No tablet holds a pattern for a phrase of {syllables} syllables. "
            f"This box covers: {lengths}."
        )


class MalformedTable(DenckringError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"That numbered vocabulary cannot be read: {reason}")


class MalformedCorpus(DenckringError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"That corpus cannot be read: {reason}")


class UnknownFigure(DenckringError):
    def __init__(self, figure_id: str, available: list[str] | None = None) -> None:
        self.figure_id = figure_id
        known = ", ".join(available or []) or "none"
        super().__init__(f"No combinatory figure called {figure_id!r}. Available: {known}.")


class UnknownLevel(DenckringError):
    def __init__(self, figure_id: str, level: str, available: list[str]) -> None:
        self.level = level
        super().__init__(
            f"Figure {figure_id!r} has no level {level!r}. It reads at: {', '.join(available)}."
        )


class DuplicatePack(DenckringError):
    def __init__(self, lang: str, first: str, second: str) -> None:
        self.lang = lang
        super().__init__(
            f"Two language packs claim {lang!r}: {first} and {second}. "
            f"Uninstall one — silently choosing between them would make the "
            f"answers depend on installation order."
        )
