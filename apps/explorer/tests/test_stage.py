"""The stage. Appearance is not tested; the claims underneath it are."""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from explorer import stage
from explorer.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _label(alternatives: list[str], index: int) -> str:
    """What a disc shows at a given index — the same model the scene's own
    script uses to turn the rings. A real alternative in range; one further
    blank position, past the end, for a ring that may contribute nothing,
    exactly as the paper rings themselves carry a blank for the prefix and
    suffix. The per-ring index is the truth on this scene now, not whatever
    text happens to be painted on screen, so this is what a Python test can
    pin without a browser."""
    return alternatives[index] if index < len(alternatives) else ""


def test_the_index_lists_every_scene() -> None:
    response = client.get("/stage")
    assert response.status_code == 200
    for scene in stage.SCENES:
        assert scene.title in response.text


def test_every_scene_names_a_real_procedure() -> None:
    """A scene dramatising a procedure that is not registered would be a scene making
    a claim the library cannot back."""
    from denckring.core.registry import all_procedures

    registered = set(all_procedures())
    assert {scene.procedure_id for scene in stage.SCENES} <= registered


def test_chrome_off_removes_the_caption() -> None:
    """Recording wants the stage and nothing else."""
    with_chrome = client.get("/stage")
    without = client.get("/stage?chrome=off")
    assert "stage-caption" in with_chrome.text
    assert "stage-caption" not in without.text


@pytest.mark.parametrize("slug", [scene.slug for scene in stage.SCENES])
def test_every_scene_renders_and_survives_chrome_off(slug: str) -> None:
    """The spec asks this of each scene, not of the index alone: `chrome_off`
    is threaded through five separate route signatures, so a typo in one would
    ship unnoticed until somebody sat down to record that scene."""
    with_chrome = client.get(f"/stage/{slug}")
    assert with_chrome.status_code == 200
    assert 'id="stage"' in with_chrome.text
    assert "stage-caption" in with_chrome.text

    without = client.get(f"/stage/{slug}?chrome=off")
    assert without.status_code == 200
    assert 'id="stage"' in without.text
    assert "stage-caption" not in without.text


def test_the_rings_carry_the_transcribed_counts() -> None:
    """Cramer's transcription has 49/60/12/120/23, where Harsdörffer's own text
    announces 48/50/12/120/24. The scene shows what the data has, not what the book
    claims — the catalogue row records both and adjusts neither."""
    rings = stage.rings()
    assert [len(slot.alternatives) for slot in rings.slots] == [49, 60, 12, 120, 23]


def test_the_scene_shows_the_true_count_beside_the_famous_one() -> None:
    rings = stage.rings()
    assert rings.claimed == 97_209_600
    assert rings.combinations != rings.claimed


def test_the_legend_gives_each_band_its_own_count() -> None:
    """The counts are read off `rings.slots`, never typed into the template: the
    two figures beside them are products of these five, and a legend carrying a
    number by hand is the one place on that page where a viewer could catch the
    arithmetic disagreeing with itself."""
    normalised = " ".join(client.get("/stage/denckring").text.split())
    for slot in stage.rings().slots:
        assert f"{slot.name} &middot; {len(slot.alternatives)}" in normalised


def test_the_scene_shows_how_the_true_count_is_reached() -> None:
    """The figure on screen is 103,680,000 and the legend beside it reads
    49/60/12/120/23, which multiply to 97,372,800 — a viewer who checks the
    arithmetic and is told nothing about the blank turn on the prefix and
    suffix rings concludes the page is wrong by 6.5%. So the page shows the
    product it actually used, built from those same slots."""
    rings = stage.rings()
    product = [len(slot.alternatives) + (1 if slot.optional else 0) for slot in rings.slots]
    assert math.prod(product) == rings.combinations
    normalised = " ".join(client.get("/stage/denckring").text.split())
    assert " &times; ".join(str(count) for count in product) in normalised
    assert "may each be left blank" in normalised


def test_the_struck_figure_is_given_its_reason() -> None:
    """Striking a number through without saying why is an assertion, not a
    demonstration. The catalogue row owns the argument — the figure factors as
    2^8 x 3 x 5^2 x 61 x 83, and no ring has 61 or 83 parts — and the scene must
    carry it rather than expecting the viewer to take the strike on trust."""
    normalised = " ".join(client.get("/stage/denckring").text.split())
    assert f"{stage.CLAIMED_COMBINATIONS:,}" in normalised
    assert "2<sup>8</sup> &times; 3 &times; 5<sup>2</sup> &times; 61 &times; 83" in normalised
    assert "neither 61 nor 83 divides any ring size" in normalised


