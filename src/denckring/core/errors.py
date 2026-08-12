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


class DuplicatePack(DenckringError):
    def __init__(self, lang: str, first: str, second: str) -> None:
        self.lang = lang
        super().__init__(
            f"Two language packs claim {lang!r}: {first} and {second}. "
            f"Uninstall one — silently choosing between them would make the "
            f"answers depend on installation order."
        )
