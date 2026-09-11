"""The board is `denckring eval` with a body. These guard what it claims."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
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


@pytest.fixture
def partial_install() -> Iterator[None]:
    """A `denckring[en,de]` install, simulated, for the tests about capability gaps.

    The explorer used to *be* such an install, and these tests read their subject
    straight off it. Then the street scene arrived, which needs `phonemes` and
    `lexicon.graded_words` in German and French, so the app now installs
    `de-wiktionary`, `de-frequency` and `fr` — and every tile went green,
    leaving the two tests below asserting things about a state the app no longer
    has. That is the same defect the project has hit three times: a guard whose
    real answer is "this machine".

    So the gap is built rather than found. `denckring.lang` is asked for a pack
    first, which is what forces entry-point discovery to run — popping `_PACKS`
    before that happens simply lets discovery put the real packs back, and an
    earlier draft of this fixture measured a confidently wrong zero that way.
    """
    import denckring.lang as lang_registry
    from denckring.lang.de import GermanPack
    from denckring.lang.fr import FrenchPack

    lang_registry.get_pack("en")
    packs = dict(lang_registry._PACKS)
    defaults = dict(lang_registry._DEFAULTS)
    lang_registry._PACKS.pop("de", None)
    lang_registry._PACKS.pop("fr", None)
    lang_registry._DEFAULTS["de"] = GermanPack()
    lang_registry._DEFAULTS["fr"] = FrenchPack()
    assert "phonemes" not in lang_registry.get_pack("fr").capabilities, (
        "the simulation did not take, so anything below it would be measuring "
        "the real install and passing for the wrong reason"
    )
    try:
        yield
    finally:
        lang_registry._PACKS.clear()
        lang_registry._PACKS.update(packs)
        lang_registry._DEFAULTS.clear()
        lang_registry._DEFAULTS.update(defaults)


def test_a_capability_gap_is_blocked_rather_than_red(partial_install: None) -> None:
    """A row whose only failures are missing capabilities is not broken.

    On a `denckring[en,de]` install that is 54 of the 158 tiles, and every one
    was `red` until 2026-09-04 — while `denckring eval --all` reported 0 failed
    on a full install at the same moment. The board was the only surface calling
    them failures.

    The install is simulated (see `partial_install`) rather than inherited from
    the app, which now installs every data distribution for the street scene.
    """
    from explorer import board

    tiles = {tile.id: tile for tile in board.tiles()}
    # `alexandrine` needs `syllables.heuristic` in French, which `denckring[fr]`
    # supplies and the simulated install does not have.
    blocked = tiles["alexandrine"]
    assert blocked.state == "blocked"
    assert blocked.detail == "requires denckring[fr]"


def test_the_remedy_is_named_from_the_error_code_not_from_its_prose(
    partial_install: None,
) -> None:
    """`CaseResult.code` carries `missing_capability`; the message is English
    that has already changed twice this week. A tile built by matching prose
    would have followed it."""
    from denckring.eval import harness

    failures = [r for r in harness.run().results if not r.passed]
    assert failures, "the simulated install is expected to lack some data"
    assert all(r.code == "missing_capability" for r in failures)


def test_a_permanent_ceiling_does_not_offer_an_install() -> None:
    """French has no lexical stress and never will (ADR 0034 D2), so no extra
    can be named. Offering one would be the defect `_PERMANENTLY_MISSING`
    exists to prevent, wearing a tile instead of an error message.

    German `lexicon.graded_words` was the second example here until ADR 0038
    gave it `denckring[de-frequency]` — which is why a gap and a ceiling are
    kept in separate tables, and why this test now asserts the difference rather
    than a list of things that happen to be missing today.
    """
    from denckring.core.errors import extra_for

    assert extra_for("fr", "stress") is None
    assert extra_for("fr", "syllables.heuristic") == "fr"
    assert extra_for("de", "phonemes") == "de-wiktionary"
    assert extra_for("de", "lexicon.graded_words") == "de-frequency"
