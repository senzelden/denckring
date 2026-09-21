import pytest

from denckring import check
from denckring.core import catalogue
from denckring.procedures import s_plus_7 as s_plus_7_module
from denckring.procedures.n_plus_7 import NPlus7Params
from denckring.procedures.s_plus_7 import SPlus7, SPlus7Params

pytest.importorskip("denckring_en_data")

#: The generalisation `s_plus_7` claims. Named once so the catalogue definition
#: and the module docstring cannot drift apart again: issue #23 was the two
#: saying different things — "any part of speech" against "any displacement" —
#: with neither implemented as a difference from `n_plus_7`.
GENERALISATION = "part of speech"

GARDEN = ["aster", "bramble", "crocus", "dahlia", "elder", "fennel", "gorse", "hazel"]

SOURCE = "the cat sat on the table"
DISPLACED_BY_THREE = "the catacala satanism on the tablefork"


def test_a_configurable_offset_is_respected() -> None:
    assert check(
        "s_plus_7", "the catacala satanism on the tablefork", source=SOURCE, offset=3
    ).satisfied


def test_the_wrong_offset_is_not_satisfied() -> None:
    assert not check(
        "s_plus_7", "the catacala satanism on the tablefork", source=SOURCE, offset=7
    ).satisfied


def test_both_rows_say_they_are_one_implementation_under_two_names() -> None:
    """While the two share an implementation, both notes must say so (#23).

    The rule, not today's wording: `s_plus_7` adding no parameter of its own is
    what makes "two named forms of one displacement" true, and the claim is
    surfaced to every caller by `denckring show` and `describe_procedure` over
    MCP. A future field would make them genuinely different rows, and this guard
    failing is the prompt to rewrite both notes rather than to delete the
    assertion.
    """
    assert set(SPlus7Params.model_fields) == set(NPlus7Params.model_fields)
    s_plus_7_notes = catalogue.get("s_plus_7").notes or ""
    n_plus_7_notes = catalogue.get("n_plus_7").notes or ""
    assert "n_plus_7" in s_plus_7_notes
    assert "s_plus_7" in n_plus_7_notes


def test_the_catalogue_and_the_module_name_the_same_generalisation() -> None:
    """Issue #23's actual defect: two descriptions of one row that disagreed."""
    definition = catalogue.get("s_plus_7").definitions["en"].casefold()
    docstring = (s_plus_7_module.__doc__ or "").casefold()
    assert GENERALISATION in definition
    assert GENERALISATION in docstring


def test_s_plus_7_inherits_the_dictionary() -> None:
    """It delegates to `NPlus7Params` and `displacement_report`, so it gets this
    free — asserted rather than assumed, because "free" is how a surface quietly
    diverges."""
    assert SPlus7().apply("aster", lang="en", dictionary=GARDEN, offset=2) == "crocus"
