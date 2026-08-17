import pytest

from denckring.core.errors import UnknownLanguage
from denckring.lang import get_pack, installed_languages


def test_english_is_available_without_entry_point_metadata() -> None:
    assert get_pack("en").lang == "en"


def test_installed_languages_reports_what_is_loadable() -> None:
    assert "en" in installed_languages()


def test_unknown_language_still_raises() -> None:
    with pytest.raises(UnknownLanguage):
        get_pack("xx")


def test_two_packs_claiming_one_language_raise_rather_than_one_winning() -> None:
    """Silently taking whichever loaded first is the failure ADR 0004 forbids."""
    from denckring.core.protocol import LanguagePack
    from denckring.lang import DuplicatePack, _install
    from denckring.lang.en import EnglishPack

    installed: dict[str, LanguagePack] = {}
    _install(installed, "en", EnglishPack(), source="first")
    with pytest.raises(DuplicatePack, match="first"):
        _install(installed, "en", EnglishPack(), source="second")


def test_german_is_a_default_so_a_data_pack_can_override_it() -> None:
    """A data distribution claiming `de` must win, not collide.

    German shipped as an entry point (ADR 0010). Two entry points claiming one
    language raise DuplicatePack, so `pip install denckring[de]` would have
    broken on first use.
    """
    from denckring.lang import _DEFAULTS

    assert "de" in _DEFAULTS, "German must be a default for a data pack to override it"


def test_core_declares_no_language_entry_points() -> None:
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "pyproject.toml"
    manifest = tomllib.loads(root.read_text(encoding="utf-8"))
    groups = manifest["project"].get("entry-points", {})
    assert "denckring.lang" not in groups, (
        "core must not claim a language by entry point; a data pack could not override it"
    )


def test_the_german_data_pack_overrides_the_core_pack_when_installed() -> None:
    """The whole point of Task 1: an entry point beats a default, no collision."""
    pytest.importorskip("denckring_de_data")
    from denckring.lang.base import NOUNS

    pack = get_pack("de")
    assert NOUNS in pack.capabilities, "the data pack did not win over the core pack"
