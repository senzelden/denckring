from denckring.core.errors import (
    DenckringError,
    InvalidParams,
    MissingCapability,
    UnknownLanguage,
    UnknownProcedure,
)


def test_all_errors_share_a_base() -> None:
    for exc in (UnknownProcedure, UnknownLanguage, MissingCapability, InvalidParams):
        assert issubclass(exc, DenckringError)


def test_unknown_language_names_the_extra_to_install() -> None:
    err = UnknownLanguage("de")
    assert "de" in str(err)
    assert "denckring[de]" in str(err)


def test_missing_capability_names_procedure_language_and_capability() -> None:
    err = MissingCapability("n_plus_7", "en", "lexicon.nouns")
    message = str(err)
    assert "n_plus_7" in message
    assert "en" in message
    assert "lexicon.nouns" in message


def test_an_ordinary_gap_recommends_installing_the_extra() -> None:
    """A German gap the `de` extra genuinely closes still gets the generic
    remedy — this is the case `_PERMANENTLY_MISSING` must not swallow."""
    assert "pip install denckring[de]" in str(MissingCapability("some_row", "de", "lexicon.nouns"))


def test_french_stress_does_not_recommend_a_remedy_that_cannot_work() -> None:
    """French has no lexical stress at all, permanently (ADR 0034 D2). All
    eighteen `stress` refusals used to recommend `pip install denckring[fr]`,
    which is installed and will never carry it."""
    message = str(MissingCapability("alcaic_stanza", "fr", "stress"))
    assert "pip install" not in message
    assert "No data distribution supplies it" in message


def test_german_graded_words_does_not_recommend_a_remedy_that_cannot_work() -> None:
    """SCOWL is vendored into `denckring-en-data` alone (ADR 0028); no German
    extra ships `lexicon.graded_words`, so `apply(anagram, lang="de")` used to
    recommend reinstalling an extra already installed."""
    message = str(MissingCapability("anagram", "de", "lexicon.graded_words"))
    assert "pip install" not in message
    assert "No data distribution supplies it" in message


def test_unknown_procedure_names_the_id() -> None:
    assert "wobble" in str(UnknownProcedure("wobble"))


def test_invalid_params_names_the_procedure() -> None:
    err = InvalidParams("lipogram", "forbidden must be a single letter")
    assert "lipogram" in str(err)
    assert "single letter" in str(err)
