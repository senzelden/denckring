"""Put a question to the Art, and let it turn its own wheels.

**This does not belong in the package, and is not in it.** The same rule
`witz.py` states, for the same reason, and it matters more here because this
one sits on a scene that renders a real `check()` a few centimetres away. What
comes back is arguments, not a verdict: no `Report`, no score, nothing the
library consults, and the page says so in the words the Ideenwürfeln scene
already uses. `llull_figure`'s own checker answers exactly one question — is
this a genuine chamber of distinct principles — and that question stays
decidable from the letters alone. Whether an argument built out of a chamber is
any good is not a thing a program settles, and putting this behind `check`
would quietly break the property the library is built on.

What makes it worth having is that it is the device operating rather than a
chat box beside it. The model does not answer the question; it reads letters
out of the question, chooses a chamber of three distinct principles that
contains them, and then argues only from the six concepts those three letters
carry. The wheels then turn to the chamber it chose. That is the Ars: the
machine supplies the terms, and the reader is left holding the judgement — the
division of labour Harsdörffer's rings make too, and the one Descartes objected
to in exactly these terms.

`nihil` is the load-bearing part of the schema. A row whose concepts do not
bear on the question has to be allowed to say so, or every chamber produces
nine confident arguments and the thing becomes a machine for manufacturing
assent. Llull's own table has rows that go nowhere.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, cast

#: The three things a row of the table may conclude. `nihil` is not a failure
#: to answer — it is an answer, and the prompt asks for it honestly rather than
#: letting a row be filled to look complete.
VERDICTS = ("pro", "contra", "nihil")

#: How many rows one turning produces. Llull's own printed table runs to twenty
#: per column; five is what fits beside a scene without becoming the scene.
ROWS = 5

SYSTEM = """\
You are operating the fourth figure of Ramon Llull's Ars, as its own \
instructions describe it: three concentric wheels of nine letters, B to K, J \
skipped, each letter naming a different principle depending on which table it \
is read against.

You are not answering the question. You are turning the wheels and reading what \
the chamber they land on has to say about it. The difference is the whole point \
of the device, and a reader who wanted your opinion would not have come to a \
volvelle.

Do exactly this, in order:

1. Read letters out of the question itself. Which letter of the QUESTIONS \
column does it belong to, and which letter of the ABSOLUTE column does its key \
term fall under? Name both, in one sentence.
2. Choose one chamber of three DISTINCT letters that contains both. The third \
is whatever the wheel supplies — do not choose it to make the argument come out \
a particular way.
3. Produce rows from that chamber, as the printed table does. Each row takes \
two or three of the concepts those three letters carry, at any of the levels, \
and builds one argument bearing on the question.

Rules:

