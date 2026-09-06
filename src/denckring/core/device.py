"""Combinatorial devices: ordered slots of alternatives.

Harsdörffer's five rings, Queneau's ten interchangeable sonnets and Kuhlmann's
Wechselsatz are one structure asked two different questions. The Denckring
*segments* a single word across its slots, because the parts concatenate with
nothing between them. The sonnet machines *select* one alternative per slot,
because the parts are already separated and the count is fixed.

Both are searches for some consistent reading, which is the shape metre, N+7 and
the free monosyllable already take.
"""

from __future__ import annotations

import os
import random
import re
from collections import Counter
from collections.abc import Callable, Sequence
from functools import lru_cache
from importlib.resources import files
from itertools import combinations
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError

from denckring.core.errors import (
    InputTooShort,
    MalformedDevice,
    MalformedFigure,
    UnknownDevice,
    UnknownFigure,
    UnknownLevel,
    counted,
)
from denckring.core.protocol import LanguagePack

DEVICE_DIR = Path(str(files("denckring") / "data" / "devices"))

#: Colon-separated directories searched, in order, before `DEVICE_DIR`. Read at
#: call time rather than cached at import time, so a caller can change it
#: between two calls in the same process — the cache in `load` is keyed to
#: match, see there.
DEVICE_PATH_ENV = "DENCKRING_DEVICE_PATH"


def _device_search_path() -> tuple[Path, ...]:
    """Extra device directories from `DENCKRING_DEVICE_PATH`, then the packaged one.

    Extra directories come first, so a directory earlier on the path shadows
    both `DEVICE_DIR` and any later directory that ships a device of the same
    id. A directory that does not exist, or is not readable, is skipped rather
    than raised on: a stale entry in someone's environment must not break
    loading a device that *is* packaged. `is_dir` itself can raise on a
    directory whose parent is unreadable, which is exactly the same "skip it
    quietly" case, so that is caught here too rather than left to surface from
    deeper inside `load`.
    """
    raw = os.environ.get(DEVICE_PATH_ENV, "")
    # `os.pathsep`, not a literal ":". This variable imitates `PATH` and must
    # split the way `PATH` does — ";" on Windows, where ":" is the drive
    # separator. Splitting on ":" tore `C:\\Users\\...` into "C" and
    # "\\Users\\...", so neither entry was a directory, every extra path was
    # silently dropped, and `DENCKRING_DEVICE_PATH` — a documented feature, see
    # "Bringing your own device" in the README — had never worked on Windows at
    # all. Found when CI ran on windows-latest for the first time.
    extra = [Path(entry) for entry in raw.split(os.pathsep) if entry]
    searchable = []
    for directory in [*extra, DEVICE_DIR]:
        try:
            if directory.is_dir():
                searchable.append(directory)
        except OSError:
            continue
    return tuple(searchable)


#: A bare filename stem: letters, digits, `_` and `-`, nothing else. Every id
#: this package ships, and every id `scripts/new_procedure.py` can generate,
#: matches it — this is not a restriction any real device or figure id needs
#: to test against.
_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def _valid_id(item_id: str) -> bool:
    """Whether `item_id` is safe to interpolate into a filename.

    `directory / f"{item_id}.yaml"` is only as safe as `item_id`:
    `Path.__truediv__` silently discards the left operand when the right is
    absolute, and a `..` segment is never rejected by `Path` at all — so an
    id of `/etc/passwd` or `../../etc/passwd` reads a file `load` never
    searched for and never meant to offer. A bare name rules out both. This
    applies to every id this module reads from a caller, not only a
    cartridge one: `load_figure` shares it, because the same interpolation
    was the same shape before this module ever grew a search path.
    """
    return bool(_ID_PATTERN.fullmatch(item_id))


def _locate(directory: Path, item_id: str) -> Path | None:
    """`{item_id}.yaml` inside `directory`, or None if it is not safely there.

    None is returned — never raised — for every reason the file cannot
    answer `item_id`: the id is not a bare name, the directory cannot be
    listed, the file does not exist, or (belt and braces alongside
    `_valid_id`) the resolved path turns out not to be inside the resolved
    directory after all — which also catches a directory that is itself a
    symlink pointing somewhere unexpected. A caller treats None exactly like
    a missing file: keep searching, or report not-found. That is also the
    right response to a rejected id — a caller asking for `"../x"` is asking
    for a device that does not exist, not for a different kind of error.
    """
    if not _valid_id(item_id):
        return None
    candidate = directory / f"{item_id}.yaml"
    try:
        if not candidate.is_file():
            return None
        resolved_dir = directory.resolve()
        resolved_candidate = candidate.resolve()
    except OSError:
        return None
    try:
        resolved_candidate.relative_to(resolved_dir)
    except ValueError:
        return None
    return candidate


