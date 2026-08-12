"""Catalogue quality is a test, not a review."""

import pytest

from denckring.core import catalogue
from denckring.core.protocol import ATTESTATIONS, CHECKABILITIES, FAMILIES, Meta

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


def test_every_row_declares_checkability() -> None:
    for meta in ENTRIES.values():
        assert meta.checkability in CHECKABILITIES, f"{meta.id} has {meta.checkability!r}"


def test_source_relative_rows_are_not_marked_self() -> None:
    """A row whose definition says 'of a source' cannot be decidable alone."""
    for meta in ENTRIES.values():
        definition = meta.definitions["en"].casefold()
        if "of a source" in definition or "of an existing" in definition:
            assert meta.checkability != "self", (
                f"{meta.id} is defined against a source text but claims to be "
                f"decidable from the text alone"
            )


def test_every_row_declares_attestation() -> None:
    for meta in ENTRIES.values():
        assert meta.attested in ATTESTATIONS, f"{meta.id} has {meta.attested!r}"


def test_author_stated_rows_name_a_source_with_a_year() -> None:
    """Claiming the author set the rule down means pointing at where."""
    for meta in ENTRIES.values():
        if meta.attested == "author-stated":
            assert any(ch.isdigit() for ch in meta.source), (
                f"{meta.id} says the author stated the rule but its source names no "
                f"year: {meta.source!r}"
            )
