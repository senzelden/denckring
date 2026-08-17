"""Read apps/explorer/.env, once.

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

from pathlib import Path

#: apps/explorer/, three parents up from src/explorer/env.py.
APP_ROOT = Path(__file__).resolve().parents[2]

_loaded = False


def load() -> None:
    """Idempotent: the CLI and the app module both call it, and `--reload`
    re-imports the app in a subprocess."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        from dotenv import load_dotenv
    except ImportError:  # the explorer still runs on the real environment
        return
    load_dotenv(APP_ROOT / ".env", override=False)