def test_the_english_gloss_is_credited_to_this_project() -> None:
    """The German is quoted; the English under it is nobody's but this
    project's, in a figure otherwise scrupulous about where its text came
    from."""
    normalised = " ".join(client.get("/stage/denckring").text.split())
    assert "the translation is this project's own" in normalised


def test_a_word_turned_from_the_rings_satisfies_the_procedure() -> None:
    """The scene's claim: what comes off these rings is a denckring word."""
    from denckring import check
    from denckring.core.protocol import Constructive
    from denckring.core.registry import get

    procedure = get("denckring")
    # `get` is typed as the base class, which has no `apply` — ADR 0002 keeps it
    # off `BaseProcedure` because it is optional. Narrow once, here.
    assert isinstance(procedure, Constructive)
    word = procedure.apply("", lang="en")
    assert check("denckring", word).satisfied is True


def test_the_denckring_scene_renders() -> None:
    response = client.get("/stage/denckring")
    assert response.status_code == 200
    assert "ring-0" in response.text


def test_the_rings_show_a_valid_word_on_first_paint() -> None:
    """The hidden field is assembled by JS from the per-ring index — the single
    source of truth for what the discs show and what gets checked, on first
    paint, after a manual turn and after a spin alike (see the two tests below
    for the latter two). Nothing server-side pre-fills it. What this can test
    without a browser is the claim first paint makes: every ring starts at
    index 0, which is always a real alternative, so reading inward to outward
    already spells a denckring word — "Read it" has something real to check
    the moment the page appears."""
    from denckring import check

    word = "".join(_label(slot.alternatives, 0) for slot in stage.rings().slots)
    assert check("denckring", word).satisfied is True


def test_a_manual_turn_still_spells_a_denckring_word() -> None:
    """A click on one disc advances only that ring's index by one, the others
    holding. Any index for any ring — including the blank position an
    optional ring carries past its last real alternative — still spells
    something the rings could have produced: one alternative, or a blank
    where the ring allows it, chosen per slot in order, which is exactly what
    device.segment() (and so `check`) accepts, regardless of which specific
    index a click happened to land on."""
    from denckring import check

    slots = stage.rings().slots
    for ring_index, slot in enumerate(slots):
        total = len(slot.alternatives) + (1 if slot.optional else 0)
        # A small turn, and turning all the way round to the blank a ring
        # allows (or, for a ring with no blank, its last real alternative).
        for turned_index in (1, total - 1):
            word = "".join(
                _label(other.alternatives, turned_index if i == ring_index else 0)
                for i, other in enumerate(slots)
            )
            assert check("denckring", word).satisfied is True, (slot.name, turned_index)


def test_a_spin_lands_the_discs_on_the_word_that_was_checked() -> None:
    """ "Turn them for me" asks the library for a word and walks the discs to it
    with stage.pieces_for() — the same segmentation the scene's script uses to
    pick each disc's target index from the piece the server sent back. The
    invariant this pins: reassembling those pieces, inward to outward, must
    give back exactly the word `check` was asked about — the discs and the
    checked word can never disagree, including after a spin."""
    from denckring import check
    from denckring.core.protocol import Constructive
    from denckring.core.registry import get

    procedure = get("denckring")
    assert isinstance(procedure, Constructive)
    word = procedure.apply("", lang="en")
    pieces = stage.pieces_for(word)
    assert pieces is not None
    assert "".join(pieces) == word
    assert check("denckring", word).satisfied is True


def test_the_harsdoerffer_quotation_is_reproduced_exactly() -> None:
    """Byte-for-byte, virgule and ellipsis included — modernising the spelling,
    "fixing" Reimwörter or swapping the slash for a comma would be exactly the
    liberty this project refuses to take with its data everywhere else."""
    response = client.get("/stage/denckring")
    normalised = " ".join(response.text.split())
    assert (
        "hat … seinen Gebrauch in Erfindung der Reimwörter / wann man die Reimsilben "
        "auf dem dritten und vierten Ring suchet und die Reimbuchstaben auf dem zweyten "
        "Ring darzu drehet"
    ) in normalised


