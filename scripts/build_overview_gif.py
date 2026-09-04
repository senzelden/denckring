"""Assemble the overview GIF from the frames `overview-gif.mjs` captured.

Split from the recording for one reason: Playwright has no GIF encoder, and
shelling out to one from a `.mjs` script would make that script depend on
whatever happens to be installed. The recording writes PNGs; this turns them
into a GIF; either half can be re-run without the other.

Not part of any gate. It needs a running server, a real Chromium and a 9.6 GB
model to produce its input, so it is a tool a person runs, like
`tests/browser/*.mjs` beside it.

Run with `uv run --with pillow python scripts/build_overview_gif.py <frames> <out.gif>`.
Pillow is not a project dependency and should not become one for this.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

#: Half the stage's 1280x720. Full size gives a file several times larger for
#: detail nobody reads off a looping GIF; half keeps the JSON in the MCP panel
#: legible, which is the smallest text that has to survive.
WIDTH = 640
HEIGHT = 360

#: Milliseconds per distinct frame. Runs of identical frames are collapsed into
#: one frame holding for a multiple of this, rather than written out repeatedly:
#: the recording holds by duplicating, and a GIF can say "wait" far more cheaply
#: than it can store the same picture twenty-six times.
TICK = 90

#: Palette size. 128 was legible once dithering was off; 96 costs about a fifth
#: of the file and nothing a reader notices on a page this flat.
COLORS = 96

#: The longest a single frame may hold. Without a cap the end of a long hold
#: reads as the animation having stopped.
MAX_HOLD = 2200


def _montage(frames: list[Image.Image]) -> Image.Image:
    """Every distinct frame stacked into one image, so the palette is chosen
    from all of them at once rather than from whichever happens to be first.

    Sampled rather than exhaustive: a hundred frames of a two-colour page teach
    the quantiser nothing the first two dozen did not.
    """
    step = max(len(frames) // 24, 1)
    sample = frames[::step]
    strip = Image.new("RGB", (frames[0].width, frames[0].height * len(sample)))
    for index, frame in enumerate(sample):
        strip.paste(frame, (0, index * frames[0].height))
    return strip


def _load(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return image.convert("RGB").resize((WIDTH, HEIGHT), Image.LANCZOS)


def build(frames_dir: Path, out: Path) -> None:
    paths = sorted(frames_dir.glob("*.png"))
    if not paths:
        raise SystemExit(f"no PNG frames in {frames_dir}")

    kept: list[Image.Image] = []
    durations: list[int] = []
    previous_bytes: bytes | None = None
    for path in paths:
        image = _load(path)
        raw = image.tobytes()
        if raw == previous_bytes and durations:
            durations[-1] = min(durations[-1] + TICK, MAX_HOLD)
            continue
        kept.append(image)
        durations.append(TICK)
        previous_bytes = raw

    # A beat at the end, so the loop does not snap round while the last answer
    # is still being read.
    durations[-1] = max(durations[-1], 1800)

    # One palette for every frame, and no dithering.
    #
    # Letting `save` quantise per frame produced visible pink striping across
    # this app's dark ground and left the JSON in the MCP panel barely legible:
    # error-diffusion dithering scatters a flat near-black into two alternating
    # palette entries, which is exactly wrong for a screenshot. A UI is flat
    # colour and small text — the two things dithering damages most — so the
    # palette is built once from a sample of the frames and every frame is
    # mapped onto it with `Dither.NONE`.
    palette = _montage(kept).quantize(colors=COLORS, method=Image.Quantize.MEDIANCUT)
    quantised = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in kept]

    first, *rest = quantised
    first.save(
        out,
        save_all=True,
        append_images=rest,
        duration=durations,
        loop=0,
        # `disposal=2` — restore to background before each frame — and no
        # optimisation. Pillow's optimiser writes partial frames that assume the
        # previous one is still underneath, and every scroll here changes the
        # whole viewport at once, so the deltas composited into torn, smeared
        # text across the catalogue. Correctness first: the file is larger for
        # it, and a legible larger file beats an illegible smaller one.
        disposal=2,
        optimize=False,
    )
    size = out.stat().st_size
    print(
        f"{len(paths)} frames in, {len(kept)} distinct, "
        f"{sum(durations) / 1000:.1f}s, {size / 1_000_000:.1f} MB -> {out}"
    )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: build_overview_gif.py <frames-dir> <out.gif>")
    build(Path(sys.argv[1]), Path(sys.argv[2]))
