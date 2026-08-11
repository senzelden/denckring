"""Language pack lookup.

English is seeded directly so core never depends on its own installed metadata
being readable in order to find its own language. Every other pack — including
the German one that ships in this same wheel — arrives through the
`denckring.lang` entry-point group, which is exactly how a third-party pack
installs.
"""

from __future__ import annotations

from importlib.metadata import entry_points

from denckring.core.errors import UnknownLanguage
from denckring.core.protocol import LanguagePack
from denckring.lang.en import EnglishPack

ENTRY_POINT_GROUP = "denckring.lang"

_PACKS: dict[str, LanguagePack] = {"en": EnglishPack()}
_DISCOVERED = False


def _discover() -> None:
    global _DISCOVERED
    if _DISCOVERED:
        return
    _DISCOVERED = True
    for entry in entry_points(group=ENTRY_POINT_GROUP):
        if entry.name in _PACKS:
            continue
        _PACKS[entry.name] = entry.load()()


def get_pack(lang: str) -> LanguagePack:
    """Return the installed pack for a language, or raise `UnknownLanguage`."""
    _discover()
    try:
        return _PACKS[lang]
    except KeyError:
        raise UnknownLanguage(str(lang)) from None


def register_pack(pack: LanguagePack) -> None:
    """Install a pack directly, bypassing entry-point discovery."""
    _PACKS[pack.lang] = pack


def installed_languages() -> list[str]:
    """Every language with a loadable pack, sorted."""
    _discover()
    return sorted(_PACKS)


__all__ = ["ENTRY_POINT_GROUP", "get_pack", "installed_languages", "register_pack"]
