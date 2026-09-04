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


def test_german_prosody_names_the_wiktionary_extra_not_the_lexical_one() -> None:
    """German has two extras and the remedy used to name the language.

    `denckring[de]` is the CC0 lexical pack; `stress`, `phonemes`,
    `syllables.dictionary` and `lexicon.glosses` come only from
    `denckring[de-wiktionary]`, quarantined in its own distribution because its
    data is CC BY-SA (ADR 0013). A reader following `pip install denckring[de]`
    for any of the four installs what they may already have and gains nothing —
    the same defect class as the French `stress` remedy above, one extra deeper.
    """
    for capability in ("stress", "phonemes", "syllables.dictionary", "lexicon.glosses"):
        message = str(MissingCapability("some_row", "de", capability))
        assert "pip install denckring[de-wiktionary]" in message, capability
        assert "denckring[de]`" not in message, capability


def test_the_lexical_german_extra_is_still_named_for_what_it_does_supply() -> None:
    """The fix must not send every German gap to the Wiktionary extra: `de-data`
    is what supplies the noun list, and naming the heavier distribution for it
    would trade one misleading remedy for another."""
    for capability in ("lexicon.nouns", "lexicon.words", "syllables.heuristic"):
        message = str(MissingCapability("some_row", "de", capability))
        assert "pip install denckring[de]" in message, capability


def test_unknown_procedure_names_the_id() -> None:
    assert "wobble" in str(UnknownProcedure("wobble"))


def test_invalid_params_names_the_procedure() -> None:
    err = InvalidParams("lipogram", "forbidden must be a single letter")
    assert "lipogram" in str(err)
    assert "single letter" in str(err)
