"""Language pack lookup.

English, German and French are available as built-in *defaults* so core never
depends on its own installed metadata being readable in order to find its own
languages. Data distributions — `denckring[en]`, `denckring[de]`,
`denckring[fr]` — arrive through the `denckring.lang` entry-point group, which
is exactly how a third-party pack installs, and take precedence over the
defaults they upgrade. All three languages now have one; French's arrived last
(ADR 0032) and carries a lexicon only, so the core default below is still what
answers every syllabic and phonetic question in French.

Precedence runs: explicitly registered pack, then entry point, then built-in
default. That ordering is what lets `denckring-en-data` upgrade English rather
than be shadowed by it.
"""

from __future__ import annotations

import threading
from importlib.metadata import entry_points

from denckring.core.errors import DuplicatePack, UnknownLanguage
from denckring.core.protocol import LanguagePack
from denckring.lang.de import GermanPack
from denckring.lang.en import EnglishPack
from denckring.lang.fr import FrenchPack

DuplicatePack = DuplicatePack

ENTRY_POINT_GROUP = "denckring.lang"

#: The floor: always present, never dependent on installed metadata. German sits
#: here beside English so that `denckring-de-data` can override it the way
#: `denckring-en-data` overrides English. It was an entry point until a second
#: distribution claiming `de` proved that two entry points for one language
#: raise DuplicatePack. Amends ADR 0010. French joins for the same reason plus
#: one more: `Lang` has always been `Literal["en", "de", "fr"]`, so `"fr"` was
#: a language the type admitted and this registry could not serve.
_DEFAULTS: dict[str, LanguagePack] = {"en": EnglishPack(), "de": GermanPack(), "fr": FrenchPack()}
#: Discovered or explicitly registered packs, which take precedence.
_PACKS: dict[str, LanguagePack] = {}
_DISCOVERED = False
_LOCK = threading.RLock()


#: Where each installed pack came from, so a collision can name both.
_SOURCES: dict[str, str] = {}


def _is_discovered() -> bool:
    """Read `_DISCOVERED` through a call, not a bare name.

    `_discover` checks this twice — once before the lock, once after — and a
    bare `if _DISCOVERED:` read twice in a row is, to mypy's single-threaded
    model, the same value both times, so the second check's `return` gets
    flagged `[unreachable]` under this project's `warn_unreachable`. It is
    reachable: another thread can set `_DISCOVERED` between the two reads.
    Routing the read through a function call mypy does not inline sidesteps
    the false positive without silencing real unreachable-code findings
    elsewhere with a blanket ignore. Same fix as `core/registry.py`.
    """
    return _DISCOVERED


def _install(
    packs: dict[str, LanguagePack],
    lang: str,
    pack: LanguagePack,
    *,
    source: str,
    sources: dict[str, str],
) -> None:
    """Install a pack, refusing to choose between two claiming one language.

    `sources` is required, not defaulted to the real module-global
    `_SOURCES`: `_discover` is the one production caller and always passes
    its own `local_sources` dict, so the `sources=None` branch that fell
    back to `_SOURCES` was reachable only from a test — and reaching it
    wrote into the real global as a side effect (issue #18 item 3).
    """
    if lang in packs:
        raise DuplicatePack(lang, sources.get(lang, "an installed pack"), source)
    packs[lang] = pack
    sources[lang] = source


def _discover() -> None:
    """Load every `denckring.lang` entry point once, under a lock.

    Builds into local dicts and publishes into `_PACKS`/`_SOURCES` only after
    every entry point has loaded without raising: a broken third-party pack
    fails loudly on every call rather than being silently and permanently
    half-installed, and a concurrent second caller blocks on `_LOCK` instead of
    observing a partial `_PACKS` (review finding P1-01). No explicit rollback
    is needed here, unlike the procedure registry: nothing touches the module
    globals until the loop has finished, because entry points do not register
    themselves as an import side effect the way procedures do.
    """
    global _DISCOVERED
    if _is_discovered():
        return
    with _LOCK:
        if _is_discovered():
            return
        local_packs: dict[str, LanguagePack] = {}
        local_sources: dict[str, str] = {}
        for entry in entry_points(group=ENTRY_POINT_GROUP):
            _install(
                local_packs, entry.name, entry.load()(), source=entry.value, sources=local_sources
            )
        # setdefault, not update: an explicitly register_pack()'d entry must win
        # over an entry-point pack claiming the same language, per the module
        # docstring's precedence. `dict.update` would silently invert that for
        # any caller who registered before discovery's first, lazy trigger
        # (review: whole-branch finding on P1-01's rollback rewrite).
        for lang, pack in local_packs.items():
            _PACKS.setdefault(lang, pack)
        for lang, source in local_sources.items():
            _SOURCES.setdefault(lang, source)
        _DISCOVERED = True


def get_pack(lang: str) -> LanguagePack:
    """Return the installed pack for a language, or raise `UnknownLanguage`.

    Takes a bare `str`, not `Lang`, deliberately (ADR 0044): `Lang` stays a
    closed three-member `Literal`, so this loads a pack registered under any
    id — `"es"`, say — without error. Such a pack is loadable but functionally
    invisible everywhere a typed catalogue surface (`Meta.names`,
    `Meta.definitions`, `Description.runs_in`) is built against `Lang` instead.
    """
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
