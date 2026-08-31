"""The French lexicon's own invariants.

Skipped in full when `denckring[fr]` is not installed, exactly as the German and
English data tests skip without theirs.
"""

import gzip
import json
import re
from pathlib import Path

import pytest

from denckring.core.errors import MissingCapability
from denckring.lang.base import GLOSSES, GRADED_WORDS, NOUNS, PHONEMES, STRESS, WORDS

fr_data = pytest.importorskip("denckring_fr_data", reason="needs denckring[fr]")

DATA = (
    Path(__file__).resolve().parent.parent
    / "packages"
    / "denckring-fr-data"
    / "src"
    / "denckring_fr_data"
    / "data"
)


def test_the_distribution_is_importable_and_versioned() -> None:
    assert fr_data.__version__ == "0.1.0"


def test_the_bands_run_the_project_s_way_and_not_the_source_s() -> None:
    """Lexique's frequencies rise with commonness; `graded_words` bands fall with
    it, matching SCOWL and what `anagram` sorts by. The build inverts, and a
    source's convention leaking through here would silently rank every French
    anagram backwards. ADR 0032.

    `nonobstant` was the planned second word, but in the built table it lands in
    the same band as `être`: Lexique's `freqlivres` gives it 2.97 per million,
    which ranks it inside the top 14% of forms (book corpora carry a lot of
    formal/legal prose), so the six-band rank split does not separate the pair.
    `obsolescence` is genuinely rare in this table (band 60) and stands in for it.
    """
    bands = fr_data.graded_words()
    assert bands["être"] < bands["obsolescence"]
    assert set(bands.values()) <= {10, 20, 30, 40, 50, 60}


def test_the_noun_list_is_ordered_and_deep() -> None:
    """N+7 indexes into this positionally, so the order is load-bearing."""
    nouns = fr_data.noun_list()
    assert list(nouns) == sorted(nouns)
    assert len(nouns) > 40_000
    assert "maison" in nouns


def test_membership_is_broad_and_keeps_accents() -> None:
    words = fr_data.known_words()
    for word in ("maison", "aimait", "côte", "être"):
        assert word in words


def test_glosses_carry_every_sense_in_wiktionary_s_order() -> None:
    """Every sense, not the first: which sense a writer meant is not knowable from
    the text, so a caller that accepts any of them is the honest reader."""
    senses = fr_data.gloss_table()["maison"]
    assert len(senses) > 3
    assert "bâtiment" in senses[0].casefold()


def test_a_capitalised_headword_resolves_through_the_pack() -> None:
    """No test covered this, and half the vendored table was unreachable.

    The build stores French Wiktionary titles as written, and `glosses` looked
    them up through `_lemma`, which casefolds and drops every non-letter: 261,638
    of 510,973 headwords (51.2%) had no reachable key, 121,388 of them to case
    alone. `glosses("Paris")` returned `()` while the table held the entry. The
    pack now case-flips the word as written, as `denckring_de_wiktionary.look_up`
    already did. Asserted through the pack rather than the table, because the
    table was never the broken half.
    """
    pack = fr_data.FrenchDataPack()
    for headword in ("Paris", "France"):
        assert headword in fr_data.gloss_table()
        assert pack.glosses(headword), headword
    # The flip runs both ways: a proper noun someone lowercased still resolves,
    # and a common noun someone capitalised at a sentence opening still does.
    assert pack.glosses("france")
    assert pack.glosses("Oiseau") == pack.glosses("oiseau")
    # As written wins over the flip, which is the point of trying it first:
    # `Maison` is a surname in this table and `maison` is the building, and a
    # caller who wrote the capital gets the surname rather than a merge of both.
    assert "Maison" in fr_data.gloss_table()
    assert pack.glosses("Maison") != pack.glosses("maison")


def test_a_headword_with_no_definition_is_absent_rather_than_empty() -> None:
    assert "zzzzqq" not in fr_data.gloss_table()


def test_no_shipped_sense_is_letterless() -> None:
    """A sense line made entirely of Wiktionary templates strips to bare
    punctuation once `_strip_markup` drops the templates: `build_lexicon.py`
    measured 14,110 of 700,213 senses (2.0%) this way over the first build,
    the first sense of `la`, `siège`, `bar` and `filtre` among them. A hollow
    `"."` sense is worse than an absent word: `LanguagePack.glosses` documents
    an empty sequence as "could not resolve", but a `"."` sense looks
    resolvable and yields nothing readable when substituted into
    `definitional_expansion` or `definitional_literature`. Sampled (every
    50th headword) rather than scanning all ~700k senses, which is slow and
    unnecessary to catch a regression in the filter.
    """
    has_letter = re.compile(r"[^\W\d_]", re.UNICODE)
    table = fr_data.gloss_table()
    words = sorted(table)[::50]
    assert words, "sample should not be empty"
    for word in words:
        for sense in table[word]:
            assert has_letter.search(sense), f"{word!r} has a letterless sense: {sense!r}"


def test_the_metadata_counts_match_the_files() -> None:
    """A silent corpus change fails here rather than drifting unnoticed. The
    gzip bytes alone do not diff cleanly enough to catch it by eye."""
    counts = json.loads((DATA / "metadata.json").read_text(encoding="utf-8"))["counts"]
    for name, expected in counts.items():
        with gzip.open(DATA / name, mode="rt", encoding="utf-8") as handle:
            assert sum(1 for _ in handle) == expected, name


def test_the_pack_declares_the_four_lexical_capabilities_and_no_prosody() -> None:
    pack = fr_data.FrenchDataPack()
    for capability in (WORDS, NOUNS, GLOSSES, GRADED_WORDS):
        assert capability in pack.capabilities
    # French has no lexical stress and this tranche ships no syllable data.
    # Declaring either would be the false-capability defect ADR 0030 fixed twice.
    for capability in (PHONEMES, STRESS):
        assert capability not in pack.capabilities
    with pytest.raises(MissingCapability):
        pack.phonemes("maison")


def test_accents_are_kept_because_cote_and_cote_are_different_words() -> None:
    pack = fr_data.FrenchDataPack()
    assert pack.is_word("côte")
    assert pack.noun_index("côte") != pack.noun_index("cote")


def test_the_entry_point_gives_this_pack() -> None:
    from denckring.lang import get_pack

    assert isinstance(get_pack("fr"), fr_data.FrenchDataPack)


def test_n_plus_7_apply_survives_its_own_checker_in_french_which_the_gate_missed() -> None:
    """`tests/test_round_trip.py` drives every registered procedure's round trip
    through `meta.languages[0]`, which for `n_plus_7` is `en` — so it could
    never have caught a French-only bug in this pack's noun list. There was one:
    `nouns.txt.gz` originally kept hyphenated forms like `abat-jour`, the
    tokeniser splits a hyphenated word into two tokens, and N+7 could displace
    into a noun its own checker would then see as the wrong word count. Fixed by
    restricting the built noun list to `word.isalpha()`, matching
    `denckring-en-data`'s `noun_list` docstring. This is the French leg the
    shared round-trip gate cannot supply for itself.
    """
    from denckring.core.base import ConstructiveProcedure
    from denckring.core.registry import get

    n_plus_7 = get("n_plus_7")
    assert isinstance(n_plus_7, ConstructiveProcedure)
    source = "abalone"
    produced = n_plus_7.apply(source, lang="fr")
    report = n_plus_7.check(produced, lang="fr", source=source)
    assert report.satisfied
