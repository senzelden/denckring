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

import contextlib
import hashlib
import json
import weakref
from collections.abc import Mapping
from importlib.metadata import PackageNotFoundError, version
from importlib.resources import files as resource_files
from importlib.resources.abc import Traversable
from typing import Any

from pydantic import BaseModel, Field

from denckring.core.errors import MissingCapability

#: The shape of `Report` and `Production`, versioned apart from the package.
#: Bump the minor on an added field, the major on one that changes meaning —
#: which the stability promise in the README says will not happen to a field
#: already shipped. 1.1 (0.3.2) added `Report.estimated`; 1.2 (0.4.0) added the
#: `ambiguous` value to `Evidence.basis` (ADR 0054), since a parser holding the
#: closed set would refuse it. `tests/test_provenance.py` holds each version to the
#: keys it serialises and to the basis values, so neither can change without this. 1.3
#: (0.5.0) added `Provenance.checkers`, each row that decided the verdict with its
#: `checker_version` (ADR 0061).
SCHEMA_VERSION = "1.3"

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
    #: Content digests (ADR 0060 D4), keyed `graded_words`, `nouns`, `files`. Filled
    #: by `denckring.pack_provenance` only: hashing a lexicon costs far more than a
    #: check, so a `Report`'s copy is always empty rather than slowing every verdict.
    digests: dict[str, str] = Field(default_factory=dict)


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
    #: Row id to `checker_version` for every row that decided this verdict: the row
    #: itself, plus each entry of a composite (ADR 0061).
    checkers: dict[str, int] = Field(default_factory=dict)


def pack_provenance(pack: object, lang: str) -> PackProvenance:
    """Describe an installed pack.

    Read with `getattr` rather than through the `LanguagePack` protocol: that
    protocol is a published contract — the README lists it, and the
    `denckring.lang` entry-point group, among the stable surfaces — and it is
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


#: Keyed weakly on the pack instance: `get_pack` returns the registered singleton,
#: so one hash per process, and a pack replaced by `register_pack` takes its entry
#: with it. Keying on class plus language would go stale when a pack is replaced by
#: another instance of the same class.
_DIGEST_CACHE: weakref.WeakKeyDictionary[object, dict[str, str]] = weakref.WeakKeyDictionary()


def _sha256_json(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _is_bytecode(parts: tuple[str, ...]) -> bool:
    return "__pycache__" in parts or parts[-1].endswith(".pyc")


def _package_files(root: Traversable) -> list[tuple[str, bytes]]:
    """Every file under an import package directory, as (relative POSIX path, bytes).

    Bytecode is skipped; it is written by the interpreter, not shipped.
    """
    found: list[tuple[str, bytes]] = []
    stack: list[tuple[Traversable, tuple[str, ...]]] = [(root, ())]
    while stack:
        node, path = stack.pop()
        for child in node.iterdir():
            child_path = (*path, child.name)
            if child.is_dir():
                stack.append((child, child_path))
            elif not _is_bytecode(child_path):
                found.append(("/".join(child_path), child.read_bytes()))
    return sorted(found)


def _trees_digest(trees: Mapping[str, Traversable]) -> str:
    """Hash `name\0path\0bytes\0` over each named package tree, names then paths sorted.

    Only the package directory is read, never `*.dist-info`: the metadata carries the
    release version, which would move the digest on every release (ADR 0060 D4), and
    its other files differ between a wheel and an editable install.
    """
    digest = hashlib.sha256()
    for name in sorted(trees):
        for path, content in _package_files(trees[name]):
            digest.update(name.encode() + b"\0" + path.encode() + b"\0" + content + b"\0")
    return digest.hexdigest()


def _files_digest(distributions: tuple[str, ...]) -> str | None:
    trees: dict[str, Traversable] = {}
    for name in distributions:
        try:
            trees[name] = resource_files(name.replace("-", "_"))
        except ModuleNotFoundError:  # pragma: no cover - requires a broken install
            return None
    return _trees_digest(trees)


def pack_digests(pack: object) -> dict[str, str]:
    """Content digests of what a pack serves, so a snapshot can key on content.

    Distribution versions move in lockstep with every release, so they cannot say
    whether the data changed. Each value is a lower-case hex SHA-256 and changes
    exactly when its surface's content does:

    - `graded_words`: over `json.dumps(sorted(pack.graded_words().items()),
      ensure_ascii=False, separators=(",", ":"))`, UTF-8 encoded.
    - `nouns`: the same over `sorted(pack.nouns())`.
    - `files`: for each of `pack.data_distributions` sorted by name, each file under
      its import package directory (the distribution name with `-` as `_`), sorted by
      POSIX path relative to that directory and excluding bytecode, feeds
      `name\0path\0bytes\0` into one hash. Nothing in `*.dist-info` is read, so the
      release version does not move it, and a wheel and an editable install of the
      same data agree. The key is omitted with no distributions.

    A surface the pack lacks, or raises `MissingCapability` or `NotImplementedError`
    for, omits its key. Cached per pack instance.
    """
    try:
        cached = _DIGEST_CACHE.get(pack)
    except TypeError:  # pragma: no cover - a pack that cannot be weakly referenced
        cached = None
    if cached is not None:
        return dict(cached)
    digests: dict[str, str] = {}
    for key, method, shape in (
        ("graded_words", "graded_words", lambda r: sorted(r.items())),
        ("nouns", "nouns", sorted),
    ):
        reader = getattr(pack, method, None)
        if reader is None:
            continue
        try:
            digests[key] = _sha256_json(shape(reader()))
        except (MissingCapability, NotImplementedError):
            continue
    distributions: tuple[str, ...] = getattr(pack, "data_distributions", NO_DATA)
    if distributions and (file_digest := _files_digest(distributions)) is not None:
        digests["files"] = file_digest
    with contextlib.suppress(TypeError):  # a pack that cannot be weakly referenced
        _DIGEST_CACHE[pack] = digests
    return dict(digests)


def provenance(
    pack: object, lang: str, params: Any = None, checkers: Mapping[str, int] | None = None
) -> Provenance:
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
        checkers=dict(checkers or {}),
    )
