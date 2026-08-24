"""Read apps/explorer/.env, once, and put the explorer's own cartridges on
the library's device search path.

The explorer needs two things a repository must never carry: an API key and a
path to somebody's private corpus. Both are environment variables, and a `.env`
beside the app is the ordinary way to keep them off disk-in-git and out of a
shell history.

Loaded from the app directory rather than the working directory, so it works
the same whether the explorer is started from the repository root, from
`apps/explorer`, or by a supervisor with no cwd of its own. Real environment
variables win: an exported `ANTHROPIC_API_KEY` is a deliberate act and should
not be quietly overridden by a stale file.
"""

from __future__ import annotations

import os
from pathlib import Path

from denckring.core.device import DEVICE_PATH_ENV

#: apps/explorer/, three parents up from src/explorer/env.py.
APP_ROOT = Path(__file__).resolve().parents[2]

#: Devices this app carries and the package deliberately does not. The one
#: cartridge here names Pokemon creatures, which are third-party trademarks;
#: `apps/explorer` is `Private :: Do Not Upload` and the catalogue's data ships
#: under CC BY 4.0, so the file lives on this side of that line. The device
#: file's own header records the reasoning.
DEVICE_DIR = Path(__file__).resolve().parent / "data" / "devices"

_loaded = False


def load() -> None:
    """Idempotent: the CLI and the app module both call it, and `--reload`
    re-imports the app in a subprocess."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    put_devices_on_the_path()
    try:
        from dotenv import load_dotenv
    except ImportError:  # the explorer still runs on the real environment
        return
    load_dotenv(APP_ROOT / ".env", override=False)


def put_devices_on_the_path() -> None:
    """Prepend `DEVICE_DIR` to `DENCKRING_DEVICE_PATH`.

    Prepended rather than assigned, so an operator who has already pointed the
    variable at a cartridge directory of their own keeps it; and idempotent, so
    `--reload`'s re-import (and a test that calls `load` again) does not stack
    the same directory up a dozen times.

    `device.load` reads the variable on every call and resolves the search path
    fresh, so this only has to happen before the first board is loaded rather
    than before the library is imported.
    """
    here = str(DEVICE_DIR)
    existing = [entry for entry in os.environ.get(DEVICE_PATH_ENV, "").split(":") if entry]
    if existing and existing[0] == here:
        return
    os.environ[DEVICE_PATH_ENV] = ":".join([here, *(e for e in existing if e != here)])