def test_the_quotation_is_attributed_without_a_page_number() -> None:
    """The catalogue's p. 517 is the page of the device plate; the sources that
    carry this sentence give no page for it, so citing one would be exactly
    the false precision this project refuses elsewhere."""
    response = client.get("/stage/denckring")
    normalised = " ".join(response.text.split())
    assert "Deliciae Physico-Mathematicae (Erquickstunden)" in normalised
    assert "Nürnberg 1651" in normalised
    assert "p. 517" not in normalised
    assert "517" not in normalised


def test_the_two_verdicts_are_distinct() -> None:
    """A word built from the rings is always a reading of them — `check`
    cannot fail it, which is why the scene shows a second verdict that can.
    A ring word straight off first paint is off-the-rings True; a made-up
    string of the same shape that the lexicon does not carry is
    German-knows False, even though neither verdict is about the other."""
    from denckring import check

    ring_word = "".join(_label(slot.alternatives, 0) for slot in stage.rings().slots)
    assert check("denckring", ring_word, lang="de").satisfied is True
    assert stage.german_pack().is_word(ring_word) is False

    found = stage.find_word()
    assert found is not None
    real_word, _pieces = found
    assert check("denckring", real_word, lang="de").satisfied is True
    assert stage.german_pack().is_word(real_word) is True


def test_the_word_panel_shows_both_verdicts_distinctly() -> None:
    """The page itself, not just the two facts in isolation: both verdicts
    render, and they disagree on the interesting word the way the facts
    above say they should."""
    found = stage.find_word()
    assert found is not None
    word, _pieces = found
    response = client.post("/stage/denckring/act", data={"word": word})
    normalised = " ".join(response.text.split())
    assert "off the rings — always true" in normalised
    assert "a word German knows — yes" in normalised


def test_find_me_one_lands_on_a_word_off_the_rings_and_in_the_lexicon() -> None:
    """The button's whole claim: a bounded server-side search that lands on a
    word both verdicts would say yes to, without a viewer sitting through the
    ~4,900 tries a random turn needs on average."""
    from denckring import check

    found = stage.find_word()
    assert found is not None
    word, pieces = found
    assert check("denckring", word, lang="de").satisfied is True
    assert stage.german_pack().is_word(word) is True
    # The pieces returned are the exact segmentation the discs would spin to,
    # not merely a word believed to match it.
    assert "".join(pieces) == word


def test_find_me_one_can_report_failure_honestly() -> None:
    """A budget of zero tries can never find anything — the search must say
    so rather than hang or claim a word it never found."""
    assert stage.find_word(attempts=0) is None


def test_find_me_one_route_turns_the_discs_to_a_real_word() -> None:
    response = client.post("/stage/denckring/act", data={"find": "1"})
    assert response.status_code == 200
    assert "data-pieces=" in response.text
    assert "a word German knows — yes" in " ".join(response.text.split())


def test_rhyme_endings_are_all_curated_and_clean() -> None:
    """Every offered ending is one this project chose to show on camera, and
    every word its sweep can produce is real — the curation the report talks
    about, pinned rather than only asserted."""
    for ending in stage.RHYME_ENDINGS:
        sweep = stage.rhyme_sweep(ending)
        hits = [word for word in sweep if word]
        assert hits, ending.label
        for word in hits:
            assert stage.german_pack().is_word(word) is True
            assert word.casefold().endswith(
                (ending.mittelbuchstabe + ending.endbuchstabe + ending.nachsylbe).casefold()
            )


def test_rhyme_sweep_yields_match_the_measured_counts() -> None:
    """The report's own headline numbers, pinned against the shipped lexicon:
    -acken 24, -ecken 23, -allen 17."""
    expected = {"-acken": 24, "-ecken": 23, "-allen": 17}
    for label, count in expected.items():
        ending = stage.rhyme_ending(label)
        assert ending is not None
        hits = [word for word in stage.rhyme_sweep(ending) if word]
        assert len(hits) == count


def test_the_rhyme_route_sweeps_a_locked_ending() -> None:
    response = client.post("/stage/denckring/rhyme", data={"ending": "-acken"})
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert "24 of 60 real — -acken" in normalised
    assert "Backen" in normalised


def test_the_rhyme_route_refuses_an_unknown_ending() -> None:
    response = client.post("/stage/denckring/rhyme", data={"ending": "-nonsense"})
    assert response.status_code == 200
    assert "choose an ending" in response.text.lower()


def test_the_scene_offers_every_curated_ending() -> None:
    response = client.get("/stage/denckring")
    for ending in stage.RHYME_ENDINGS:
        assert f'value="{ending.label}"' in response.text


