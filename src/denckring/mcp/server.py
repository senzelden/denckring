"""An MCP server over the catalogue.

Four tools, with the procedure as a parameter. One tool per procedure would put
eighty-six definitions in every client's context; model performance degrades
sharply with tool count.

Nothing here computes anything. The tools call `describe`, `summaries` and
`check`, and convert `DenckringError` into data — a model can act on
`{"code": "invalid_params", ...}` and cannot act on a traceback.
"""

from __future__ import annotations

from typing import Any

from mcp.server import MCPServer

from denckring import check, describe, produce, summaries
from denckring.core.errors import DenckringError
from denckring.core.protocol import Lang

server = MCPServer("denckring")


def list_procedures_tool(
    query: str | None = None,
    family: str | None = None,
    runnable_only: bool = False,
    lang: Lang = "en",
) -> list[dict[str, Any]] | dict[str, Any]:
    """List the writing procedures this install can run.

    `query` matches ids, names and aliases. Call this before `check_text` if you
    do not already know a procedure's id.
    """
    try:
        rows = summaries(query=query, family=family, runnable_only=runnable_only, lang=lang)
    except DenckringError as exc:
        return exc.to_dict()
    return [row.model_dump() for row in rows]


def describe_procedure_tool(
    procedure: str, scholarly: bool = False, lang: Lang = "en"
) -> dict[str, Any]:
    """Describe one procedure: what it constrains, and its parameter schemas.

    `params` is JSON Schema — pass parameters matching it to `check_text`.
    `apply_params` is the separate schema `apply_procedure` takes, empty for a
    row with no generator; it is where `seed` and `allow_identity` are declared,
    which `params` does not carry. Set `scholarly` for the form's source,
    attribution and history.
    """
    try:
        return describe(procedure, lang=lang, scholarly=scholarly).model_dump()
    except DenckringError as exc:
        return exc.to_dict()


def check_text_tool(
    procedure: str,
    text: str,
    params: dict[str, Any] | None = None,
    lang: Lang = "en",
) -> dict[str, Any]:
    """Check whether a text satisfies a procedure's constraint.

    Returns `satisfied`, a `score`, and `violations`. Each violation names the
    rule it broke, what it `found` and what was `expected`, and usually carries
    an `offset` into the text. Fixing the first violation listed is normally the
    fastest route to a satisfied report.
    """
    try:
        return check(procedure, text, lang=lang, **(params or {})).model_dump()
    except DenckringError as exc:
        return exc.to_dict()


def apply_procedure_tool(
    procedure: str,
    text: str,
    params: dict[str, Any] | None = None,
    lang: Lang = "en",
) -> dict[str, Any]:
    """Run a procedure that generates rather than only checks.

    Some of the procedures have a generator here and most do not. `kind` says
    whether the form admits one; `constructive` in `describe_procedure` says
    whether this install has it. Read `constructive`, not `kind`, before calling
    this, and `apply_params` — not `params` — for what may go in `params` here.

    `constructive` is not the whole answer, because it does not depend on `lang`.
    A row can have a generator this install can run and still not run it in the
    language you asked for: `anagram` needs SCOWL, which ships for English alone
    (ADR 0028), and `proteus_verse` needs stress, which French has not got (ADR
    0034 D2). `apply_missing` is the language-aware field — empty means this call
    will run, non-empty names the capabilities it would refuse on. Check both.

    No count is given, deliberately: this said twenty-seven and was read by
    callers as current while the twenty-eighth was landing. `list_procedures`
    answers it exactly and cannot go stale.

    `text` is the first and best of `texts` — kept for callers that only ever
    wanted one result. `truncated` says whether more were found than
    `max_results` allowed.
    """
    try:
        produced = produce(procedure, text, lang=lang, **(params or {}))
    except DenckringError as exc:
        return exc.to_dict()
    return {
        "text": produced.texts[0],
        "texts": produced.texts,
        "truncated": produced.truncated,
        # `texts` alone made ADR 0031's `attestation: "mask"` a no-op over MCP:
        # the mask's whole output is a per-word attested/neglected mark on
        # `Candidate.metrics`, and `anagram` likewise ranks covers by a SCOWL
        # band the client never saw. A caller shown an order deserves the number
        # it was computed from, which is `Candidate`'s own stated contract.
        # `texts` stays, and stays first: ADR 0026 made `texts[0]` the definition
        # of `apply` and every existing consumer reads it.
        "candidates": [candidate.model_dump() for candidate in produced.candidates],
        "metrics": produced.metrics,
    }


# The functions carry a `_tool` suffix so the module can also be imported and
# called directly; the client must not see it. Register under the names the
# docstrings above tell the model to call.
for _name, _tool in (
    ("list_procedures", list_procedures_tool),
    ("describe_procedure", describe_procedure_tool),
    ("check_text", check_text_tool),
    ("apply_procedure", apply_procedure_tool),
):
    server.tool(name=_name)(_tool)


def main() -> None:
    """Entry point for `denckring-mcp`."""
    server.run()
