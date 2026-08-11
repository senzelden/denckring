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
