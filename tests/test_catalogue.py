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


def test_the_rows_that_decline_a_stress_model_say_so() -> None:
    """ADR 0040 D4 declines to widen the stress model and pays for that in the
    catalogue instead. A row that quietly rejects its own canonical examples and
    does not say why is the defect this asserts against."""
    assert "sprung rhythm" in (catalogue.get("curtal_sonnet").notes or "")
    assert "accentual" in (catalogue.get("elegiac_couplet").notes or "")
