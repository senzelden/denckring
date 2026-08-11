import pytest

from denckring.core import catalogue
from denckring.core.errors import UnknownProcedure
from denckring.core.protocol import Meta


def test_loads_every_row_as_meta() -> None:
    entries = catalogue.load()
    assert entries
    assert all(isinstance(m, Meta) for m in entries.values())


def test_row_key_matches_its_id() -> None:
    for key, meta in catalogue.load().items():
        assert key == meta.id


def test_get_returns_a_known_entry() -> None:
    meta = catalogue.get("lipogram")
    assert meta.kind == "restrictive"
    assert "en" in meta.languages
    assert meta.source


def test_get_raises_on_unknown_id() -> None:
    with pytest.raises(UnknownProcedure):
        catalogue.get("wobble")


def test_every_entry_has_an_english_name_definition_and_source() -> None:
    for meta in catalogue.load().values():
        assert meta.names.get("en")
        assert meta.definitions.get("en")
        assert meta.source
        assert meta.prompt_hints.get("en")