def test_the_scene_renders_without_any_corpus() -> None:
    """Every machine except the author's has an empty DENCKRING_CORPORA. A scene that
    exploded there would be worse than one that explains itself (ADR 0020: corpora are
    never shipped). `corpora.available` is a plain function with nothing to clear —
    it re-globs the directory on every call, so pointing the env var elsewhere is
    the whole setup."""
    import os

    original = os.environ.get("DENCKRING_CORPORA")
    os.environ["DENCKRING_CORPORA"] = "/nonexistent-for-this-test"
    try:
        response = client.get("/stage/ideenwuerfeln")
        assert response.status_code == 200
        assert "no corpus" in response.text.lower()
    finally:
        if original is None:
            os.environ.pop("DENCKRING_CORPORA", None)
        else:
            os.environ["DENCKRING_CORPORA"] = original


def test_each_corpus_maps_to_a_register() -> None:
    """The corpora already carry the marker that switches the scene's look:
    `style: jean_paul` and `style: modern`."""
    assert stage.register_for("jean_paul") == "baroque"
    assert stage.register_for("modern") == "modern"
    assert stage.register_for("anything-else") == "modern"


def test_slips_of_matches_each_line_back_to_its_field() -> None:
    """A viewer has to be able to see the field each slip was filed under —
    that's what makes a cross-field collision visible rather than merely
    claimed. A line the corpus has no record of (should not happen, but the
    scene should not crash if it does) is labelled rather than dropped, and
    marked as not filed under the headword since nothing backs that claim."""
    import json

    text = json.dumps(
        {
            "entries": [
                {"text": "a fact about beetles", "domain": "Entomologie", "headwords": ["bug"]},
                {"text": "a fact about kings", "domain": "Geschichte"},
            ]
        }
    )
    slips = stage.slips_of(
        text, "a fact about beetles\na fact about kings\nsomething unfiled", "bug"
    )
    assert [(s.text, s.domain, s.filed) for s in slips] == [
        ("a fact about beetles", "Entomologie", True),
        ("a fact about kings", "Geschichte", False),
        ("something unfiled", "unfiled", False),
    ]


def _write_corpus(tmp_path: Path, entries: list[dict[str, object]]) -> Path:
    """A minimal corpus file inside a temp `DENCKRING_CORPORA`, so the throw
    route can be exercised without any real corpus on disk — the only path CI
    ever runs."""
    import json

    path = tmp_path / "test-corpus.json"
    path.write_text(json.dumps({"name": "test corpus", "style": "modern", "entries": entries}))
    return path


def test_the_throw_route_without_a_corpus_path_says_so() -> None:
    """A bare POST with no `corpus_path` is exactly what the picker sends when
    `choices` was empty and the form never rendered a select at all — it needs
    no corpus file on disk, and is the branch CI actually exercises."""
    response = client.post("/stage/ideenwuerfeln/act", data={"headword": "Licht"})
    assert response.status_code == 200
    assert "no corpus chosen" in response.text.lower()


def test_a_throw_collides_distinct_fields_and_labels_each_slip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The scene's whole point: a headword filed across several fields comes
    back as slips from different fields, and each one says which."""
    corpus_path = _write_corpus(
        tmp_path,
        [
            {"text": "excerpt alpha", "domain": "Alpha", "headwords": ["word"]},
            {"text": "excerpt beta", "domain": "Beta", "headwords": ["word"]},
            {"text": "excerpt gamma", "domain": "Gamma", "headwords": ["word"]},
        ],
    )
    monkeypatch.setenv("DENCKRING_CORPORA", str(tmp_path))
    response = client.post(
        "/stage/ideenwuerfeln/act",
        data={"corpus_path": str(corpus_path), "headword": "word"},
    )
    assert response.status_code == 200
    for domain in ("Alpha", "Beta", "Gamma"):
        assert domain in response.text
    assert "not filed across enough fields" not in response.text


def test_a_throw_falls_back_and_says_so_when_a_headword_spans_too_few_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A headword whose pool sits in a single field — Jean Paul's own corpus is
    exactly like this — still throws, but the page says plainly that it fell
    back to a plain draw rather than showing a same-field throw as a
    collision it never was."""
    corpus_path = _write_corpus(
        tmp_path,
        [
            {"text": "excerpt one", "domain": "Register", "headwords": ["Licht"]},
            {"text": "excerpt two", "domain": "Register", "headwords": ["Licht"]},
            {"text": "excerpt three", "domain": "Register", "headwords": ["Licht"]},
        ],
    )
    monkeypatch.setenv("DENCKRING_CORPORA", str(tmp_path))
    response = client.post(
        "/stage/ideenwuerfeln/act",
        data={"corpus_path": str(corpus_path), "headword": "Licht"},
    )
    assert response.status_code == 200
    assert "not filed across enough fields" in response.text
    # Not shown as an error — `.notice` is the checker's own failure colour,
    # and a thin corpus is neither a failure nor the checker's business.
    assert "notice" not in response.text


