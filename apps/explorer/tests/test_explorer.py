"""The explorer reads the library at request time, so these guard the seams."""

from __future__ import annotations

import pytest
from explorer import bench, catalogue_view
from explorer.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_the_case_lists_every_family() -> None:
    drawers = catalogue_view.case()
    assert {family for family, _ in drawers} == {
        "letter",
        "word",
        "syntax",
        "form",
        "permutation",
        "procedural",
        "translation",
        "visual",
    }


def test_every_catalogued_procedure_has_a_compartment() -> None:
    from denckring.core import catalogue

    in_case = {sort.id for _, sorts in catalogue_view.case() for sort in sorts}
    assert in_case == set(catalogue.ids())


def test_coverage_matches_the_library() -> None:
    from denckring.eval import harness

    assert catalogue_view.coverage()["implemented"] == harness.status().implemented


def test_gaps_and_unreachable_partition_what_is_not_implemented() -> None:
    from denckring.core import catalogue
    from denckring.core.registry import all_procedures

    waiting = sum(count for _, count, _ in catalogue_view.gaps())
    assert waiting + len(catalogue_view.unreachable()) == len(catalogue.ids()) - len(
        all_procedures()
    )


def test_the_case_renders() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "compartments set" in response.text


def test_a_procedure_page_renders_its_form_from_the_schema() -> None:
    response = client.get("/p/lipogram")
    assert response.status_code == 200
    # The field exists because lipogram's params_schema says so, not because
    # anything here knows what a lipogram is.
    assert 'name="forbidden"' in response.text


def test_an_unimplemented_procedure_says_what_it_waits_on() -> None:
    response = client.get("/p/chimera")
    assert "lexicon.synonyms" in response.text


def test_an_unreachable_procedure_explains_itself() -> None:
    response = client.get("/p/canada_dry")
    assert "cannot be checked" in response.text


def test_checking_marks_the_offending_characters() -> None:
    response = client.post(
        "/p/lipogram/check",
        data={"text": "Here is the letter", "lang": "en", "forbidden": "e"},
    )
    assert response.status_code == 200
    assert "Not satisfied" in response.text
    assert response.text.count('<mark class="hit">') == 5


def test_a_satisfied_check_says_so() -> None:
    response = client.post(
        "/p/lipogram/check", data={"text": "aaa bbb", "lang": "en", "forbidden": "z"}
    )
    assert "Satisfied" in response.text


def test_a_library_error_is_shown_not_raised() -> None:
    """A `DenckringError` reaches the page as a message, rather than escaping as a 500.

    The row was `lipogram` with `lang="fr"` until French became a built-in language
    pack in core (ADR 0029): `check("lipogram", ..., lang="fr")` now succeeds, so that
    request produced a report and this test had no error left to surface. `n_plus_7`
    is the replacement because it needs `lexicon.nouns`, which `FrenchPack` does not
    carry and no French data distribution exists to supply, so the request still fails
    inside the library and still fails for a stated reason. Capabilities are enforced
    before parameters are parsed, which is why no `source` is posted here even though
    the row is `checkability: source`.

    The assertion is on the capability name and not on the install hint: the hint says
    `denckring[fr]` for any missing capability, which is what the old assertion matched
    and is therefore no evidence about which failure occurred.
    """
    response = client.post("/p/n_plus_7/check", data={"text": "a cat", "lang": "fr"})
    assert response.status_code == 200
    assert "lexicon.nouns" in response.text


def test_a_constructive_procedure_generates() -> None:
    response = client.post(
        "/p/cut_up/apply", data={"text": "one two three", "lang": "en", "seed": "1"}
    )
    assert "Generated" in response.text


def test_search_finds_by_alias() -> None:
    assert "snowball" in client.get("/search", params={"q": "rhopalic"}).text


def test_an_unknown_id_is_a_page_not_a_traceback() -> None:
    response = client.get("/p/nonesuch")
    assert response.status_code == 200
    assert "No procedure called" in response.text


@pytest.mark.parametrize("procedure_id", ["haiku", "acrostic", "n_plus_7", "palindrome"])
def test_forms_can_be_built_for_a_spread_of_procedures(procedure_id: str) -> None:
    fields = bench.fields_for(procedure_id)
    assert all(f.control for f in fields)
