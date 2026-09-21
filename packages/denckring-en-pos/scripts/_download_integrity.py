"""Verify or record the SHA-256 of a downloaded release input.

A build script that fetches an upstream dataset and never checks what it got
is not reproducible from repository state alone, and a network attacker (the
plain-HTTP Lexique fetch was one concrete case) or an upstream mirror swap can
silently change shipped linguistic behavior (review finding P2-05).

Duplicated across the five distributions that download anything — denckring-fr-data,
denckring-en-data, denckring-de-frequency, denckring-de-wiktionary and
denckring-en-pos — rather than imported from one of them: these are
independent workspace packages that depend on each other only as installed
distributions declared in `pyproject.toml` (e.g. denckring-de-frequency pins
`denckring-de-data` by exact version), never on one another's
`scripts/` directories — no build script in this workspace imports across a
package boundary that way — and this ~15-line function is not worth adding a
new inter-package, build-time-only dependency to establish that pattern.
"""

from __future__ import annotations

import hashlib
import sys


def verify_or_record(data: bytes, *, source: str, expected_sha256: str | None) -> str:
    """Return the SHA-256 of `data`. If `expected_sha256` is given, refuse a
    mismatch loudly rather than silently building from unverified bytes."""
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        print(
            f"{source}: expected sha256 {expected_sha256}, got {digest} — "
            f"refusing to build from unverified data",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return digest