def test_a_thin_headword_pool_is_widened_and_the_page_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`apply` widens a headword pool too thin to fill `slots` entries to the
    *whole corpus*, silently — the exact case a pre-flight check of the
    headword's own pool cannot see coming, because it never looks past that
    pool. Only one entry is filed under "rare"; the other three fields come
    from entries with no headword at all, so the throw can find three
    distinct fields only by reaching past the headword. The page must say
    that plainly, and must not caption slips that mostly aren't "rare" as if
    they were "Filed under 'rare'"."""
    corpus_path = _write_corpus(
        tmp_path,
        [
            {"text": "excerpt alpha rare", "domain": "Alpha", "headwords": ["rare"]},
            {"text": "excerpt beta", "domain": "Beta"},
            {"text": "excerpt gamma", "domain": "Gamma"},
        ],
    )
    monkeypatch.setenv("DENCKRING_CORPORA", str(tmp_path))
    response = client.post(
        "/stage/ideenwuerfeln/act",
        data={"corpus_path": str(corpus_path), "headword": "rare"},
    )
    assert response.status_code == 200
    for domain in ("Alpha", "Beta", "Gamma"):
        assert domain in response.text
    # Normalised the way `test_the_harsdoerffer_quotation_is_reproduced_exactly`
    # normalises: the wording is the claim, and the template's indentation is
    # not — a pure re-wrap should not fail a test about what the page says.
    normalised = " ".join(response.text.split())
    assert (
        "&ldquo;rare&rdquo; was too thin to draw three excerpts from — this throw was made "
        "across the whole corpus instead."
    ) in normalised
    assert "Filed under" not in response.text
    assert "Drawn across the whole corpus" in response.text
    # Not the fallback case — three distinct fields were found, just not from
    # the headword's own pool, so the fallback wording would be false here.
    assert "not filed across enough fields" not in response.text


def test_the_witz_disclaimer_survives_a_real_throw(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The disclaimer is the requirement with the highest cost of being wrong
    on this whole scene — pin its actual words, not just that some element
    exists, so a future edit that quietly drops or rewords it fails a test
    rather than only a human review."""
    corpus_path = _write_corpus(
        tmp_path,
        [
            {"text": "excerpt alpha", "domain": "Alpha", "headwords": ["word"]},
            {"text": "excerpt beta", "domain": "Beta", "headwords": ["word"]},
            {"text": "excerpt gamma", "domain": "Gamma", "headwords": ["word"]},
        ],
    )
    monkeypatch.setenv("DENCKRING_CORPORA", str(tmp_path))
    # A key that only has to be present for `witz.available()` to be true —
    # this test never calls `/p/ideenwuerfeln/witz`, so nothing here reaches
    # the network.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-a-real-one")
    response = client.post(
        "/stage/ideenwuerfeln/act",
        data={"corpus_path": str(corpus_path), "headword": "word"},
    )
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert (
        "A reading, not a verdict. No <code>Report</code> is produced and no checker "
        "consults it — the Witz is the step no program performs."
    ) in normalised


# ── scene three: Arca musarithmica ──────────────────────────────────────────


def test_the_arca_scene_uses_a_tablet_that_is_not_kirchers() -> None:
    """Kircher's own pitch numbers are not shipped, and the golden fixture's tablet is
    synthetic and says so. The scene must not imply otherwise."""
    assert "4" in str(sorted(stage.tablet().lengths()))
    response = client.get("/stage/arca")
    assert response.status_code == 200
    assert "not his" in response.text


def test_the_pattern_the_scene_offers_really_sets_the_phrase() -> None:
    from denckring import check

    source = "the cat sat down"
    pattern = stage.tablet().patterns(4)[0]
    report = check("arca_musarithmica", pattern, source=source, pinakes=stage.TABLET)
    assert report.satisfied is True


def test_the_arca_scene_renders() -> None:
    response = client.get("/stage/arca")
    assert response.status_code == 200
    assert "Arca musarithmica" in response.text