def _safe_reason(exc: Exception) -> str:
    """A short, content-free description of why a device/figure file failed.

    Never includes anything read from the file itself: a YAML parser's
    default message quotes a snippet of the source around the error, and a
    Pydantic `ValidationError`'s default message echoes each offending value
    back — both are exactly the payload `MalformedDevice`/`MalformedFigure`
    exist to keep out of a message a caller might display, log or hand to a
    model.
    """
    if isinstance(exc, yaml.YAMLError):
        return f"invalid YAML ({type(exc).__name__})"
    if isinstance(exc, ValidationError):
        return f"does not match the schema ({len(exc.errors())} error(s))"
    return type(exc).__name__


def _device_ids(directory: Path) -> set[str]:
    """Every device id `directory` offers, or an empty set if it cannot be listed."""
    try:
        return {path.stem for path in directory.glob("*.yaml")}
    except OSError:
        return set()


class DisputedTotal(BaseModel):
    """A count the literature asserts, and who asserts it.

    Kept beside the computed one rather than instead of it. Harsdorffer's rings
    are the case that forces this: 97,209,600 circulates widely and is not
    divisible by 144, so it cannot be a product of rings of 12 and 120 at all,
    and one survey attributes it to Leibniz's own 1666 calculation without a
    primary citation. Recording it as disputed is the only honest option that
    neither adopts it nor pretends it was never claimed.
    """

    value: int
    source: str
    note: str | None = None


class Slot(BaseModel):
    """One ring, or one interchangeable position.

    `line` groups slots that belong to the same line of a multi-line device. It
    defaults to 0, so a device whose YAML never mentions it — Harsdörffer's
    rings, which spell one word — reads as a single line and behaves exactly as
    before. A flap-board composing a six-line poem numbers its slots 0 to 5.
    """

    name: str
    alternatives: list[str]
    optional: bool = False
    line: int = 0

    def matches(self, piece: str) -> bool:
        folded = piece.casefold()
        return any(alternative.casefold() == folded for alternative in self.alternatives)


class Mask(BaseModel):
    """Which of a device's readings are attested, and what to do with the rest.

    Al-Khalil ibn Ahmad al-Farahidi's *Kitab al-Ayn* (8th c.) enumerates every
    ordering of a root's consonants and then marks which are realised and which
    are *muhmal*, neglected. That is the shape this field records: a device plus
    a validity mask, so a generator knows which of its own outputs are real
    without a second pass over them.

    `hold` is the default because it is what al-Khalil does. He does not discard
    the muhmal forms; he enumerates and flags them, and that distinction is the
    intellectual content of the device rather than an implementation detail.
    `drop` is for a caller who wants only the attested readings.

    `source` names the capability that answers, not a file: `lexicon.words` is a
    question a pack answers, and which pack is installed is the caller's business.
    """

    kind: Literal["lexicon"]
    source: str
    unmarked_policy: Literal["hold", "drop"] = "hold"


