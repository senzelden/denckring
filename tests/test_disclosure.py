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


#: Phrases a definition can only be read as a promise about what is verified.
#: `caesura` needs no entry in `requires` because nothing in this project locates
#: one at all, so naming it is always a promise nothing keeps.
_DISCLOSURE = ("checker", "checked", "read as", "only the", "compares", "counts")


def _promises_beyond_requires(meta: object) -> list[str]:
    definition = meta.definitions.get("en", "").lower()  # type: ignore[attr-defined]
    requires = meta.requires  # type: ignore[attr-defined]
    promises = []
    if "caesura" in definition:
        promises.append("caesura")
    if "stress" in definition and "stress" not in requires:
        promises.append("stress")
    if "syllable" in definition and not any(c.startswith("syllables") for c in requires):
        promises.append("syllable")
    return promises


def test_a_definition_promising_what_the_checker_lacks_says_so() -> None:
    """Finding 6: six rows published a definition promising what the checker
    structurally cannot do, and `describe_procedure` hands that definition to a
    model as the description of the constraint.

    Four of the six are reachable this way. `limerick` (line lengths) and
    `blank_verse` (the caveat `iambic_pentameter` publishes) are not: their
    promises are ordinary prose with no capability word to key on, which is why
    the sweep called for a definition-by-definition read rather than a regex.
    This guard holds the four that generalise, so the next row to name a caesura
    it does not locate fails here rather than shipping.
    """
    from denckring.core import catalogue

    rows = catalogue.load()
    bare = []
    for meta in rows.values() if isinstance(rows, dict) else rows:
        promises = _promises_beyond_requires(meta)
        if not promises:
            continue
        definition = meta.definitions.get("en", "").lower()
        if not any(mark in definition for mark in _DISCLOSURE):
            bare.append((meta.id, promises))
    assert bare == [], f"definitions promise what the checker cannot do: {bare}"