def test_measuring_a_phrase_offers_only_the_tablets_own_columns() -> None:
    """A bare measurement (no column drawn yet) must offer exactly what
    `stage.tablet()` carries for that length — nothing invented on the page."""
    response = client.post("/stage/arca/act", data={"phrase": "the cat sat down"})
    assert response.status_code == 200
    assert "4" in response.text
    for pattern in stage.tablet().patterns(4):
        assert pattern in response.text
    # No column has been drawn, so there is nothing yet for `check` to have
    # verified — the page must not claim a verdict it never produced.
    assert "verdict" not in response.text


def test_drawing_an_offered_column_is_verified_against_the_tablet() -> None:
    """Choosing one of the tablet's own columns must show the real `check`
    verdict — the scene's whole claim, made concrete for one phrase."""
    phrase = "the cat sat down"
    pattern = stage.tablet().patterns(4)[0]
    response = client.post("/stage/arca/act", data={"phrase": phrase, "pattern": pattern})
    assert response.status_code == 200
    assert "verdict yes" in response.text


def test_a_phrase_the_tablet_cannot_set_says_so_plainly() -> None:
    """ "hello there" measures three syllables, and this tablet only carries
    columns for four and six — the box cannot set it, which is a fact about
    the box (ADR 0021), not an error to paper over."""
    response = client.post("/stage/arca/act", data={"phrase": "hello there"})
    assert response.status_code == 200
    assert "3" in response.text
    assert "no column" in response.text.lower()


def test_the_arca_scene_measures_with_the_procedures_own_counter() -> None:
    """The scene must count syllables the same way `arca_musarithmica` itself
    does — `line_syllables` — rather than a second, independently drifting way
    of measuring a phrase."""
    response = client.post("/stage/arca/act", data={"phrase": "the dog ran home to eat"})
    assert response.status_code == 200
    assert "6" in response.text
    for pattern in stage.tablet().patterns(6):
        assert pattern in response.text


# ── scene four: N+7 ─────────────────────────────────────────────────────────


def test_the_displacement_the_scene_animates_is_the_one_the_checker_accepts() -> None:
    """The scene's whole claim: what `displace` produces is a real n_plus_7
    displacement of the source it started from."""
    from denckring import check
    from denckring.procedures.n_plus_7 import displace

    source = "the cat sat on the table"
    produced = displace(source, stage.pack(), 7)
    assert check("n_plus_7", produced, source=source).satisfied is True


def test_the_scene_shows_the_words_a_noun_travels_past() -> None:
    """Pinned against Open English WordNet 2024: `cat` sits at index 8402 and
    lands on `catacomb` at 8409, eight entries inclusive. If this ever fails,
    the noun list has changed underneath the project — check `CHANGELOG.md`
    before touching this test; it exists to catch exactly that."""
    steps = stage.displacement("the cat sat on the table", 7)
    cat = next(step for step in steps if step.word == "cat")
    assert cat.replacement == "catacomb"
    assert len(cat.neighbours) == 8
    assert cat.neighbours[0] == "cat" and cat.neighbours[-1] == "catacomb"


def test_the_n_plus_7_scene_renders() -> None:
    response = client.get("/stage/n_plus_7")
    assert response.status_code == 200
    assert "catacomb" in response.text


def test_the_n_plus_7_scene_names_the_wordnet_migration() -> None:
    """The catafalque-to-catacomb story is the caption this scene exists to
    tell — pin the actual wording, not just that some note is present."""
    response = client.get("/stage/n_plus_7")
    assert "catafalque" in response.text
    assert "Open English WordNet" in response.text


def test_a_displaced_text_is_shown_beside_its_real_verdict() -> None:
    """Both halves of the round trip: `displace` produces the text, and
    `check` confirms it against the very source that was posted."""
    response = client.post("/stage/n_plus_7/act", data={"source": "the cat sat on the table"})
    assert response.status_code == 200
    assert "catacomb" in response.text
    assert "verdict yes" in response.text


def test_a_source_with_no_noun_is_not_called_a_displacement() -> None:
    """`displace("quickly ran", …)` gives back "quickly ran" and `check` reports
    satisfied — vacuously, there being no noun in it to displace wrongly. True
    by the checker's semantics and misleading on camera, in the one scene with
    a free-text box a recorder types into. The panel says what happened
    instead."""
    from denckring import check
    from denckring.procedures.n_plus_7 import displace

    source = "quickly ran"
    produced = displace(source, stage.pack(), 7)
    assert produced == source
    assert check("n_plus_7", produced, source=source).satisfied is True

    response = client.post("/stage/n_plus_7/act", data={"source": source})
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert "a real displacement of the source" not in normalised
    assert "nothing moved: the source carries no noun the list knows" in normalised