class Device(BaseModel):
    """An ordered set of slots, and where it comes from.

    Also an **address space**: the slots have unequal lengths, so a reading is an
    integer in a non-uniform base, and `at` and `address` are the two directions
    of that. Pingala's *Chandahsastra* (c. 3rd-2nd c. BCE) names both — *nasta*
    is address to pattern, *uddista* is pattern to address — which makes the
    odometer reading of these devices an attested procedure rather than a modern
    gloss on one. B. van Nooten, "Binary Numbers in Indian Antiquity", *Journal of
    Indian Philosophy* 21.1 (1993): 31-50, defends the binary reading.
    """

    id: str
    name: str
    source: str
    slots: list[Slot]
    mask: Mask | None = None
    #: Counts the literature asserts that the inventory does not support. A field
    #: rather than a comment, because a device whose published totals disagree is
    #: the normal case and the disagreement is worth carrying: the Denckring has
    #: three irreconcilable figures and none of them is the product of its rings.
    disputed_totals: list[DisputedTotal] = Field(default_factory=list)

    @property
    def radix(self) -> list[int]:
        """How many ways each slot can come up, a skip counted as one of them.

        The mixed base the address arithmetic runs in. `combinations` is its
        product, and is kept as its own property because that is the number
        every caller actually asks for.
        """
        return [len(slot.alternatives) + (1 if slot.optional else 0) for slot in self.slots]

    def at(self, address: int) -> list[str]:
        """The reading at this address. Pingala's *nasta*: address to pattern.

        **The first slot is the most significant digit**, so incrementing the
        address turns the last ring — an odometer, and the order the device is
        read in. Stated rather than assumed: sources differ on which end of a
        *prastara* row carries the low-order position, and presenting a choice as
        *the* convention is how a caller ends up with a different device's
        numbering.

        A skipped optional slot reads as `""`, the same as `spin` and `segment`
        report it, and sorts last within its slot so that address 0 is every ring
        at its first alternative rather than every optional ring skipped.
        """
        total = self.combinations
        if not 0 <= address < total:
            raise IndexError(f"{self.id} has {total} readings; {address} is not one of them")
        reading = []
        remaining = address
        for slot, base in zip(self.slots, self.radix, strict=True):
            total //= base
            digit, remaining = divmod(remaining, total)
            reading.append(slot.alternatives[digit] if digit < len(slot.alternatives) else "")
        return reading

    def address(self, reading: Sequence[str]) -> int:
        """This reading's address. Pingala's *uddista*: pattern to address.

        The inverse of `at` on every reading `at` can produce, which is what makes
        the pair a bijection rather than two functions that happen to be related.
        Raises for a reading the device cannot produce, rather than returning some
        nearby address: a wrong answer here is indistinguishable from a right one.
        """
        if len(reading) != len(self.slots):
            raise ValueError(
                f"{self.id} has {len(self.slots)} slots and was given {len(reading)} pieces"
            )
        address = 0
        for slot, base, piece in zip(self.slots, self.radix, reading, strict=True):
            address *= base
            if piece == "" and slot.optional:
                digit = len(slot.alternatives)
            else:
                folded = piece.casefold()
                matches = [
                    index
                    for index, alternative in enumerate(slot.alternatives)
                    if alternative.casefold() == folded
                ]
                if not matches:
                    raise ValueError(f"{slot.name!r} does not carry {piece!r}")
                digit = matches[0]
            address += digit
        return address

    @property
    def combinations(self) -> int:
        """How many readings the device admits, counting a skip as an option.

        An `int`, never a float: a six-line board of six ten-way modules admits
        10^36 poems, which no float can hold exactly and Python's integers can.
        """
        total = 1
        for slot in self.slots:
            total *= len(slot.alternatives) + (1 if slot.optional else 0)
        return total

    @property
    def lines(self) -> list[int]:
        """The line numbers the slots carry, in order. `[0]` for a flat device."""
        return sorted({slot.line for slot in self.slots})

    def for_line(self, line: int) -> Device:
        """The slots of one line, as a device in their own right.

        Returning a `Device` rather than a bare list is what lets `segment`,
        `select`, `spin` and `combinations` be asked about one line without any
        of them learning what a line is.
        """
        return Device(
            id=f"{self.id}#{line}",
            name=f"{self.name}, line {line}",
            source=self.source,
            slots=[slot for slot in self.slots if slot.line == line],
            mask=self.mask,
            # Deliberately not carried: a disputed total is a claim about the
            # whole device, and attaching it to one line would assert the
            # literature disputed a number nobody published.
        )


