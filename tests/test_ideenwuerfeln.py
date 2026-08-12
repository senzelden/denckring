"""Jean Paul's throw, reconstructed — and the limits of what it checks.

Every corpus here is synthetic. The excerpt books are public domain but the
transcriptions that make them usable are scholarly editions, so none travels
with this package or its tests.
"""

import json

import pytest

from denckring import check, get
from denckring.core import corpus as corpora
from denckring.core.protocol import Constructive

CORPUS = json.dumps(
    {
        "name": "synthetic",
        "entries": [
            {
                "text": "The Roman legions carried a portable sundial.",
                "domain": "antiquity",
                "headwords": ["Zeit"],
            },
            {
                "text": "The heart's left ventricle is the thickest chamber.",
                "domain": "anatomy",
                "headwords": ["Herz", "Zeit"],
            },
            {
                "text": "A mayfly lives one day as an adult.",
                "domain": "entomology",
                "headwords": ["Zeit"],
            },
            {
                "text": "Whoever counts the hours has already lost them.",
                "domain": "aphorism",
                "headwords": ["Zeit"],
            },
        ],
    }
)

THROW = "\n".join(
    [
        "The Roman legions carried a portable sundial.",
        "The heart's left ventricle is the thickest chamber.",
        "A mayfly lives one day as an adult.",
    ]
)


def test_a_throw_drawn_from_the_corpus_is_satisfied() -> None:
    assert check("ideenwuerfeln", THROW, source=CORPUS).satisfied


def test_an_excerpt_nobody_wrote_down_is_a_violation() -> None:
    invented = THROW.replace("A mayfly lives one day as an adult.", "Something invented.")
    report = check("ideenwuerfeln", invented, source=CORPUS)
    assert not report.satisfied
    assert report.violations[0].rule == "not_in_the_corpus"


def test_the_wrong_number_of_excerpts_is_a_violation() -> None:
    two = "\n".join(THROW.split("\n")[:2])
    report = check("ideenwuerfeln", two, source=CORPUS)
    assert any(v.rule == "wrong_number_of_excerpts" for v in report.violations)


def test_a_headword_the_excerpt_is_not_filed_under() -> None:
    report = check("ideenwuerfeln", THROW, source=CORPUS, headword="Herz")
    assert any(v.rule == "wrong_headword" for v in report.violations)


def test_distinct_domains_can_be_required() -> None:
    assert check("ideenwuerfeln", THROW, source=CORPUS, distinct_domains=True).satisfied
    repeated = "\n".join(
        [
            "The Roman legions carried a portable sundial.",
            "The Roman legions carried a portable sundial.",
            "A mayfly lives one day as an adult.",
        ]
    )
    report = check("ideenwuerfeln", repeated, source=CORPUS, distinct_domains=True)
    assert any(v.rule == "domain_repeated" for v in report.violations)


def test_an_unknown_field_is_reported_rather_than_assumed_distinct() -> None:
    unfielded = json.dumps({"entries": [{"text": "a"}, {"text": "b"}, {"text": "c"}]})
    report = check("ideenwuerfeln", "a\nb\nc", source=unfielded, distinct_domains=True)
    assert any(v.rule == "domain_unknown" for v in report.violations)


def test_throwing_produces_something_the_checker_accepts() -> None:
    procedure = get("ideenwuerfeln")
    assert isinstance(procedure, Constructive)
    for seed in range(8):
        throw = procedure.apply(CORPUS, seed=seed, headword="Zeit")
        assert check("ideenwuerfeln", throw, source=CORPUS, headword="Zeit").satisfied


def test_throwing_is_deterministic_under_a_seed() -> None:
    procedure = get("ideenwuerfeln")
    assert isinstance(procedure, Constructive)
    assert procedure.apply(CORPUS, seed=3) == procedure.apply(CORPUS, seed=3)


def test_a_corpus_too_small_for_a_throw_refuses() -> None:
    procedure = get("ideenwuerfeln")
    assert isinstance(procedure, Constructive)
    with pytest.raises(corpora.MalformedCorpus, match="fewer than"):
        procedure.apply("only one line", seed=0)


def test_the_row_says_the_rule_is_a_reconstruction() -> None:
    """Jean Paul named the notebook; he never wrote the procedure down."""
    from denckring.core import catalogue

    assert catalogue.get("ideenwuerfeln").attested == "reconstruction"


def test_the_witz_step_is_catalogued_as_beyond_checking() -> None:
    """Where the mechanisable part ends is worth recording."""
    from denckring.core import catalogue

    assert catalogue.get("witz_metaphor").checkability == "none"
