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
    "glosses": {"cat": ["petit animal"], "dog": ["animal fidèle"]},
}
PARAMS: dict[str, Any] = {"source": "cat dog"}
PARAMS["data"] = json.dumps(DATA)


def satisfying() -> CaseStrategy:
    return st.just(("petit animal animal fidèle", PARAMS.copy()))


def violating() -> CaseStrategy:
    return st.just(("animal fidèle petit animal", PARAMS.copy()))
