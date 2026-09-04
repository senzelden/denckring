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
    """Against the line the board itself computes, not a literal.

    It pinned `154 catalogued`, so it went red the moment the library catalogued a
    155th row — reporting a change in the library as a fault in the explorer. The
    board's job here is to render the scoreboard, not to know what it says.
    """
    response = client.get("/board")
    assert response.status_code == 200
    assert board.scoreboard_line() in response.text
    assert "catalogued" in board.scoreboard_line()


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


def test_a_capability_gap_is_blocked_rather_than_red() -> None:
    """A row whose only failures are missing capabilities is not broken.

    On a `denckring[en,de]` install that is 52 of the 156 tiles, and every one
    was `red` until 2026-09-04 — while `denckring eval --all` reported 0 failed
    on a full install at the same moment. The board was the only surface calling
    them failures.
    """
    from explorer import board

    tiles = {tile.id: tile for tile in board.tiles()}
    # `alexandrine` needs `syllables.heuristic` in French, which `denckring[fr]`
    # supplies and this app does not install.
    blocked = tiles["alexandrine"]
    assert blocked.state == "blocked"
    assert blocked.detail == "requires denckring[fr]"


def test_the_remedy_is_named_from_the_error_code_not_from_its_prose() -> None:
    """`CaseResult.code` carries `missing_capability`; the message is English
    that has already changed twice this week. A tile built by matching prose
    would have followed it."""
    from denckring.eval import harness

    failures = [r for r in harness.run().results if not r.passed]
    assert failures, "this install is expected to lack some data"
    assert all(r.code == "missing_capability" for r in failures)


def test_a_permanent_ceiling_does_not_offer_an_install() -> None:
    """French has no lexical stress and never will (ADR 0034 D2), so no extra
    can be named. Offering one would be the defect `_PERMANENTLY_MISSING`
    exists to prevent, wearing a tile instead of an error message."""
    from denckring.core.errors import extra_for

    assert extra_for("fr", "stress") is None
    assert extra_for("de", "lexicon.graded_words") is None
    assert extra_for("fr", "syllables.heuristic") == "fr"
    assert extra_for("de", "phonemes") == "de-wiktionary"
