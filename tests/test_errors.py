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


def test_unknown_procedure_names_the_id() -> None:
    assert "wobble" in str(UnknownProcedure("wobble"))


def test_invalid_params_names_the_procedure() -> None:
    err = InvalidParams("lipogram", "forbidden must be a single letter")
    assert "lipogram" in str(err)
    assert "single letter" in str(err)
