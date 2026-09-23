"""Declared-data examples; no claim of an attested literary translation."""

import json
from typing import Any

from hypothesis import strategies as st

from strategies import CaseStrategy

DATA = {
    "version": "supplied-bilingual-v1",
    "source_language": "en",
    "target_language": "fr",
    "provenance": "constructed test data; not a verified bilingual dictionary",
    "alphabet": ["a", "b", "c"],
    "source_pronunciations": {"cat": ["a", "b"]},
    "target_pronunciations": {"chat": ["a", "b"], "mot": ["a", "c"]},
}
PARAMS: dict[str, Any] = {"source": "cat", "max_distance": 0}
PARAMS["data"] = json.dumps(DATA)


def satisfying() -> CaseStrategy:
    return st.just(("chat", PARAMS.copy()))


def violating() -> CaseStrategy:
    return st.just(("mot", PARAMS.copy()))
