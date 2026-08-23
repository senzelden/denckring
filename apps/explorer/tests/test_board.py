"""The board is `denckring eval` with a body. These guard what it claims."""

from __future__ import annotations

from explorer import board
from explorer.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_every_catalogued_procedure_gets_a_tile() -> None:
    from denckring.core import catalogue

    assert {tile.id for tile in board.tiles()} == set(catalogue.ids())


def test_an_implemented_procedure_with_passing_cases_is_green() -> None:
    tiles = {tile.id: tile for tile in board.tiles()}
    assert tiles["lipogram"].state == "green"
    assert tiles["lipogram"].cases > 0
    assert tiles["lipogram"].detail == ""


def test_a_catalogued_but_unimplemented_procedure_is_grey() -> None:
    """`homosyntaxism` is blocked on a `pos` capability no pack provides. It is not a
    failure, and a board that showed it red would cry wolf 35 times."""
    tiles = {tile.id: tile for tile in board.tiles()}
    assert tiles["homosyntaxism"].state == "grey"
    assert tiles["homosyntaxism"].cases == 0


def test_the_board_renders_with_the_scoreboard_line() -> None:
    response = client.get("/board")
    assert response.status_code == 200
    assert "153 catalogued" in response.text


def test_a_tile_is_readable_and_not_just_an_id() -> None:
    """The board's stated job is scannability, and `sestina` reads where the id
    beside it does not. Both are shown: the id is what the fixtures, the
    procedure page and `denckring eval` all call the row."""
    tiles = {tile.id: tile for tile in board.tiles()}
    response = client.get("/board")
    assert tiles["lipogram"].name in response.text
    assert ">lipogram<" in response.text
    assert tiles["lipogram"].family in response.text


def test_the_board_prints_no_empty_caption() -> None:
    """It borrows the stage's shell, which carries a caption under the frame —
    an empty one is a stray element with nothing in it to read."""
    response = client.get("/board")
    assert '<p class="stage-caption"></p>' not in response.text
    assert "run just now" in response.text
