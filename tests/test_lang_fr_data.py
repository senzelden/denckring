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
    """Importable and carrying a version — not carrying one particular version.
    The literal made this fail on the release bump, which is the change it should
    never have objected to; agreement with the pyproject is
    `test_packaging.py::test_every_distribution_reports_the_same_version`'s job."""
    assert re.match(r"^\d+\.\d+\.\d+(?:[-+].+)?$", fr_data.__version__), fr_data.__version__


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


def test_the_pack_declares_prosody_but_not_stress() -> None:
    """Task 5 (2026-09-01) adds `syllables`/`phonemes`: Lexique carries an
    orthographic syllabation and a phonemic transcription. French still has no
    lexical stress, so `STRESS` stays refused -- declaring it to reach more
    rows would be the false-capability defect ADR 0030 fixed twice."""
    pack = fr_data.FrenchDataPack()
    for capability in (WORDS, NOUNS, GLOSSES, GRADED_WORDS, PHONEMES):
        assert capability in pack.capabilities
    assert STRESS not in pack.capabilities
    # rhyme_key is implemented (from the last vowel -- French has no stressed
    # one to anchor on), so the still-refused capability is exercised through
    # a method that actually needs it.
    with pytest.raises(MissingCapability):
        pack.stress_pattern("belle")


def test_accents_are_kept_because_cote_and_cote_are_different_words() -> None:
    pack = fr_data.FrenchDataPack()
    assert pack.is_word("côte")
    assert pack.noun_index("côte") != pack.noun_index("cote")


def test_the_entry_point_gives_this_pack() -> None:
    from denckring.lang import get_pack

    assert isinstance(get_pack("fr"), fr_data.FrenchDataPack)


def test_the_syllable_table_carries_the_three_columns_the_rules_need() -> None:
    table = fr_data.syllable_table()
    # nbsyll is the citation count, orthosyll judges a mute -ent, and phon
    # distinguishes `de` (d2, a schwa) from `les` (le, none).
    assert table["belle"] == (1, "bEl", "bel-le")
    assert table["les"] == (1, "le", "les")
    assert table["de"] == (1, "d2", "de")
    assert table["chantent"] == (1, "S@t", "chan-tent")
    assert table["vient"] == (1, "vj5", "vient")
    assert table["carrosse"][2] == "car-ros-se"


def test_a_homograph_keeps_its_most_frequent_reading() -> None:
    """`parent` is a noun of two syllables and a verb of one. The table holds
    one row per spelling, so it holds the commoner one and the pack is wrong
    about the other -- recorded in ADR 0034 rather than hidden."""
    assert fr_data.syllable_table()["parent"][0] == 2


def test_the_aspirated_h_list_separates_haricot_from_hotel() -> None:
    """Lexique gives `haricot` /aRiko/ and `hôtel` /otEl/ and cannot tell them
    apart; the elision rule needs the difference, so it comes from
    frwiktionary. The prototype's ad-hoc list missed `hais`, and "je hais"
    then elided wrongly -- inflected forms have to be in here too."""
    aspire = fr_data.h_aspire()
    assert "haricot" in aspire
    assert "hais" in aspire
    assert "hauteur" in aspire
    assert "hôtel" not in aspire
    assert "homme" not in aspire
    assert "heure" not in aspire


def test_a_word_in_lexique_is_exact_and_one_outside_it_is_not() -> None:
    pack = fr_data.FrenchDataPack()
    assert pack.syllable_count("belle") == (1, True)
    _count, exact = pack.syllable_count("zzzzblorf")
    assert exact is False


def test_syllables_returns_the_orthographic_division() -> None:
    """French is the first pack that can honestly declare `syllables`: Lexique
    carries an orthographic syllabation, where German's transcriptions carry
    none and English's distribution declared the capability without one
    (ADR 0030, spec D5)."""
    assert fr_data.FrenchDataPack().syllables("carrosse") == ["car", "ros", "se"]


def test_phonemes_are_ipa_not_sampa() -> None:
    assert fr_data.FrenchDataPack().phonemes("dans") == ["d", "ɑ̃"]


def test_the_nasal_counts_as_a_vowel() -> None:
    """The trap that cost fifteen points in the prototype: `@` is /ɑ̃/, a
    vowel, and reading it as a schwa loses a syllable on every nasal-final
    word."""
    pack = fr_data.FrenchDataPack()
    assert pack.is_vowel_phoneme("ɑ̃") is True
    assert pack.is_vowel_phoneme("j") is False


def test_rhyme_key_is_from_the_last_vowel_because_french_has_no_stress() -> None:
    """`rhyme_scheme` and `ghazal` get their keys through
    `core.prosody.word_rhyme_keys`, which calls `pack.rhyme_keys`; without this
    method both rows ran in French and scored 0.0 on every input forever,
    because `BasePack.rhyme_keys` raises and prosody reads that as "undecidable"
    rather than "unimplemented" -- two hollow rows counted toward 103 would
    have been exactly the inflated-capability defect ADR 0030 exists to
    prevent. The four pairs are hand-verified rhymes; `rose`/`table` is a
    verified non-rhyme sharing no key."""
    pack = fr_data.FrenchDataPack()
    assert pack.rhyme_key("rose") == pack.rhyme_key("chose") == "oz"
    assert pack.rhyme_key("belle") == pack.rhyme_key("chandelle") == "ɛl"
    assert pack.rhyme_key("amour") == pack.rhyme_key("jour") == "uʁ"
    assert pack.rhyme_key("rose") != pack.rhyme_key("table")
    assert pack.rhyme_keys("rose") == ["oz"]


