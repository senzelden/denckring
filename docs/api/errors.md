# Errors

Every failure mode in denckring is one of these. None of them is silent: each carries
a stable `code`, a human-readable message, and a `detail()` dict for a caller that
would rather not parse English out of the message.

::: denckring.core.errors.DenckringError

::: denckring.core.errors.UnknownProcedure

::: denckring.core.errors.UnknownLanguage

::: denckring.core.errors.MissingCapability

::: denckring.core.errors.InvalidParams

::: denckring.core.errors.DuplicateProcedure

::: denckring.core.errors.UnknownDevice

::: denckring.core.errors.UnsettablePhrase

::: denckring.core.errors.InputTooLong

::: denckring.core.errors.NoCandidateWord

::: denckring.core.errors.MalformedTable

::: denckring.core.errors.MalformedCorpus

::: denckring.core.errors.UnknownFigure

::: denckring.core.errors.UnknownLevel

::: denckring.core.errors.DuplicatePack
