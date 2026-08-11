"""Catalogue quality is a test, not a review."""

import pytest

from denckring.core import catalogue
from denckring.core.protocol import FAMILIES, Meta

ENTRIES = catalogue.load()


@pytest.mark.parametrize("meta", ENTRIES.values(), ids=list(ENTRIES))
def test_row_is_complete(meta: Meta) -> None:
    assert meta.names.get("en"), f"{meta.id} has no English name"
    assert meta.definitions.get("en"), f"{meta.id} has no English definition"
    assert meta.prompt_hints.get("en"), f"{meta.id} has no English prompt hint"
    assert meta.source.strip(), f"{meta.id} has no source"
    assert meta.family in FAMILIES, f"{meta.id} has family {meta.family!r}"


@pytest.mark.parametrize("meta", ENTRIES.values(), ids=list(ENTRIES))
def test_definition_is_a_sentence_not_a_label(meta: Meta) -> None:
    definition = meta.definitions["en"]
    assert len(definition.split()) >= 4, f"{meta.id}: {definition!r} is too terse to be useful"


def test_aliases_are_unique_across_the_catalogue() -> None:
    seen: dict[str, str] = {}
    for meta in ENTRIES.values():
        for alias in meta.aliases:
            key = alias.casefold()
            assert key not in seen, f"{meta.id} and {seen[key]} both claim the alias {alias!r}"
            seen[key] = meta.id


def test_aliases_never_collide_with_an_id() -> None:
    ids = set(ENTRIES)
    for meta in ENTRIES.values():
        clashes = {a for a in meta.aliases if a.casefold() in ids}
        assert not clashes, f"{meta.id} claims alias(es) {clashes} that are already ids"


def test_primary_attributions_name_a_year() -> None:
    """A primary attribution asserts a specific origin, so it must cite one."""
    for meta in ENTRIES.values():
        if meta.attribution == "primary":
            assert any(ch.isdigit() for ch in meta.source), (
                f"{meta.id} claims a primary attribution but its source names no year: "
                f"{meta.source!r} — use 'reference' if the origin is not established"
            )
