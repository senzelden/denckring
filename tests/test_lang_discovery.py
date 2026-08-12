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
