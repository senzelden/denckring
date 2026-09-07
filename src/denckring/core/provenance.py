"""What produced a verdict, recorded on the verdict itself.

A `Report` said what it decided and nothing about how. Re-running it a year later
needed the package version, which pack answered, and which data that pack was
reading — none of which any output carried, and two of which were not reachable
from Python at all: no pack exposed a version, and `Production` never echoed the
seed it was given, so `apply --seed 7 --json` printed an object not containing 7.

The schema version is deliberately separate from the package version. A caller
parsing these objects cares when their *shape* changes, which is not the same
event as a release, and tying the two would make every patch look like a schema
change to anyone reading the field to decide whether they can still parse it.

Data distributions are a tuple rather than one string because German is three of
them: `denckring-de-data` carries the lexicon, `denckring-de-wiktionary` the
pronunciations and `denckring-de-frequency` the bands, and
`GermanWiktionaryFrequencyPack` layers all three. A single version here would
have to pick one and would be a lie about the other two.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any

from pydantic import BaseModel, Field

#: The shape of `Report` and `Production`, versioned apart from the package.
#: Bump the minor on an added field, the major on one that changes meaning —
#: which the stability promise in the README says will not happen to a field
#: already shipped.
SCHEMA_VERSION = "1.0"

#: What a pack reports when it reads no data files. The three built-in defaults
#: are part of the library, so their content is pinned by the package version
#: already recorded beside them.
NO_DATA: tuple[str, ...] = ()


def _distribution_version(name: str) -> str:
    """A distribution's version, or a marker rather than a raised error.

    A pack naming a distribution that is not installed is a contradiction — it
    could not have loaded its data — but provenance exists to describe a run that
    already happened, and failing to describe it is worse than describing it
    incompletely. `check` must not start raising because metadata is unreadable.
    """
    try:
        return version(name)
    except PackageNotFoundError:  # pragma: no cover - requires a broken install
        return "unknown"


class PackProvenance(BaseModel):
    """Which pack answered, and what it was reading."""

    lang: str
    #: The class, which is what distinguishes `GermanDataPack` from
    #: `GermanWiktionaryFrequencyPack` when both are spelled `de`.
    pack: str
    #: Distribution name to version, empty for a built-in default.
    data: dict[str, str] = Field(default_factory=dict)


class Provenance(BaseModel):
    """How a verdict was reached, as opposed to what it was."""

    denckring: str
    schema_version: str = SCHEMA_VERSION
    pack: PackProvenance
    #: The normalisation policy actually in force, where the procedure has one.
    #: `None` means the procedure does not compare letters and never asked.
    fold_diacritics: bool | None = None
    #: The seed a drawing generator used. `None` on every check, and on the
    #: generators that do not draw.
    seed: int | None = None


def pack_provenance(pack: object, lang: str) -> PackProvenance:
    """Describe an installed pack.

    Read with `getattr` rather than through the `LanguagePack` protocol: that
    protocol is a published contract — the README lists the `denckring.lang`
    entry-point group among the five stable surfaces — and it is
    `runtime_checkable`, so requiring a new member would stop a third-party pack
    satisfying `isinstance`. A pack that predates this reports no data rather
    than failing to load.
    """
    distributions: tuple[str, ...] = getattr(pack, "data_distributions", NO_DATA)
    return PackProvenance(
        lang=lang,
        pack=type(pack).__name__,
        data={name: _distribution_version(name) for name in distributions},
    )


def provenance(pack: object, lang: str, params: Any = None) -> Provenance:
    """Everything reproducing this run needs, gathered at the one place that has it.

    `params` is the parsed parameter model, which is where the fold policy and
    the seed live — both are ordinary fields on mixins that only the procedures
    needing them inherit, so both are read with `getattr` and default to `None`.
    """
    from denckring import __version__

    return Provenance(
        denckring=__version__,
        pack=pack_provenance(pack, lang),
        fold_diacritics=getattr(params, "fold_diacritics", None),
        seed=getattr(params, "seed", None),
    )