- A row's verdict is "pro", "contra" or "nihil". Use "nihil" honestly and often \
where the concepts genuinely do not bear on the question. Never manufacture an \
argument to fill a row. A table of five confident rows from a chamber that has \
nothing to say about the question is the failure this instruction exists to \
prevent.
- Rows may contradict each other. That is expected and is not something to \
resolve.
- Do not deliver an overall conclusion, a summary, or a recommendation. The \
judgement is the reader's and the device has never had one.
- Terse. A proposition is at most sixteen words; an inference at most forty.
- Name the concepts you are using by their Latin names, as the table does.\
"""

#: The one tool, and the whole of the contract. Forced rather than parsed out
#: of prose: the wheels have to be turned to the chamber that comes back, and a
#: chamber recovered by regex from a paragraph is a chamber the scene would
#: sometimes turn to the wrong place.
TOOL: dict[str, Any] = {
    "name": "read_the_chamber",
    "description": "Report the chamber the wheels landed on and what it says.",
    "input_schema": {
        "type": "object",
        "properties": {
            "chamber": {
                "type": "string",
                "description": "Three distinct letters from B C D E F G H I K, e.g. 'BCD'.",
            },
            "derived": {
                "type": "string",
                "description": "One sentence naming the letters read out of the question.",
            },
            "rows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "concepts": {"type": "string"},
                        "proposition": {"type": "string"},
                        "inference": {"type": "string"},
                        "verdict": {"type": "string", "enum": list(VERDICTS)},
                    },
                    "required": ["concepts", "proposition", "inference", "verdict"],
                },
            },
        },
        "required": ["chamber", "derived", "rows"],
    },
}


def model() -> str:
    """Which model turns the wheels. Overridable, because a bench should let
    you put a different reader in the chair and compare — the same reasoning
    `witz.model` gives, and the same default."""
    return os.environ.get("DENCKRING_ARS_MODEL", "claude-opus-5")


@dataclass(frozen=True)
class Row:
    """One row of the table: two or three concepts, and where they lead."""

    concepts: str
    proposition: str
    inference: str
    verdict: str


@dataclass(frozen=True)
class Session:
    """What came back, or why nothing did.

    `chamber` is the letters the wheels are to be turned to. It is empty
    whenever `problem` is set, so a caller cannot turn the figure to a chamber
    that was never validated.
    """

    chamber: str
    derived: str
    rows: list[Row]
    problem: str


def available() -> bool:
    """Whether a key is present. The control is hidden when it is not."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _chamber(raw: str, letters: list[str], arity: int) -> str:
    """The chamber, if it is one this figure actually has.

    Validated rather than repaired. A returned chamber decides where the wheels
    are turned, and quietly dropping a bad letter or padding a short chamber
    would move the figure to a position the model did not choose while the
    table beside it still described the one it did.
    """
    cleaned = "".join(ch for ch in raw.upper() if ch in set(letters))
    if len(cleaned) != arity or len(set(cleaned)) != arity:
        return ""
    return cleaned


def interrogate(question: str, *, alphabet: str, letters: list[str], arity: int = 3) -> Session:
    """Put one question to the figure.

    Failures come back rather than being raised: this sits on a scene beside a
    real verdict, and a missing key or a network blip must not take the page
    down — the same contract `witz.read` keeps.
    """
    if not question.strip():
        return Session("", "", [], "There is no question yet — type one first.")
    if not available():
        return Session("", "", [], "Set ANTHROPIC_API_KEY to put a question to the Art.")

    try:
        import anthropic
    except ImportError:
        return Session("", "", [], "The anthropic package is not installed in this environment.")

    prompt = (
        f"The nine letters, at every level they are read against:\n\n{alphabet}\n\n"
        f"A question is put to the Art: {question.strip()!r}\n\n"
        f"Turn the wheels and report {ROWS} rows."
    )

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model(),
            max_tokens=16000,
            system=SYSTEM,
            # `cast` because the SDK is imported lazily, the way `witz.py`
            # imports it: its own `ToolParam` types are not in scope at module
            # level, where `TOOL` has to live so that the schema is readable
            # beside the prompt it belongs to.
            tools=cast(Any, [TOOL]),
            tool_choice=cast(Any, {"type": "tool", "name": TOOL["name"]}),
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIStatusError as exc:
        return Session("", "", [], f"The model refused or errored ({exc.status_code}).")
    except anthropic.APIConnectionError:
        return Session("", "", [], "Could not reach the API. Check the network.")

    blocks = [block for block in response.content if block.type == "tool_use"]
    if not blocks:
        return Session("", "", [], "The wheels did not turn. Try again.")
    payload: dict[str, Any] = dict(cast(Any, blocks[0].input))

    chamber = _chamber(str(payload.get("chamber", "")), letters, arity)
    if not chamber:
        return Session(
            "",
            "",
            [],
            f"That is not a chamber of {arity} distinct principles on this figure.",
        )

    rows = [
        Row(
            concepts=str(row.get("concepts", "")),
            proposition=str(row.get("proposition", "")),
            inference=str(row.get("inference", "")),
            verdict=str(row.get("verdict", "")),
        )
        for row in payload.get("rows", [])
        if isinstance(row, dict) and str(row.get("verdict", "")) in VERDICTS
    ]
    if not rows:
        return Session("", "", [], "The chamber came back with nothing to say. Try again.")
    return Session(chamber, str(payload.get("derived", "")), rows, "")
