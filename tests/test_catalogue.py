import pytest
from pydantic import ValidationError

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


def test_a_caller_cannot_mutate_the_shared_catalogue_entry() -> None:
    """P2-01: catalogue.get() must not hand back a mutable shared object."""
    meta = catalogue.get("lipogram")
    with pytest.raises((AttributeError, TypeError)):
        meta.requires.append("sentinel.capability")  # type: ignore[attr-defined]


def test_reassigning_a_catalogue_entry_field_is_refused() -> None:
    meta = catalogue.get("lipogram")
    with pytest.raises(ValidationError):
        meta.requires = ()


def test_mutating_one_call_result_does_not_affect_another() -> None:
    """`catalogue.get()` hands every caller the *same* cached `Meta` object
    (P2-01, see `load()`'s `lru_cache`) — so object separation cannot be what
    protects one caller's view from another's mutation, because there is no
    separation. The freeze is the only thing standing between them. Fetching
    the entry twice and comparing for equality (the previous body of this
    test) stays true whether or not `Meta` is frozen, because nothing ever
    attempts a mutation — it cannot fail for the reason it exists. This
    attempts one, through `first`, and checks that `second` — a second
    caller's view of the identical object — never saw it take effect."""
    first = catalogue.get("lipogram")
    second = catalogue.get("lipogram")
    assert first is second, "P2-01 promises the same cached object, not merely an equal one"
    original = first.requires
    with pytest.raises(ValidationError):
        first.requires = ("sentinel.capability",)
    assert second.requires == original
