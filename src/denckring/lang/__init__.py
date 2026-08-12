"""Language pack lookup.

English is available as a built-in *default* so core never depends on its own
installed metadata being readable in order to find its own language. Everything
else — including the German pack that ships in this same wheel, and the
`denckring[en]` data package — arrives through the `denckring.lang` entry-point
group, which is exactly how a third-party pack installs.

Precedence runs: explicitly registered pack, then entry point, then built-in
default. That ordering is what lets `denckring-en-data` upgrade English rather
than be shadowed by it.
"""

from __future__ import annotations

from importlib.metadata import entry_points

from denckring.core.errors import DuplicatePack, UnknownLanguage
from denckring.core.protocol import LanguagePack
from denckring.lang.en import EnglishPack

DuplicatePack = DuplicatePack

ENTRY_POINT_GROUP = "denckring.lang"

#: The floor: always present, never dependent on installed metadata.
_DEFAULTS: dict[str, LanguagePack] = {"en": EnglishPack()}
#: Discovered or explicitly registered packs, which take precedence.
_PACKS: dict[str, LanguagePack] = {}
_DISCOVERED = False


#: Where each installed pack came from, so a collision can name both.
_SOURCES: dict[str, str] = {}


def _install(packs: dict[str, LanguagePack], lang: str, pack: LanguagePack, *, source: str) -> None:
    """Install a pack, refusing to choose between two claiming one language."""
    if lang in packs:
        raise DuplicatePack(lang, _SOURCES.get(lang, "an installed pack"), source)
    packs[lang] = pack
    _SOURCES[lang] = source


def _discover() -> None:
    global _DISCOVERED
    if _DISCOVERED:
        return
    _DISCOVERED = True
    for entry in entry_points(group=ENTRY_POINT_GROUP):
        _install(_PACKS, entry.name, entry.load()(), source=entry.value)


def get_pack(lang: str) -> LanguagePack:
    """Return the installed pack for a language, or raise `UnknownLanguage`."""
    _discover()
    pack = _PACKS.get(lang) or _DEFAULTS.get(lang)
    if pack is None:
        raise UnknownLanguage(str(lang))
    return pack


def register_pack(pack: LanguagePack) -> None:
    """Install a pack directly, replacing any already registered for its language."""
    _PACKS[pack.lang] = pack
    _SOURCES[pack.lang] = f"{type(pack).__module__}.{type(pack).__qualname__}"


def installed_languages() -> list[str]:
    """Every language with a loadable pack, sorted."""
    _discover()
    return sorted(set(_PACKS) | set(_DEFAULTS))


__all__ = [
    "ENTRY_POINT_GROUP",
    "DuplicatePack",
    "get_pack",
    "installed_languages",
    "register_pack",
]
