"""Ask a model what the collision yields.

**This does not belong in the package, and is not in it.** `ideenwuerfeln`'s own
docstring says the step that matters — forcing remote materials together until a
likeness appears, the *Witz* of the Vorschule der Ästhetik — is exactly what no
program does, and the catalogue row says so too. That stays true: nothing here
is a checker, nothing here scores, and no `Report` is produced. The explorer is
a bench, and this is a reader sitting at it with an opinion.

Keeping it in the explorer is the whole point. The package's claim is that its
acceptance criteria are intrinsic; a language model's reading is not one, and
putting it behind `check` would quietly break the property the library is built
on. Here it is clearly a second thing, run by hand, next to the verdict.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def model() -> str:
    """Which model reads the throw. Overridable, because a bench should let you
    put a different reader in the chair and compare."""
    return os.environ.get("DENCKRING_WITZ_MODEL", "claude-opus-5")


#: The register belongs to the corpus, not to the feature. Jean Paul's own
#: excerpts want his periodic prose; a corpus of arXiv abstracts wants the
#: register its own material is written in, and forcing 1795 syntax onto
#: nucleation and qubits produces pastiche about physics rather than a figure.
#: A corpus declares its register in its JSON; `modern` is the default, because
#: it is the one that does not impersonate anybody.
#:
#: Write the paragraph, don't describe it.
#:
#: This asked for an analysis first — "say what these have in common" — which
#: produced competent criticism about a passage that did not exist. But the
#: excerpt books were working material: Jean Paul drew from them *into* prose,
#: and the Witz is a thing done in a sentence, not a claim about one. So the
#: deliverable is the paragraph itself, and the instructions below describe the
#: move rather than the mannerisms, because a caricature of the style is easy
#: and worthless while the construction is the part that transfers.
JEAN_PAUL = """\
You are Jean Paul at the writing desk, drawing on the excerpt books. Several \
excerpts from distant fields have been thrown together under one headword. \
Write the paragraph you would build out of them.

This is the Witz of the Vorschule der Ästhetik: the finding of resemblance in \
remote material — *das Finden der Ähnlichkeit im Entlegenen*. Not a summary, \
not commentary, not an essay about the excerpts. The finished prose.

How it is built:

- Every excerpt must do work in the paragraph. One supplies the figure, the \
others bend toward it; none is decoration and none is left on the table.
- The likeness carries the sentence. Yoke the remote things by a shared turn — \
a shape, a motion, a reversal — and let the reader feel the distance being \
crossed. The further apart the fields, the more the comparison has to earn.
- The move is from the physical detail to the human case and back. A fact of \
optics or anatomy becomes a proposition about grief, vanity, or the state, and \
the proposition is then paid for with another physical detail.
- The sentences are long and jointed, carrying subordinate clauses, dashes and \
parentheses, and they turn at the end. Humour and pathos in the same breath. \
Where a compound word is wanted and does not exist, coin it.
- Do not name the sources, cite them, number them, or say "these excerpts". No \
title, no preamble, no note about what you did. The paragraph only.

One paragraph, roughly 90 to 160 words.

If the excerpts genuinely refuse each other — no shape they share, nothing to \
cross — do not force a conceit. Write one plain sentence saying the throw \
yields nothing, and stop. That verdict is worth more than a manufactured \
likeness, and a bench that always produces profundity is useless for judging \
which throws to keep.\
"""


#: Same construction, contemporary prose, and much shorter. Brevity is the whole
#: constraint here: the Witz is a single connection, and a modern reader wants it
#: made and then left alone, not decorated.
MODERN = """\
Several excerpts from distant fields have been thrown together under one \
headword. Write the short paragraph that finds what they share.

This is Witz in Jean Paul's sense — the finding of resemblance in remote \
material — but in plain contemporary prose. Not a summary of each excerpt, not \
commentary about them, not an essay. The finished paragraph.

How it is built:

- Every excerpt must do work. One supplies the figure, the others bend toward \
it; none is decoration and none is left on the table.
- One connection, stated once. Find the shape the remote things actually share \
— a mechanism, a reversal, a trade-off — and let the distance between the \
fields do the work. Do not list resemblances; make one.
- Move from the technical detail to what it implies, and stop there. Earn any \
generalisation with the detail that produced it.
- Plain modern sentences. No period pastiche, no archaism, no exclamation. \
Concrete nouns over abstractions. Strip hedging, throat-clearing and \
transitions that carry no information.
- Do not name the sources, cite them, number them, or say "these excerpts". No \
title, no heading, no preamble, no note about what you did. The paragraph only.

**Brevity is the point: 50 to 80 words. One paragraph. If it can be said \
shorter, say it shorter.**

If the excerpts genuinely refuse each other — no shape they share, nothing to \
cross — say so in one plain sentence and stop. A forced connection is worse \
than none, and a bench that always finds something is useless for judging which \
throws to keep.\
"""


#: Which register a corpus asks for.
REGISTERS = {"jean_paul": JEAN_PAUL, "modern": MODERN}
DEFAULT_REGISTER = "modern"


@dataclass(frozen=True)
class Reading:
    """What came back, or why nothing did."""

    text: str
    problem: str


def available() -> bool:
    """Whether a key is present. The button is hidden when it is not."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def read(
    throw: str, *, headword: str = "", lang: str = "en", register: str = DEFAULT_REGISTER
) -> Reading:
    """Ask for a reading of one throw.

    Failures are returned rather than raised: this sits beside a verdict on a
    bench, and a missing key or a network blip should not take the page down.
    """
    if not throw.strip():
        return Reading("", "There is no throw to read yet — generate one first.")
    if not available():
        return Reading("", "Set ANTHROPIC_API_KEY to ask for a reading.")

    try:
        import anthropic
    except ImportError:
        return Reading("", "The anthropic package is not installed in this environment.")

    # The headword is the collision chamber, not a label — naming it tells the
    # writer which likeness the excerpts were filed for in the first place.
    filed = f"Filed under the headword {headword!r}.\n\n" if headword else ""
    system = REGISTERS.get(register, REGISTERS[DEFAULT_REGISTER])
    if lang == "de":
        tongue = (
            "Write the paragraph in German, as he would have."
            if register == "jean_paul"
            else "Write the paragraph in German."
        )
    else:
        tongue = "Write the paragraph in English."

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model(),
            max_tokens=16000,
            system=system,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": f"{filed}{throw}\n\n{tongue}"}],
        )
    except anthropic.APIStatusError as exc:
        return Reading("", f"The model refused or errored ({exc.status_code}): {exc.message}")
    except anthropic.APIConnectionError:
        return Reading("", "Could not reach the API. Check the network.")

    if response.stop_reason == "refusal":
        return Reading("", "The model declined to read this throw.")
    text = "\n\n".join(block.text for block in response.content if block.type == "text")
    return Reading(text.strip(), "" if text.strip() else "The model returned nothing.")
