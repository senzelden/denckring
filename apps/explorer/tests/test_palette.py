"""The palette's two structural rules, neither of which a rendered page shows.

`tests/browser/README.md` already records why this suite cannot see CSS at all:
`TestClient` runs no JavaScript and no stylesheet, which is how two unscoped
`.tile` rules sized every board tile wrong for a fortnight. These guards do not
render anything either. They read the stylesheets as text and hold them to the
two decisions that a repaint is most likely to quietly undo.
"""

import re
from pathlib import Path

import pytest

STATIC = Path(__file__).parent.parent / "src" / "explorer" / "static"
SHEETS = ("explorer.css", "reading.css", "stage.css")

#: A colour written anywhere in this stylesheet: hex, rgb(a), hsl(a).
COLOUR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\([^)]*\)|\bhsla?\([^)]*\)")

#: Pure black or pure white with an alpha. These carry no hue, so they read the
#: same against any ground — a drop shadow, the grain wash on the drawer, an
#: inset highlight on a raised key. They are exempt because repainting the app
#: never needs to reach them.
NEUTRAL = re.compile(r"^rgba?\(\s*(?:0,\s*0,\s*0|255,\s*255,\s*255|0 0 0|255 255 255)\s*[,/]")


def _uncommented(name: str) -> str:
    """The sheet with comments blanked but its line numbering intact.

    Blanked rather than stripped: several of these files explain a colour in
    prose right above the rule that sets it, and a comment naming `#14110f` is
    documentation, not a literal anyone can repaint.
    """
    text = (STATIC / name).read_text(encoding="utf-8")
    return re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)


def _tokens() -> dict[str, str]:
    """Every hex-valued custom property declared in `explorer.css`.

    That file is the one every page loads, so it is where the palette lives;
    `stage.css` declares only what a scene adds to it.
    """
    found = {}
    for line in _uncommented("explorer.css").split("\n"):
        match = re.match(r"\s*(--[a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;", line)
        if match:
            found[match.group(1)] = match.group(2)
    return found