def test_rhyme_key_raises_missing_capability_rather_than_guessing_an_unknown_word() -> None:
    """A guessed rhyme is worse than an unknown one -- matching `phonemes()`,
    which this is built on. `MissingCapability`, not `KeyError`: fix-round 1
    found that `core.prosody.word_rhyme_keys` catches only `MissingCapability`
    around `rhyme_keys`, so a plain `KeyError` escaped uncaught out of
    `check('rhyme_scheme', ..., lang='fr')` on the first unknown word."""
    pack = fr_data.FrenchDataPack()
    with pytest.raises(MissingCapability):
        pack.rhyme_key("zzzzblorf")
    with pytest.raises(MissingCapability):
        pack.rhyme_keys("zzzzblorf")


def test_rhyme_key_falls_back_past_a_leading_elision() -> None:
    """Fix-round 2 (2026-09-01): task 8's fixture verification hit a line
    ending `d'espoir` and found the whole-form-only lookup made it
    undecidable rather than a rhyme for `espoir` -- an ordinary elided form,
    not one of the 94 fused Lexique entries like `aujourd'hui`. An elided
    form is extremely common at a French line ending (`d'espoir`, `l'amour`,
    `qu'un`), so `rhyme_scheme` and `ghazal` were silently hollow on it: the
    same "reads as undecidable, not as unimplemented" failure shape ADR 0030
    exists to catch, just reached through a lookup gap rather than a missing
    method. `_table_entry` now retries past the apostrophe when the whole
    form fails."""
    pack = fr_data.FrenchDataPack()
    assert pack.rhyme_key("d'espoir") == pack.rhyme_key("espoir")
    assert pack.rhyme_key("l'amour") == pack.rhyme_key("amour")


def test_rhyme_scheme_reads_a_line_ending_in_an_elided_word() -> None:
    """The end-to-end case fix-round 2 was found from: a couplet ending
    `d'espoir`/`noir` is ordinary French verse, and before the fix it scored
    `rhyme_undecidable` rather than being read at all."""
    from denckring import check

    report = check("rhyme_scheme", "un rayon d'espoir\nun ciel tout noir", lang="fr", scheme="AA")
    assert report.satisfied is True
    assert report.score == 1.0


def test_aujourd_hui_still_resolves_as_one_word_after_the_elision_fallback() -> None:
    """The regression guard for fix-round 2: `_table_entry` must try the
    whole lowercased form FIRST and only fall back past the apostrophe when
    that fails. `aujourd'hui` is one of the 94 Lexique entries that carry an
    apostrophe internally -- three syllables, `(3, True)` -- and if the
    fallback ran unconditionally (splitting at the last apostrophe before
    trying the whole form) it would instead resolve as `hui`, which Lexique
    also carries but as one syllable. This test fails loudly if that
    ordering is ever reversed."""
    assert fr_data.FrenchDataPack().syllable_count("aujourd'hui") == (3, True)


def test_phonemes_of_an_unknown_word_raises_missing_capability_not_key_error() -> None:
    """Fix-round 1 (2026-09-01): `phonemes()` shipped raising plain `KeyError`
    for a word `syllable_table()` does not carry. `assonance_constraint` and
    `spoonerism` both catch only `MissingCapability` around their own call to
    `pack.phonemes`, and `core.prosody.word_rhyme_keys` does the same around
    `rhyme_keys` -- so `KeyError` was not "undecidable", it was unhandled.
    `check('assonance_constraint', 'la belle zzzzblorf', lang='fr')` crashed
    outright, on a routine event (one word Lexique lacks) rather than an edge
    case. Fixed to match the convention `denckring-en-data` and
    `denckring-de-wiktionary` already use for exactly this call.
    """
    with pytest.raises(MissingCapability):
        fr_data.FrenchDataPack().phonemes("zzzzblorf")


def test_the_rows_that_read_phonemes_survive_an_unknown_word_in_french() -> None:
    """The gate that would have caught fix-round 1's crash and did not.

    `tests/test_round_trip.py` drives every registered procedure's round trip
    through `meta.languages[0]`, which is English for all three of these rows
    -- so it could never exercise their French out-of-vocabulary path.
    `tests/test_prosody_robustness.py` exercises unknown words only in
    English. So `rhyme_scheme`, `assonance_constraint` and `spoonerism` had
    zero coverage of their commonest French failure -- ordinary text
    containing one word Lexique does not carry -- and the full gate was green
    while all three crashed with an uncaught `KeyError` on it. This test
    asserts a `Report` comes back, not an exception; the reading each row
    lands on for the unknown word is not this test's concern.
    """
    from denckring import check

    text = "la belle zzzzblorf\nune autre chose"
    for procedure_id, kwargs in (
        ("rhyme_scheme", {"scheme": "AA"}),
        ("assonance_constraint", {}),
        ("spoonerism", {}),
    ):
        report = check(procedure_id, text, lang="fr", **kwargs)
        assert report.procedure == procedure_id


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
