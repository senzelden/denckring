"""What the catalogue publishes about itself, and where it used to stay quiet.

Finding 6 of the 2026-09-02 MCP sweep: several disclosure surfaces answered a
question with something other than the answer. These pin the fixes.
"""

from denckring import describe


def test_a_row_says_which_of_its_texts_are_not_in_the_asked_language() -> None:
    """Localisation fell back to English silently, and per field.

    Measured on 2026-09-04 over 155 rows: `names` de 95 / fr 98, `definitions`
    de 95 / fr 95, `prompt_hints` de 4 / fr 0. A French caller was handed English
    prose in a field typed as French with nothing marking the substitution, so a
    client could not tell a translated row from an untranslated one.
    """
    described = describe("lipogram", lang="fr")
    assert described.name == "Lipogramme"
    # The hint exists in English only, so this row is not fully French.
    assert described.untranslated == ["prompt_hints"]


def test_a_fully_localised_row_reports_nothing_untranslated() -> None:
    assert describe("lipogram", lang="en").untranslated == []


def test_a_row_missing_its_name_and_definition_says_so() -> None:
    described = describe("supervocalic", lang="fr")
    assert "name" in described.untranslated
    assert "definition" in described.untranslated


def test_an_absent_field_is_not_reported_as_a_fallback() -> None:
    """A field a row does not have in any language has not fallen back.

    Asserted against the mapping rather than a row on purpose: all 155 rows
    carry at least one `prompt_hints` entry (measured 2026-09-04), so no row can
    exercise this branch today, and a test written against one would be pinning
    the catalogue's current contents rather than the rule.
    """
    from denckring.core.describe import _fell_back

    assert _fell_back({}, "fr") is False
    assert _fell_back({"en": "a hint"}, "fr") is True
    assert _fell_back({"fr": "un indice"}, "fr") is False
