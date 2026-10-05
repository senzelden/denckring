# Errors

Every failure mode in denckring is one of these. None of them is silent: each carries
a stable `code`, a human-readable message, and a `detail()` dict for a caller that
would rather not parse English out of the message.

Each is importable from `denckring` itself (`from denckring import InvalidParams`),
and this page documents them from there: that is the path under the README's
stability promise, and `denckring.core.errors`, where they are defined, is not. A
class keeps its name, its place under `DenckringError` and its `code`; the message
wording may change.

::: denckring.DenckringError

::: denckring.UnknownProcedure

::: denckring.UnknownLanguage

::: denckring.MissingCapability

::: denckring.InvalidParams

::: denckring.DuplicateProcedure

::: denckring.UnknownDevice

::: denckring.UnsettablePhrase

::: denckring.InputTooLong

::: denckring.TextTooLong

::: denckring.InputTooShort

::: denckring.DegenerateOutput

::: denckring.NoCandidateWord

::: denckring.MalformedTable

::: denckring.MalformedCorpus

::: denckring.MalformedDevice

::: denckring.MalformedFigure

::: denckring.UnknownFigure

::: denckring.UnknownLevel

::: denckring.DuplicatePack

::: denckring.NotConstructive

::: denckring.NoPromptHint

::: denckring.UnsetHintParameter

::: denckring.NotWordLocal
