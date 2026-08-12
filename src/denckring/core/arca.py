"""Pattern tables indexed by prosody.

Kircher's *Arca musarithmica* is a box of rods carrying numbered patterns. You
take a phrase, count its syllables, choose the tablet — the *pinax* — for that
count, and draw a column from it. Kircher's columns are pitches and rhythms, and
he advertises that an *amusos*, someone with no musical training at all, can set
correct four-part music in any language this way.

The music is not the transferable part. What carries over is the indexing: give a
passage its prosodic profile, then draw from a table keyed by that profile. So
patterns here are opaque strings and this module never reads one. Put Kircher's
numbers in and you get his machine; put stress patterns or rhyme schemes in and
you get something else with the same bones.

No table ships. Kircher's own pinakes run to many pages of Book VIII and have not
been transcribed into anything this project could verify.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from denckring.core.errors import MalformedTable

__all__ = ["DEFAULT_SYNTAGMA", "Pinakes", "parse"]

#: Kircher's first syntagma is plain homophony, the second florid counterpoint.
#: Which one a table means is the table's business; this is only the default key.
DEFAULT_SYNTAGMA = "1"


@dataclass(frozen=True)
class Pinakes:
    """Pattern tablets, keyed by syntagma and then by syllable count."""

    syntagmata: dict[str, dict[int, list[str]]]
    tones: list[str] = field(default_factory=list)
    source: str | None = None

    def syntagma_names(self) -> list[str]:
        return sorted(self.syntagmata)

    def patterns(self, syllables: int, syntagma: str = DEFAULT_SYNTAGMA) -> list[str]:
        """Every pattern offered for a phrase of this length, or nothing."""
        return list(self.syntagmata.get(syntagma, {}).get(syllables, []))

    def lengths(self, syntagma: str = DEFAULT_SYNTAGMA) -> list[int]:
        """The syllable counts this table can set at all."""
        return sorted(self.syntagmata.get(syntagma, {}))


def parse(text: str) -> Pinakes:
    """Read a pattern table from JSON.

    Either `{"6": ["…"], "8": ["…"]}` for a single tablet, or the fuller form
    with `syntagmata`, `tones` and a `source` so a table can carry its own
    provenance.
    """
    stripped = text.strip()
    if not stripped:
        raise MalformedTable("it is empty")
    try:
        raw: Any = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise MalformedTable(f"it is not valid JSON ({exc.msg})") from exc
    if not isinstance(raw, dict) or not raw:
        raise MalformedTable("it is not an object of pattern tablets")

    if "syntagmata" in raw:
        tablets, tones, source = raw["syntagmata"], raw.get("tones", []), raw.get("source")
    else:
        tablets, tones, source = {DEFAULT_SYNTAGMA: raw}, [], None

    syntagmata: dict[str, dict[int, list[str]]] = {}
    for name, tablet in tablets.items():
        if not isinstance(tablet, dict):
            raise MalformedTable(f"syntagma {name!r} is not a mapping of length to patterns")
        by_length: dict[int, list[str]] = {}
        for length, patterns in tablet.items():
            try:
                count = int(length)
            except (TypeError, ValueError) as exc:
                raise MalformedTable(f"{length!r} is not a syllable count") from exc
            if isinstance(patterns, str):
                patterns = [patterns]
            if not patterns:
                raise MalformedTable(f"length {count} offers no patterns")
            by_length[count] = [str(p) for p in patterns]
        syntagmata[str(name)] = by_length
    if not any(syntagmata.values()):
        raise MalformedTable("it holds no patterns")
    return Pinakes(syntagmata=syntagmata, tones=[str(t) for t in tones], source=source)