def from_text(
    text: str,
    pack: LanguagePack,
    *,
    device_id: str,
    name: str,
    slots: int = 5,
    per_slot: int = 8,
    drop_commonest: int = 0,
) -> Device:
    """Build a device whose rings are filled from a text.

    The only shape here with no historical precedent, and the reason it is worth
    having anyway: structure fixed and enumerable, content input-dependent. Every
    other device in this package ships its own contents, so a reader wanting rings
    over *their* material had no way to get any.

    **Not a catalogue row, deliberately.** This catalogue records procedures with
    provenance, and `attribution` offers `primary`, `reference` and `traditional` —
    none of which means "contemporary, with no source". Adding an entry for a
    technique this project invented would put it beside Harsdörffer's rings under
    fields that would have to lie. It is a device constructor instead, and the
    devices it makes are read by the rows that already exist, through the
    `DENCKRING_DEVICE_PATH` cartridge mechanism `load` documents.
    Use `scripts/rings_from_text.py` to write one out.

    **Deterministic, because two callers have to agree.** `check` and `apply` derive
    the same rings from the same text or a generator produces output its own checker
    rejects — the drift ADR 0025 made `apply` inherit `check`'s spine to prevent. So
    the order is total: by falling frequency, ties broken by first appearance.

    `drop_commonest` is this package's whole stoplist, and saying so is more honest
    than shipping one: a real stoplist is per-language data, and dropping the *n*
    most frequent types is the crude standard substitute. At 0 the rings fill with
    function words, which is a faithful reading of the text and rarely the wanted one.

    Words are dealt round-robin rather than in blocks, so every ring spans the
    frequency range. In blocks the first ring would hold the commonest words and the
    last the rarest, and every reading would be one register sliding into another.
    """
    order: dict[str, int] = {}
    counts: Counter[str] = Counter()
    for token in pack.tokenize(text):
        folded = token.casefold()
        counts[folded] += 1
        order.setdefault(folded, len(order))
    ranked = sorted(counts, key=lambda word: (-counts[word], order[word]))
    usable = ranked[drop_commonest:]
    wanted = slots * per_slot
    if len(usable) < wanted:
        raise InputTooShort(
            device_id,
            counted(wanted, "distinct word") + f" after dropping {drop_commonest}",
            counted(len(usable), "distinct word"),
        )
    return Device(
        id=device_id,
        name=name,
        source=(
            f"derived from {name}: the {wanted} most frequent words after the "
            f"{drop_commonest} most frequent, dealt round-robin into {slots} rings"
        ),
        slots=[
            Slot(name=f"ring{index + 1}", alternatives=usable[index:wanted:slots])
            for index in range(slots)
        ],
    )


def load(device_id: str) -> Device:
    """Read a device by id, from `DENCKRING_DEVICE_PATH` or the shipped data.

    `DENCKRING_DEVICE_PATH` is a colon-separated list of directories, read from
    the environment on every call — there is no process-wide setter, so the
    only way to change it is to change the environment. Each directory is
    searched for `{device_id}.yaml` *before* the directory this package ships,
    in the order given, and the first match wins. That makes shadowing a
    packaged device deliberate and available: put a directory ahead of the
    packaged one on the path, give a file in it the same id, and it is what
    `load` returns instead.

    A user-supplied device is data the library reads, nothing more: there is
    no schema versioning beyond what `Device.model_validate` already enforces,
    no record of where a resolved device actually came from, and if it
    shadows a packaged id, the packaged device is not what ran — `load`
    itself has no way to tell a caller that a result came from a shadow
    rather than from the package, so a caller who needs to know must control
    what it puts on the path.

    A directory on the path that does not exist, or cannot be listed, is
    skipped quietly rather than raising, so a stale entry in someone's
    environment does not break loading a device that ships with the package.

    `device_id` must be a bare filename stem (letters, digits, `_` and `-`);
    it is never accepted as a path. A cartridge lives *in* a directory on the
    path — it cannot be addressed by giving `device_id` a separator, `..`, or
    an absolute path to point somewhere else entirely, which `Path` would
    otherwise allow. An id that fails this check is treated exactly like an
    id no directory offers: not found, not a different kind of error.

    Raises `UnknownDevice` naming every id findable across the whole search
    path — the packaged directory and every extra one — not only the
    packaged directory, because that error's job is to say what the caller
    could have said instead. Raises `MalformedDevice` if a matching file
    exists but its content is not readable as a device — invalid YAML, or
    YAML that does not fit the schema — rather than letting the underlying
    parser or validation error escape with a fragment of the file's own
    content in its message.
    """
    search = _device_search_path()
    for directory in search:
        candidate = _locate(directory, device_id)
        if candidate is not None:
            return _load_path(candidate)
    available = sorted(set().union(*(_device_ids(directory) for directory in search)))
    raise UnknownDevice(device_id, available)


