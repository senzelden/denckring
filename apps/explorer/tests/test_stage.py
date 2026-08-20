"""The stage. Appearance is not tested; the claims underneath it are."""

from __future__ import annotations

from explorer import stage
from explorer.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _label(alternatives: list[str], index: int) -> str:
    """What a disc shows at a given index — the same model the scene's own
    script uses to turn the rings. A real alternative in range; one further
    blank position, past the end, for a ring that may contribute nothing,
    exactly as the paper rings themselves carry a blank for the prefix and
    suffix. The per-ring index is the truth on this scene now, not whatever
    text happens to be painted on screen, so this is what a Python test can
    pin without a browser."""
    return alternatives[index] if index < len(alternatives) else ""


def test_the_index_lists_every_scene() -> None:
    response = client.get("/stage")
    assert response.status_code == 200
    for scene in stage.SCENES:
        assert scene.title in response.text


def test_every_scene_names_a_real_procedure() -> None:
    """A scene dramatising a procedure that is not registered would be a scene making
    a claim the library cannot back."""
    from denckring.core.registry import all_procedures

    registered = set(all_procedures())
    assert {scene.procedure_id for scene in stage.SCENES} <= registered


def test_chrome_off_removes_the_caption() -> None:
    """Recording wants the stage and nothing else."""
    with_chrome = client.get("/stage")
    without = client.get("/stage?chrome=off")
    assert "stage-caption" in with_chrome.text
    assert "stage-caption" not in without.text


def test_the_rings_carry_the_transcribed_counts() -> None:
    """Cramer's transcription has 49/60/12/120/23, where Harsdörffer's own text
    announces 48/50/12/120/24. The scene shows what the data has, not what the book
    claims — the catalogue row records both and adjusts neither."""
    rings = stage.rings()
    assert [len(slot.alternatives) for slot in rings.slots] == [49, 60, 12, 120, 23]


def test_the_scene_shows_the_true_count_beside_the_famous_one() -> None:
    rings = stage.rings()
    assert rings.claimed == 97_209_600
    assert rings.combinations != rings.claimed


def test_a_word_turned_from_the_rings_satisfies_the_procedure() -> None:
    """The scene's claim: what comes off these rings is a denckring word."""
    from denckring import check
    from denckring.core.protocol import Constructive
    from denckring.core.registry import get

    procedure = get("denckring")
    # `get` is typed as the base class, which has no `apply` — ADR 0002 keeps it
    # off `BaseProcedure` because it is optional. Narrow once, here.
    assert isinstance(procedure, Constructive)
    word = procedure.apply("", lang="en")
    assert check("denckring", word).satisfied is True


def test_the_denckring_scene_renders() -> None:
    response = client.get("/stage/denckring")
    assert response.status_code == 200
    assert "ring-0" in response.text


def test_the_rings_show_a_valid_word_on_first_paint() -> None:
    """The hidden field is assembled by JS from the per-ring index — the single
    source of truth for what the discs show and what gets checked, on first
    paint, after a manual turn and after a spin alike (see the two tests below
    for the latter two). Nothing server-side pre-fills it. What this can test
    without a browser is the claim first paint makes: every ring starts at
    index 0, which is always a real alternative, so reading inward to outward
    already spells a denckring word — "Read it" has something real to check
    the moment the page appears."""
    from denckring import check

    word = "".join(_label(slot.alternatives, 0) for slot in stage.rings().slots)
    assert check("denckring", word).satisfied is True


def test_a_manual_turn_still_spells_a_denckring_word() -> None:
    """A click on one disc advances only that ring's index by one, the others
    holding. Any index for any ring — including the blank position an
    optional ring carries past its last real alternative — still spells
    something the rings could have produced: one alternative, or a blank
    where the ring allows it, chosen per slot in order, which is exactly what
    device.segment() (and so `check`) accepts, regardless of which specific
    index a click happened to land on."""
    from denckring import check

    slots = stage.rings().slots
    for ring_index, slot in enumerate(slots):
        total = len(slot.alternatives) + (1 if slot.optional else 0)
        # A small turn, and turning all the way round to the blank a ring
        # allows (or, for a ring with no blank, its last real alternative).
        for turned_index in (1, total - 1):
            word = "".join(
                _label(other.alternatives, turned_index if i == ring_index else 0)
                for i, other in enumerate(slots)
            )
            assert check("denckring", word).satisfied is True, (slot.name, turned_index)


def test_a_spin_lands_the_discs_on_the_word_that_was_checked() -> None:
    """ "Turn them for me" asks the library for a word and walks the discs to it
    with stage.pieces_for() — the same segmentation the scene's script uses to
    pick each disc's target index from the piece the server sent back. The
    invariant this pins: reassembling those pieces, inward to outward, must
    give back exactly the word `check` was asked about — the discs and the
    checked word can never disagree, including after a spin."""
    from denckring import check
    from denckring.core.protocol import Constructive
    from denckring.core.registry import get

    procedure = get("denckring")
    assert isinstance(procedure, Constructive)
    word = procedure.apply("", lang="en")
    pieces = stage.pieces_for(word)
    assert pieces is not None
    assert "".join(pieces) == word
    assert check("denckring", word).satisfied is True


def test_the_harsdoerffer_quotation_is_reproduced_exactly() -> None:
    """Byte-for-byte, virgule and ellipsis included — modernising the spelling,
    "fixing" Reimwörter or swapping the slash for a comma would be exactly the
    liberty this project refuses to take with its data everywhere else."""
    response = client.get("/stage/denckring")
    normalised = " ".join(response.text.split())
    assert (
        "hat … seinen Gebrauch in Erfindung der Reimwörter / wann man die Reimsilben "
        "auf dem dritten und vierten Ring suchet und die Reimbuchstaben auf dem zweyten "
        "Ring darzu drehet"
    ) in normalised


def test_the_quotation_is_attributed_without_a_page_number() -> None:
    """The catalogue's p. 517 is the page of the device plate; the sources that
    carry this sentence give no page for it, so citing one would be exactly
    the false precision this project refuses elsewhere."""
    response = client.get("/stage/denckring")
    normalised = " ".join(response.text.split())
    assert "Deliciae Physico-Mathematicae (Erquickstunden)" in normalised
    assert "Nürnberg 1651" in normalised
    assert "p. 517" not in normalised
    assert "517" not in normalised


def test_the_scene_renders_without_any_corpus() -> None:
    """Every machine except the author's has an empty DENCKRING_CORPORA. A scene that
    exploded there would be worse than one that explains itself (ADR 0020: corpora are
    never shipped)."""
    import os

    from explorer import corpora

    original = os.environ.get("DENCKRING_CORPORA")
    os.environ["DENCKRING_CORPORA"] = "/nonexistent-for-this-test"
    corpora.available.cache_clear() if hasattr(corpora.available, "cache_clear") else None
    try:
        response = client.get("/stage/ideenwuerfeln")
        assert response.status_code == 200
        assert "no corpus" in response.text.lower()
    finally:
        if original is None:
            os.environ.pop("DENCKRING_CORPORA", None)
        else:
            os.environ["DENCKRING_CORPORA"] = original


def test_each_corpus_maps_to_a_register() -> None:
    """The corpora already carry the marker that switches the scene's look:
    `style: jean_paul` and `style: modern`."""
    assert stage.register_for("jean_paul") == "baroque"
    assert stage.register_for("modern") == "modern"
    assert stage.register_for("anything-else") == "modern"