def test_displacing_a_new_source_re_renders_the_reels() -> None:
    """Every other scene here re-renders everything its action touched. Reels
    still reading "cat" beside a panel displacing something else would be this
    scene's own version of describing what it did not do — and the caption that
    tells the catafalque story goes with them, since it is true of one word on
    one reel."""
    response = client.post("/stage/n_plus_7/act", data={"source": "the dog ran home"})
    assert response.status_code == 200
    assert 'id="n7-reels"' in response.text
    assert 'hx-swap-oob="true"' in response.text
    assert "doggedness" in response.text
    assert "homefolk" in response.text
    assert "catacomb" not in response.text
    assert "catafalque" not in response.text


def test_a_blank_source_produces_nothing_to_check() -> None:
    """No source, no displacement — the fragment must not claim a verdict
    `check` was never asked to make."""
    response = client.post("/stage/n_plus_7/act", data={"source": ""})
    assert response.status_code == 200
    assert "verdict" not in response.text


# ── scene five: Ghazal ───────────────────────────────────────────────────────


def test_the_ghazal_examples_are_what_the_scene_claims() -> None:
    """One passes, one fails on the couplet the scene points at. A scene whose
    counterexample quietly passed would be teaching the wrong thing."""
    from denckring import check

    assert check("ghazal", stage.GHAZAL_GOOD).satisfied is True
    broken = check("ghazal", stage.GHAZAL_BROKEN)
    assert broken.satisfied is False
    assert broken.violations


def test_the_broken_example_fails_on_the_qafia_alone() -> None:
    """The brief's own requirement: the counterexample must fail for the one
    reason the scene points at, not some other one. `GHAZAL_BROKEN` changes
    only the closing couplet's qafia, so the radif must still hold everywhere
    and the only violation raised must be `broken_qafia`, naming the actual
    swapped word rather than some other line."""
    from denckring import check

    report = check("ghazal", stage.GHAZAL_BROKEN)
    assert [v.rule for v in report.violations] == ["broken_qafia"]
    assert report.violations[0].found == "book"


def test_the_ghazal_scene_renders_the_good_example_already_marked() -> None:
    """The pattern has to be visible before a viewer reads a word of
    explanation — the radif and qafia are marked on first paint, not only
    after an action."""
    response = client.get("/stage/ghazal")
    assert response.status_code == 200
    assert "role-radif" in response.text
    assert "role-qafia" in response.text
    assert "state-defines" in response.text
    assert "verdict yes" in response.text


def test_the_ghazal_scene_names_the_form_without_being_coy() -> None:
    """The set's only non-Western form — the scene must say so plainly."""
    response = client.get("/stage/ghazal")
    assert "Persian and Urdu" in response.text
    assert "Traditional" in response.text


def test_checking_the_broken_couplet_marks_the_fault_the_checker_actually_found() -> None:
    """The scene's claim: the checker finds the fault in the couplet the page
    points at. `stage.ghazal_reading` must mark exactly the word `check`
    itself flagged as `state-bad`, and nothing else — including not the
    radif, which this counterexample leaves untouched."""
    from denckring import check

    report = check("ghazal", stage.GHAZAL_BROKEN)
    reading = stage.ghazal_reading(stage.GHAZAL_BROKEN)
    assert reading is not None
    bad_words = [word for line in reading.lines for word in line.words if word.state == "bad"]
    assert [word.text for word in bad_words] == [report.violations[0].found]
    assert all(word.role == "qafia" for word in bad_words)
    # Every radif still holds — this counterexample never touches it.
    assert not any(
        word.role == "radif" and word.state == "bad"
        for line in reading.lines
        for word in line.words
    )

    response = client.post("/stage/ghazal/act", data={"text": stage.GHAZAL_BROKEN})
    assert response.status_code == 200
    assert "verdict no" in response.text
    assert "broken qafia" in response.text
    assert "state-bad" in response.text
    assert "missing radif" not in response.text