@lru_cache(maxsize=8)
def _load_path(path: Path) -> Device:
    """Read and validate one device file. Cached on the resolved path.

    Caching here rather than in `load` is what keeps `DENCKRING_DEVICE_PATH`
    safe to change between two calls for the same `device_id`: `load` resolves
    the search path — and therefore which file answers a given id — on every
    call, uncached, and only the read of one already-resolved file is memoised.
    A cache keyed on `device_id` alone would go stale the moment the
    environment changed and a different file started answering the same id.

    Raises `MalformedDevice` — never a raw `yaml.YAMLError` or Pydantic
    `ValidationError` — because `load` reaching here means `path` came off
    `_locate`, which by now may have resolved to arbitrary user-authored
    YAML rather than only this package's own. Both underlying exceptions
    quote content from the file in their default message; `MalformedDevice`
    does not, and it is what callers already catch as a `DenckringError`.
    """
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        return Device.model_validate(raw)
    except (yaml.YAMLError, ValidationError) as exc:
        raise MalformedDevice(str(path), _safe_reason(exc)) from exc


def segment(text: str, device: Device, *, separator: str = "") -> list[str] | None:
    """Cut `text` into one piece per slot, in order, or return None.

    Slots marked optional may contribute nothing.

    **A word the rings can spell more than one way is read literally first.**
    Matching is case- and ß-insensitive, so the pieces come back spelled as the
    plate spells them and their join need not equal the input: Harsdörffer's
    ring II is the *Anfangsbuchstabe* and carries capitals, so `Bestes` also
    reads as `be` + `S` + `tes`, and `Misslich` as `mi` + `ß` + `lich`. For a
    caller asking only whether the rings can produce a word, any reading will
    do — which is what an earlier version of this docstring said, and it was
    true for `check` alone.

    It was not true for a caller that turns real discs to the reading and
    prints the word beside them. `apps/explorer`'s Denckring scene did exactly
    that and showed `Bestes` in the panel while the discs beside it spelled
    `beStes`, on about 0.15% of draws. So this walks twice: once comparing the
    text as written, and only then case-folded. A reading that reproduces the
    input exactly is never worse, and where one exists the caller gets it.

    The second pass is what keeps a *lowercase* query working — `bestes` typed
    into the bench has no literal reading and must still be producible.

    `separator` is what stands between two neighbouring pieces. It defaults to
    the empty string, which is Harsdörffer's rings: the parts concatenate with
    nothing between them. A board whose flaps carry whole words sets it to a
    space, and the same backtracking walk then splits a line into modules.

    A separator is expected before a piece only if some earlier slot actually
    contributed one, so a skipped optional slot leaves no orphaned separator
    behind — that is what `emitted` tracks. No device this package ships
    reaches that bookkeeping: the rings have optional slots and no separator,
    the flap-board has a separator and no optional slots. It is exercised by a
    synthetic device in `tests/test_poesie_automat.py` rather than by any
    shipped data, because a branch defended in prose and reached by nothing is
    a branch nobody has checked.
    """

    def read(normalise: Callable[[str], str]) -> list[str] | None:
        target = normalise(text)
        joint = normalise(separator)

        def walk(position: int, index: int, emitted: bool) -> list[str] | None:
            if index == len(device.slots):
                return [] if position == len(target) else None
            slot = device.slots[index]
            start: int | None = position
            if emitted and joint:
                start = position + len(joint) if target.startswith(joint, position) else None
            if start is not None:
                # Longest alternatives first, so a greedy-looking reading is preferred
                # and the common case terminates sooner.
                for alternative in sorted(slot.alternatives, key=len, reverse=True):
                    written = normalise(alternative)
                    if target.startswith(written, start):
                        rest = walk(start + len(written), index + 1, True)
                        if rest is not None:
                            return [alternative, *rest]
            if slot.optional:
                rest = walk(position, index + 1, emitted)
                if rest is not None:
                    return ["", *rest]
            return None

        return walk(0, 0, False)

    # Literal first, folded second — and compared against None, not truth: an
    # empty device reading empty text returns `[]`, which `or` would discard as
    # a miss and silently re-walk.
    literal = read(lambda piece: piece)
    return literal if literal is not None else read(str.casefold)


