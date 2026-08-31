"""Write a device whose rings are filled from a text of your own.

    python scripts/rings_from_text.py notes.txt --out ~/.denckring/devices
    DENCKRING_DEVICE_PATH=~/.denckring/devices denckring apply poesie_automat -p device=notes

Every device this package ships carries its own contents — Harsdörffer's five
rings, Enzensberger's flap-board — so a reader wanting rings over *their* material
had no way to get any. This writes one, in the format `denckring.core.device.load`
already reads from `DENCKRING_DEVICE_PATH`.

It is a contributor tool and stays outside the package, like
`scripts/new_procedure.py`: it writes files a person then chooses to use, and
nothing at runtime calls it.

**No catalogue row goes with it, deliberately.** See `device.from_text`, which is
where the derivation and that decision are documented.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from denckring.core.device import from_text
from denckring.core.errors import DenckringError
from denckring.lang import get_pack


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", type=Path, help="The text to draw the rings from.")
    parser.add_argument(
        "--out", type=Path, default=Path("."), help="Directory to write the device into."
    )
    parser.add_argument("--id", help="Device id. Defaults to the text file's stem.")
    parser.add_argument("--lang", default="en", help="Which pack tokenises the text.")
    parser.add_argument("--slots", type=int, default=5, help="How many rings.")
    parser.add_argument("--per-slot", type=int, default=8, help="Words on each ring.")
    parser.add_argument(
        "--drop-commonest",
        type=int,
        default=0,
        help=(
            "Skip this many of the most frequent words. This package ships no "
            "stoplist; dropping the commonest types is the crude substitute, and "
            "at 0 the rings fill with function words."
        ),
    )
    args = parser.parse_args()

    # `id` is interpolated into a filename by `load`, which validates it as a bare
    # stem. Deriving it from the file's stem rather than its path keeps it one.
    device_id = args.id or args.text.stem
    try:
        device = from_text(
            args.text.read_text(encoding="utf-8"),
            get_pack(args.lang),
            device_id=device_id,
            name=args.text.name,
            slots=args.slots,
            per_slot=args.per_slot,
            drop_commonest=args.drop_commonest,
        )
    except (OSError, DenckringError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    written = args.out / f"{device_id}.yaml"
    written.write_text(
        yaml.safe_dump(device.model_dump(exclude_none=True), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"{written}: {device.combinations} readings over {len(device.slots)} rings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
