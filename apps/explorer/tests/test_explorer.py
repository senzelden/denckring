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

    The row has moved twice, and both moves were the same mistake: it was pinned
    to a capability the *install* happened to lack, so improving the install cost
    the suite its only library-error row. It was `lipogram` in French until ADR
    0029 made French built-in; then `n_plus_7`, whose docstring here argued the
    app should stay on `denckring[en,de]` precisely to keep this test alive. The
    street scene then needed `phonemes` and `lexicon.graded_words` in German and
    French, the app installed all six distributions, and `n_plus_7` in French
    started succeeding.

    So it is now pinned to a capability **no install can supply**: French has no
    lexical stress and never will (ADR 0034 D2, and `_PERMANENTLY_MISSING` in
    `errors.py` says so). `iambic_pentameter` requires `stress`, so this request
    raises `MissingCapability` on every possible install, and no future extra can
    take the row away again.

    The assertion is on the capability name rather than on the install hint,
    which is the older lesson and still holds: the hint depends on `lang`, not on
    which capability is missing, so it would be no evidence about which failure
    occurred. Capabilities are enforced before parameters are parsed, which is
    why no other field is posted.
    """
    response = client.post("/p/iambic_pentameter/check", data={"text": "un vers", "lang": "fr"})
    assert response.status_code == 200
    assert "stress" in response.text


def test_a_constructive_procedure_generates() -> None:
    response = client.post(
        "/p/cut_up/apply", data={"text": "one two three", "lang": "en", "seed": "1"}
    )
    assert "Generated" in response.text


def test_a_seed_reaches_apply_so_the_bench_can_repeat_itself() -> None:
    """The bench posts one form to two routes, and `coerce` walks the fields it
    is handed — so while the apply route was handed the *checker's* fields, a
    posted `seed` was dropped before it could reach a procedure that draws.

    The visible cost was not a wrong answer but an unrepeatable one: the ten
    drawing procedures (ADR 0025) drew unseeded from the bench, so the same
    request gave a different result each time, and
    `test_a_constructive_procedure_generates` above failed roughly one run in
    three when `cut_up` shuffled three words back into their own order and met
    the identity guard. Asserting agreement across repeats is what pins the fix;
    asserting that two different seeds disagree is what stops it passing because
    the seed is being ignored in some new way."""
    text = "one two three four five six"
    same = {
        client.post("/p/cut_up/apply", data={"text": text, "lang": "en", "seed": "1"}).text
        for _ in range(5)
    }
    assert len(same) == 1
    other = client.post("/p/cut_up/apply", data={"text": text, "lang": "en", "seed": "9"}).text
    assert other not in same


def test_the_bench_offers_the_parameters_apply_actually_takes() -> None:
    """`apply_fields_for` is the checker's schema subtracted from `apply`'s.

    `source` is left out because `parse_apply_params` refuses a second one — the
    text being transformed is the source. `max_results` is left out because
    `apply` is `produce(...).texts[0]` (ADR 0026), so no value of it changes the
    one text this page shows, and a control that cannot move the result teaches
    the reader the wrong thing about the parameter."""
    names = {f.name for f in bench.apply_fields_for("cut_up")}
    assert "seed" in names
    assert names.isdisjoint({"source", "max_results"})
    # A procedure that validates but does not generate has no apply form at all.
    assert bench.apply_fields_for("lipogram") == []


def test_a_word_list_parameter_is_not_read_as_numbers() -> None:
    """`coerce` cast every entry of every array field with `int`, which was true
    of the only array parameter that existed when it was written
    (`syllable_count.pattern`) and false of all three that have arrived since.

    So `n_plus_7`'s `dictionary` — ADR 0029's own headline parameter — could
    only ever answer "That is not a number", and `multiple_constraint`'s
    `constraints`, a list of procedure ids, had the same shape before it. The
    assertion is on the displacement rather than on the absence of the error
    message: *dog* is the entry after *cat* in the supplied list and in no other
    list, so it is evidence the caller's own dictionary was the one walked."""
    response = client.post(
        "/p/n_plus_7/apply",
        data={"text": "the cat sat", "lang": "en", "dictionary": "cat, dog, emu", "offset": "1"},
    )
    assert "the dog sat" in response.text


def test_a_number_list_parameter_is_still_read_as_numbers() -> None:
    """The other half of the fix above, and the reason it reads the schema's
    item type rather than simply dropping the cast: `syllable_count.pattern` is
    a list of integers and a bad entry in one is still a caller error worth
    naming."""
    good = client.post(
        "/p/syllable_count/check",
        data={"text": "one two three\nfour five", "lang": "en", "pattern": "3, 2"},
    )
    assert "Satisfied" in good.text
    bad = client.post("/p/syllable_count/check", data={"text": "a b", "lang": "en", "pattern": "x"})
    assert "That is not a number" in bad.text


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