def select(pieces: list[str], device: Device) -> list[bool]:
    """Which pieces sit on their corresponding slot.

    A piece per slot, in order. A shorter or longer text is reported by the
    caller rather than silently truncated here.
    """
    return [slot.matches(piece) for slot, piece in zip(device.slots, pieces, strict=False)]


def spin(device: Device, seed: int | None = None) -> list[str]:
    """Turn every ring at random. Deterministic under a fixed seed."""
    chooser = random.Random(seed)
    turned: list[str] = []
    for slot in device.slots:
        options = [*slot.alternatives, *([""] if slot.optional else [])]
        turned.append(chooser.choice(options))
    return turned


class DeviceParams(BaseModel):
    """Mixed into procedures driven by a combinatorial device."""

    device: str = Field(
        default="harsdoerffer_1651",
        description="Which device to read the slots from.",
    )


FIGURE_DIR = Path(str(files("denckring") / "data" / "figures"))


class Figure(BaseModel):
    """An alphabet read at several levels at once.

    Llull's ternary Ars letters nine principles B to K — J is not used — and the
    same letter names a dignity, a relation, a question, a subject, a virtue or a
    vice depending on the table it is read against. Turning the concentric wheels
    produces chambers of letters; what a chamber *says* depends on the level.

    Unlike a `Device`, whose slots are different sets, a figure draws every
    position from one alphabet, and a chamber is a combination rather than a
    product.
    """

    id: str
    name: str
    source: str
    letters: list[str]
    levels: dict[str, dict[str, str]]

    def level_names(self) -> list[str]:
        return sorted(self.levels)

    def read(self, chamber: str, level: str = "absolute") -> list[str]:
        """Spell a chamber out at one level, or raise if the level is unknown."""
        if level not in self.levels:
            raise UnknownLevel(self.id, level, self.level_names())
        table = self.levels[level]
        return [table[letter] for letter in chamber if letter in table]

    def chambers(self, arity: int = 3) -> list[str]:
        """Every combination of `arity` distinct letters, in alphabet order.

        Computed, never quoted: the count of the printed tabula has not been
        checked against a facsimile, and a figure derived from the letters is
        worth more than one taken from the literature.
        """
        return ["".join(combo) for combo in combinations(self.letters, arity)]


def load_figure(figure_id: str) -> Figure:
    """Read a figure by id from the shipped data.

    `figure_id` is validated exactly as `load`'s `device_id` is — a bare
    filename stem, never a path — and for the same reason: `FIGURE_DIR /
    f"{figure_id}.yaml"` would otherwise let an id of `/etc/passwd` or
    `../../etc/passwd` read a file this function never meant to offer.
    `load_figure` has no search path to shadow through, but the
    interpolation was the same shape, so it gets the same guard via `_locate`
    rather than a second, easier-to-miss copy of it.

    Raises `UnknownFigure` for an id no directory offers, including one that
    fails the bare-name check — a rejected id is asking for a figure that
    does not exist, not for a different kind of error. Raises
    `MalformedFigure`, not a raw YAML or Pydantic error, if a matching file
    exists but cannot be read as a figure.
    """
    path = _locate(FIGURE_DIR, figure_id)
    if path is None:
        raise UnknownFigure(figure_id, sorted(p.stem for p in FIGURE_DIR.glob("*.yaml")))
    return _load_figure_path(path)


@lru_cache(maxsize=8)
def _load_figure_path(path: Path) -> Figure:
    """Read and validate one figure file. Cached on the resolved path.

    `FIGURE_DIR` never changes at runtime, so caching by `figure_id` would be
    just as safe here as caching by path — unlike `_load_path`, this loader
    has no mutable search path to go stale against. Caching by path anyway
    keeps the two loaders the same shape, which is what let this file's
    security fix apply to both from one guard instead of two.
    """
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        # `label` sits alongside the letters in each level; it documents, it does not map.
        raw["levels"] = {
            name: {k: v for k, v in table.items() if k != "label"}
            for name, table in raw["levels"].items()
        }
        return Figure.model_validate(raw)
    except (yaml.YAMLError, ValidationError) as exc:
        raise MalformedFigure(str(path), _safe_reason(exc)) from exc
    except (KeyError, TypeError, AttributeError) as exc:
        raise MalformedFigure(str(path), f"malformed levels table ({type(exc).__name__})") from exc