def _relative_luminance(colour: str) -> float:
    raw = [int(colour.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lit = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in raw]
    return 0.2126 * lit[0] + 0.7152 * lit[1] + 0.0722 * lit[2]


def contrast(foreground: str, background: str) -> float:
    first, second = _relative_luminance(foreground), _relative_luminance(background)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


def test_a_colour_literal_appears_only_where_a_token_is_declared() -> None:
    """The rule that makes a repaint a repaint, rather than a search.

    Before the risograph palette these three sheets held 88 hex literals with
    only 19 of them in `:root`, plus a second population nobody had counted:
    `rgba()` washes restating a colour by hand. Those were the worse half,
    because they go *stale silently* — `rgba(20, 17, 15, 0.16)` was the ink at
    16% until the ink moved, `rgba(63, 125, 63, 0.15)` a green wash left behind
    on a page with no green in it. Both still rendered, and neither looked like
    a bug until you knew what colour it was supposed to be.

    So: a colour may be written where a custom property is *declared* — in
    `:root`, or in a scene's own block, which is how `.llull-stage` states its
    minium — and nowhere else. Everything downstream references the token, and
    a wash derives with `color-mix` rather than restating its own accent.
    """
    offenders = []
    for name in SHEETS:
        for number, line in enumerate(_uncommented(name).split("\n"), 1):
            if line.strip().startswith("--"):
                continue
            for match in COLOUR.finditer(line):
                value = " ".join(match.group(0).split())
                if NEUTRAL.match(value):
                    continue
                offenders.append(f"{name}:{number}  {value}  in  {line.strip()[:60]}")
    assert offenders == [], "colour literals outside a token declaration:\n" + "\n".join(offenders)


def test_the_two_pinks_keep_the_contrast_that_is_the_reason_for_two() -> None:
    """`--rubric` and `--rubric-ink` are one ink printed once and twice.

    A risograph's fluorescent pink is a light ink. Measured on the stock it is
    2.76:1 — fine for a rule, a border or a wash, and unreadable as running
    text, which is what every pink mark in this app actually is: a verdict.
    `.verdict.fail .verdict-word` is the case that matters.

    The pair is the sort of thing a later reader collapses back into one token
    for tidiness, so the distinction is asserted rather than only explained: the
    bright ink must stay too light to set text on paper, and the overprinted one
    must clear AA. If they ever both pass, one of them is redundant and the
    comment above them has gone false.
    """
    token = _tokens()
    paper, case = token["--paper"], token["--case"]

    assert contrast(token["--rubric"], paper) < 4.5, (
        "--rubric now reads on paper, so --rubric-ink has no reason to exist"
    )
    assert contrast(token["--rubric-ink"], paper) >= 4.5
    # And the bright one earns its keep on the dark ground, where the
    # overprinted ink would sink into the case.
    assert contrast(token["--rubric"], case) >= 3.0
    assert contrast(token["--rubric-ink"], case) < contrast(token["--rubric"], case)


@pytest.mark.parametrize(
    ("name", "ground", "floor"),
    [
        # Running text, both grounds: AA.
        ("--ink", "--paper", 4.5),
        ("--ink-mid", "--paper", 4.5),
        ("--ink-soft", "--paper", 4.5),
        ("--lead", "--case", 4.5),
        ("--lead-bright", "--case", 4.5),
        # Marks and large type: AA large.
        ("--ink-faint", "--well", 3.0),
        ("--lead-dim", "--case", 3.0),
        ("--pass", "--paper", 4.5),
        ("--preprint", "--paper", 4.5),
        ("--warn-ink", "--warn-well", 4.5),
    ],
)
def test_each_step_of_a_scale_reads_on_the_ground_it_is_for(
    name: str, ground: str, floor: float
) -> None:
    """`--ink-*` darkens on paper and `--lead-*` dims on the case, and the two
    are not interchangeable.

    The scales exist because the same warm greys used to be written into rules
    on both grounds with nothing saying which was which — `.sort-face` at
    #4f4841 is a case grey, `.sort.is-set .sort-face` at #9a8f7e a paper one.
    Swapping a value between them costs no test and produces a page somebody
    cannot read, so each step is pinned to the ground it was picked against.

    `--ink-soft` was measured at 4.28 on the first pass of the risograph stock
    and darkened to clear this; that is the whole reason the floor is here and
    not in a comment.
    """
    token = _tokens()
    measured = contrast(token[name], token[ground])
    assert measured >= floor, f"{name} on {ground} is {measured:.2f}, below {floor}"


def test_the_denckring_hub_sets_its_labels_in_the_ink_it_can_carry() -> None:
    """The one place a token's contrast is decided by an SVG fill.

    `--ring-0` is `--rubric`, so the Denckring's hub is painted in the bright
    ink — and the bright ink is light. The labels sat on it in `--paper` at
    1.95:1: visible, unreadable, and invisible to every other guard here,
    because neither colour is wrong on its own and the pairing only happens
    inside a `fill:`. Caught by opening the scene, which is the second time
    this app has needed an eye rather than a test, so it gets a test.
    """
    token = _tokens()
    hub = token["--rubric"]  # --ring-0 is declared as var(--rubric) in stage.css
    stage = _uncommented("stage.css")

    assert "--ring-0: var(--rubric);" in stage, "the hub is no longer the bright ink"
    rule = stage.split(".ring-part-hub {", 1)[1].split("}", 1)[0]
    assert "fill: var(--ink);" in rule, rule
    assert contrast(token["--ink"], hub) >= 4.5
    assert contrast(token["--paper"], hub) < 3.0, (
        "paper now reads on the hub, so the comment explaining why it does not is false"
    )


def test_a_fill_of_the_bright_ink_carries_type_that_reads_on_it() -> None:
    """The general form of the bug the Denckring hub was one instance of.

    `--rubric` is light, so *filling* with it inverts which ink reads on top.
    Three rules had inherited `--paper` onto a pink fill and each was a control
    somebody uses: the hover state of every button in the app, the word
    ladder's changed letter, and the calculator's C key. All measured about
    1.9:1, all still looked deliberate.

    The invariant has no exception list: a rule that fills with the bright ink
    states its own `color`, and that colour clears AA against it. The gauge bar
    holds no type and states one anyway, which costs a line and means this test
    never needs to know which fills carry text.
    """
    token = _tokens()
    fills, offenders = 0, []
    for name in SHEETS:
        sheet = _uncommented(name)
        depth, start = 0, None
        lines = sheet.split("\n")
        for number, line in enumerate(lines, 1):
            if "{" in line and depth == 0 and not line.strip().startswith("@"):
                start = number
            depth += line.count("{") - line.count("}")
            if depth == 0 and start is not None:
                block = "\n".join(lines[start - 1 : number])
                if re.search(r"background(-color)?:\s*var\(--rubric\)", block):
                    fills += 1
                    colour = re.search(r"\n\s*color:\s*var\((--[a-z0-9-]+)\);", block)
                    if colour is None:
                        offenders.append(f"{name}:{start} fills with --rubric and sets no colour")
                    elif contrast(token[colour.group(1)], token["--rubric"]) < 4.5:
                        offenders.append(
                            f"{name}:{start} sets {colour.group(1)} on --rubric at "
                            f"{contrast(token[colour.group(1)], token['--rubric']):.2f}"
                        )
                start = None
    assert fills >= 4, f"only found {fills} pink fills; the scan is not matching rules"
    assert offenders == [], "\n".join(offenders)
