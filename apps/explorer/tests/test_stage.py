"""The stage. Appearance is not tested; the claims underneath it are."""

from __future__ import annotations

from explorer import stage
from explorer.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


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
