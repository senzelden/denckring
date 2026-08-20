"""The stage. Appearance is not tested; the claims underneath it are."""

from __future__ import annotations

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
    assert (
        "&ldquo;rare&rdquo; was too thin to draw three excerpts\n"
        "    from — this throw was made across the whole corpus instead."
    ) in response.text
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
    assert (
        "A reading, not a verdict. No <code>Report</code> is produced and no checker "
        "consults\n    it — the Witz is the step no program performs."
    ) in response.text


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
