"""The corpus layer. Nothing here loads anything the package ships."""

import json

import pytest

from denckring.core import corpus as corpora
from denckring.core.errors import MalformedCorpus


def test_plain_text_is_one_entry_per_line() -> None:
    c = corpora.parse("first\nsecond\n\nthird\n")
    assert [e.text for e in c.entries()] == ["first", "second", "third"]


def test_json_carries_domains_and_headwords() -> None:
    c = corpora.parse(
        json.dumps({"entries": [{"text": "a", "domain": "anatomy", "headwords": ["Herz"]}]})
    )
    assert c.domains() == ["anatomy"]
    assert c.headwords() == ["Herz"]


def test_entries_can_be_asked_for_by_headword() -> None:
    c = corpora.parse(
        json.dumps(
            {
                "entries": [
                    {"text": "a", "headwords": ["Herz"]},
                    {"text": "b", "headwords": ["Zeit"]},
                ]
            }
        )
    )
    assert [e.text for e in c.entries("herz")] == ["a"]
    assert len(c.entries()) == 2


def test_the_wuerzburg_export_shape_is_read() -> None:
    """Its keys are German; a reader of this procedure is likely to have that shape."""
    c = corpora.parse(json.dumps({"quelle": "x", "eintraege": [{"id": "IIa-1", "t": "text"}]}))
    entry = c.entries()[0]
    assert entry.id == "IIa-1"
    assert entry.text == "text"


def test_an_in_memory_corpus_satisfies_the_protocol() -> None:
    c = corpora.InMemoryCorpus([corpora.Entry(text="a")])
    assert isinstance(c, corpora.Corpus)


@pytest.mark.parametrize(
    ("text", "reason"),
    [("", "empty"), ("{not json", "JSON"), ('{"other": []}', "eintraege")],
)
def test_a_corpus_that_cannot_be_read_says_why(text: str, reason: str) -> None:
    with pytest.raises(MalformedCorpus, match=reason):
        corpora.parse(text)