def test_checking_the_good_couplets_shows_every_carrying_line_holding() -> None:
    response = client.post("/stage/ghazal/act", data={"text": stage.GHAZAL_GOOD})
    assert response.status_code == 200
    assert "verdict yes" in response.text
    assert "state-bad" not in response.text
    # Both roles recur down the page — not just on the opening couplet.
    assert response.text.count("role-radif") >= 3
    assert response.text.count("role-qafia") >= 3


def test_the_ghazal_scene_promises_no_marking_it_cannot_do() -> None:
    """`.proof-text` carries real <mark> spans on the bench page, and the label
    over it promises them. Every ghazal violation is a whole-line judgement
    with `offset=None`, so `mark_up` here only ever escapes the text — the
    block appears when there is a mark in it and not before. The fault is still
    pointed at, on the couplets themselves."""
    from explorer import bench

    from denckring import check

    report = check("ghazal", stage.GHAZAL_BROKEN)
    assert [v.offset for v in report.violations] == [None]
    assert "<mark" not in bench.mark_up(stage.GHAZAL_BROKEN, report)

    response = client.post("/stage/ghazal/act", data={"text": stage.GHAZAL_BROKEN})
    assert response.status_code == 200
    assert "The text, as checked" not in response.text
    assert "proof-text" not in response.text
    assert "state-bad" in response.text


def test_a_blank_ghazal_produces_nothing_to_check() -> None:
    """No text, nothing to read — the fragment must not claim a verdict
    `check` was never asked to make."""
    response = client.post("/stage/ghazal/act", data={"text": ""})
    assert response.status_code == 200
    assert "verdict" not in response.text
    assert "Nothing to read yet" in response.text


def test_a_single_couplet_is_a_whole_ghazal() -> None:
    """The minimal case: two lines, no couplet after the opening one. The
    checker's own `carriers` list (`[1, *range(3, len(lines), 2)]`) is empty
    past index 1 here, so there is nothing left to require — this must read
    as satisfied, not as a poem too short to judge."""
    from denckring import check

    two_line = "i cannot find the road tonight\nthe lamps have all been slowed tonight"
    report = check("ghazal", two_line)
    assert report.satisfied is True
    assert report.violations == []

    reading = stage.ghazal_reading(two_line)
    assert reading is not None
    assert len(reading.lines) == 2
    assert reading.radif == "tonight"
    assert reading.qafia == "road"
    opening, carrier = reading.lines
    opening_roles = {(w.role, w.state) for w in opening.words if w.role}
    assert opening_roles == {("radif", "defines"), ("qafia", "defines")}
    carrier_roles = {(w.role, w.state) for w in carrier.words if w.role}
    assert carrier_roles == {("radif", "ok"), ("qafia", "ok")}


def test_an_opening_line_with_no_words_sets_no_radif() -> None:
    """An opening line the pack cannot find a single word on — digits only,
    here — leaves `radif` and `qafia` both empty rather than raising. Every
    later carrying line's closing word can then never equal that empty
    string, so `check` itself raises `missing_radif` (`expected=''`) on each
    one, and `ghazal_reading` must mark exactly those words `state-bad` —
    the same real disagreement the checker found, not a guessed one — while
    leaving their qafia position unscored, matching the checker's own
    continue-past-an-unmatched-radif behaviour."""
    from denckring import check

    no_radif = (
        "42 17\nsome line that ends tonight\nanother free line here\nand closes again tonight"
    )
    report = check("ghazal", no_radif)
    assert report.satisfied is False
    assert [(v.rule, v.expected) for v in report.violations] == [
        ("missing_radif", ""),
        ("missing_radif", ""),
    ]

    reading = stage.ghazal_reading(no_radif)
    assert reading is not None
    assert reading.radif == ""
    assert reading.qafia == ""
    opening, first_carrier, free, second_carrier = reading.lines
    assert opening.words == []
    assert free.carries is False
    for line in (first_carrier, second_carrier):
        assert line.carries is True
        radif_words = [w for w in line.words if w.role == "radif"]
        assert [w.state for w in radif_words] == ["bad"]
        # The checker never even looks at a carrying line's qafia once its
        # radif has already failed (`_check` `continue`s past it) — neither
        # does the display, so that word is left with no state at all.
        qafia_words = [w for w in line.words if w.role == "qafia"]
        assert [w.state for w in qafia_words] == [""]

    # The page must not print the empty radif/qafia as bare quotation marks.
    response = client.post("/stage/ghazal/act", data={"text": no_radif})
    assert response.status_code == 200
    assert "&ldquo;&rdquo;" not in response.text
    assert "no word for a" in response.text
