"""Language pack lookup. Third-party packs register via `register_pack`."""

from __future__ import annotations

from denckring.core.errors import UnknownLanguage
from denckring.core.protocol import LanguagePack
from denckring.lang.en import EnglishPack

_PACKS: dict[str, LanguagePack] = {"en": EnglishPack()}


def get_pack(lang: str) -> LanguagePack:
    """Return the installed pack for a language, or raise `UnknownLanguage`."""
    try:
        return _PACKS[lang]
    except KeyError:
        raise UnknownLanguage(str(lang)) from None


def register_pack(pack: LanguagePack) -> None:
    """Install a pack. Used by the `de` and `fr` extras and by third parties."""
    _PACKS[pack.lang] = pack


__all__ = ["get_pack", "register_pack"]
