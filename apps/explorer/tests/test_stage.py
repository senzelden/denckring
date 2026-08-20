"""The stage. Appearance is not tested; the claims underneath it are."""

from __future__ import annotations

import math
import random
import re
from itertools import pairwise
from pathlib import Path

import pytest
from explorer import bench, corpora, stage
from explorer.app import app
from fastapi.testclient import TestClient

from denckring.core.protocol import LanguagePack

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


def _found_word() -> tuple[str, list[int]]:
    """`stage.find_word` is a bounded random search over ~21,000 possible real
    words and can rarely exhaust its budget without a hit — not a bug, just
    an unlucky draw (`test_find_me_one_can_report_failure_honestly` pins that
    this can happen at all, with a budget of zero forcing it). The tests
    calling this one are about what a found word looks like, not about the
    search's own completeness, so they retry past that rare draw rather than
    flake on it — three tries makes the whole thing fail only if the same
    draw goes unlucky three times running, which measured empirically never
    happened in hundreds of calls (see the task report)."""
    for _ in range(3):
        found = stage.find_word()
        if found is not None:
            return found
    raise AssertionError("find_word failed 3 times running — investigate, do not just retry more")


def test_the_index_lists_every_scene() -> None:
    response = client.get("/stage")
    assert response.status_code == 200
    for scene in stage.SCENES:
        assert scene.title in response.text


def test_the_indexs_own_count_comes_from_the_scene_list() -> None:
    """The caption used to type its own number, and spent three rounds saying
    "three procedures" over a list of six. It reads `scenes | length` now, so
    this pins the property rather than the figure: whatever `SCENES` holds is
    what the page announces, and adding or removing a scene cannot leave the
    line stale again."""
    normalised = " ".join(client.get("/stage").text.split())
    assert f"{len(stage.SCENES)} procedures, driven by hand." in normalised


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
    is threaded through three separate route signatures, so a typo in one would
    ship unnoticed until somebody sat down to record that scene."""
    with_chrome = client.get(f"/stage/{slug}")
    assert with_chrome.status_code == 200
    assert 'id="stage"' in with_chrome.text
    assert "stage-caption" in with_chrome.text

    without = client.get(f"/stage/{slug}?chrome=off")
    assert without.status_code == 200
    assert 'id="stage"' in without.text
    assert "stage-caption" not in without.text


#: The `data-sync` declaration each scene's driving `<select>` carries, and
#: the id/key pairs it names. Three scenes wrote three copies of the same
#: toggle-sync script before it was extracted to `_stage_sync.html`; what the
#: markup now has to get right is the declaration, so that is what is pinned.
_SYNC_DECLARATIONS = {
    "n_plus_7": [("source-field", "example")],
    "word_ladder": [("start-field", "start"), ("target-field", "target")],
}


def _assert_sync_wiring(html: str, pairs: list[tuple[str, str]]) -> None:
    """Every field and dataset key the declaration names is really on the page.

    The shared script fails silently on a name that is not there — it filters
    missing fields out and syncs the rest — which is exactly the kind of quiet
    half-working control this stage must not ship, and exactly what a test
    reading the markup can catch without running any JavaScript."""
    normalised = " ".join(html.split())
    assert normalised.count('data-sync="') == 1
    assert normalised.count('document.querySelectorAll("[data-sync]")') == 1
    declaration = " ".join(f"{field}:{key}" for field, key in pairs)
    assert f'data-sync="{declaration}"' in normalised
    for field, key in pairs:
        assert f'id="{field}"' in normalised, field
        assert f"data-{key}=" in normalised, key


@pytest.mark.parametrize("slug", sorted(_SYNC_DECLARATIONS))
def test_the_shared_toggle_sync_is_wired_to_fields_that_exist(slug: str) -> None:
    _assert_sync_wiring(client.get(f"/stage/{slug}").text, _SYNC_DECLARATIONS[slug])


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


def test_the_plate_replaces_the_quotation() -> None:
    """The scene used to quote Harsdörffer from secondary sources and said so
    on the page. That caveat comes off now that the print was read directly
    (see `primary-source.md`) — the plate itself, credited exactly to the
    Wolfenbüttel copy, stands where the quotation used to."""
    response = client.get("/stage/denckring")
    normalised = " ".join(response.text.split())
    assert '<img src="/static/denckring-plate.jpg"' in response.text
    assert "quoted from secondary sources" not in normalised
    credit = "Herzog August Bibliothek Wolfenbüttel, 224.2 Quod., the leaf facing p. 517"
    assert credit in normalised
    assert "https://diglib.hab.de/drucke/224-2-quod/start.htm?image=00535" in normalised


def test_the_plate_and_the_legend_disagree_and_say_so() -> None:
    """The plate's own cartouche prints 48/60/12/120/24; the shipped
    transcription's legend prints 49/60/12/120/23 (see
    `test_the_rings_carry_the_transcribed_counts`). A viewer can see both at
    once now that the plate is on the page — the scene says so in one
    clause, adjusting neither figure."""
    normalised = " ".join(client.get("/stage/denckring").text.split())
    assert "48 &middot; 60 &middot; 12 &middot; 120 &middot; 24" in normalised
    assert "unreconciled" in normalised


def test_rhyme_mode_is_labelled_on_the_plate_not_inferred() -> None:
    """The plate's own cartouche calls the second ring "die 60
    Anfangsbuchstab und Reimbuchstaben" — rhyme mode is named on the device
    itself, not a reading this project imposed on it."""
    normalised = " ".join(client.get("/stage/denckring").text.split())
    assert "Reimbuchstaben" in normalised


def test_the_scene_opens_with_harsdoerffers_own_line_about_the_two_verdicts() -> None:
    """p. 517: turning the rings gives "blinde oder deutunglose Wörter" —
    until one is not. That is exactly what the two verdicts below it show."""
    normalised = " ".join(client.get("/stage/denckring").text.split())
    assert "blinde oder deutunglose Wörter" in normalised


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
    """First paint opens on Harsdörffer's own example, `Aas` (`stage.default_reading`,
    p. 517: "Aas (cadaver) &c."), rather than whatever each ring's own index 0
    happens to spell. The word panel is server-rendered through the same
    `_stage_word.html` partial every other route answers through, and the
    discs' `data-default-index` carries the exact positions `pieces` names —
    so a no-JS viewer sees precisely what "Read it" would report, and the
    discs and the panel can never open disagreeing."""
    from denckring import check

    word, positions = stage.default_reading()
    assert word == "Aas"
    assert check("denckring", word).satisfied is True

    response = client.get("/stage/denckring")
    assert f'data-positions="{"|".join(str(p) for p in positions)}">Aas</p>' in response.text
    # Each ring's own `data-default-index`, in ring order — the exact positions
    # the discs seed themselves from, not merely the same numbers somewhere
    # on the page.
    seeded = [int(match) for match in re.findall(r'data-default-index="(\d+)"', response.text)]
    assert seeded == positions


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
    set each disc's index from the position the server sent back. The
    invariant this pins: reading the discs off those positions, inward to
    outward, must give back exactly the word `check` was asked about — the
    discs and the checked word can never disagree, including after a spin."""
    from denckring import check
    from denckring.core.protocol import Constructive
    from denckring.core.registry import get

    procedure = get("denckring")
    assert isinstance(procedure, Constructive)
    word = procedure.apply("", lang="en")
    positions = stage.pieces_for(word)
    assert positions is not None
    slots = stage.rings().slots
    reassembled = "".join(
        _label(slot.alternatives, p) for slot, p in zip(slots, positions, strict=True)
    )
    assert reassembled == word
    assert check("denckring", word).satisfied is True


def test_the_two_verdicts_are_distinct() -> None:
    """A word built from the rings is always a reading of them — `check`
    cannot fail it, which is why the scene shows a second verdict that can.
    A word assembled directly from the rings' own index-0 alternatives is
    off-the-rings True; a made-up string of the same shape that the lexicon
    does not carry is German-knows False, even though neither verdict is
    about the other."""
    from denckring import check

    ring_word = "".join(_label(slot.alternatives, 0) for slot in stage.rings().slots)
    assert check("denckring", ring_word, lang="de").satisfied is True
    assert stage.german_pack().is_word(ring_word) is False

    real_word, _pieces = _found_word()
    assert check("denckring", real_word, lang="de").satisfied is True
    assert stage.german_pack().is_word(real_word) is True


def test_the_word_panel_shows_both_verdicts_distinctly() -> None:
    """The page itself, not just the two facts in isolation: both verdicts
    render, and they disagree on the interesting word the way the facts
    above say they should."""
    word, _pieces = _found_word()
    response = client.post("/stage/denckring/act", data={"word": word})
    normalised = " ".join(response.text.split())
    assert "off the rings — always true" in normalised
    assert "a word German knows — yes" in normalised


def test_find_me_one_lands_on_a_word_off_the_rings_and_in_the_lexicon() -> None:
    """The button's whole claim: a bounded server-side search that lands on a
    word both verdicts would say yes to, without a viewer sitting through the
    ~4,900 tries a random turn needs on average."""
    from denckring import check

    word, positions = _found_word()
    assert check("denckring", word, lang="de").satisfied is True
    assert stage.german_pack().is_word(word) is True
    # The positions returned are the exact ring indices the discs would spin
    # to, not merely a word believed to match it.
    slots = stage.rings().slots
    reassembled = "".join(
        _label(slot.alternatives, p) for slot, p in zip(slots, positions, strict=True)
    )
    assert reassembled == word


def test_find_me_one_can_report_failure_honestly() -> None:
    """A budget of zero tries can never find anything — the search must say
    so rather than hang or claim a word it never found."""
    assert stage.find_word(attempts=0) is None


def test_find_me_one_route_turns_the_discs_to_a_real_word() -> None:
    # A rare failed search (see `_found_word`) would come back through this
    # same route as `find_failed`, not a "data-positions" response — retried
    # here the same way, for the same reason.
    for _ in range(3):
        response = client.post("/stage/denckring/act", data={"find": "1"})
        assert response.status_code == 200
        if "data-positions=" in response.text:
            break
    else:
        raise AssertionError("find_word failed 3 times running — investigate, do not retry more")
    assert "a word German knows — yes" in " ".join(response.text.split())


def test_find_word_never_returns_a_word_the_blocklist_rejects() -> None:
    """`find_word`'s own filter, exercised rather than only read — the bug a
    review caught was exactly this path returning `is_word`-true words with
    no filter on top at all. Repeated rather than run once, since a single
    draw proves little about a search over ~21,000 possible real words."""
    for _ in range(30):
        word, _pieces = _found_word()
        assert stage.fit_for_stage(word) is True, word


def test_turn_them_for_me_never_returns_a_word_the_blocklist_rejects() -> None:
    """ "Turn them for me" does not require a real word — that is the point
    of the "off the rings" verdict — so it is the one path where a random
    draw could in principle spell a blocked stem inside a nonsense string,
    not just inside a real word. Run through the actual route, repeatedly,
    rather than asserted from the retry loop's own logic."""
    for _ in range(30):
        response = client.post("/stage/denckring/act", data={"turn": "1"})
        assert response.status_code == 200
        match = re.search(r'<p class="word"[^>]*>([^<]*)</p>', response.text)
        assert match is not None
        assert stage.fit_for_stage(match.group(1)) is True, match.group(1)


def test_fit_for_stage_rejects_the_known_vulgarities() -> None:
    """The concrete failure a review caught by hand: `-acken`'s sweep put
    "Kacken" on screen, and `find_word` had no filter at all. Pinned here
    against the predicate directly, on the exact words that failure
    surfaced, plus one inflected form the rings can also assemble around
    the same stem, so a substring match rather than a whole-word one is
    load-bearing here rather than incidental."""
    for word in ("Kacken", "Ficken", "Titten", "verkacken", "gefickt"):
        assert stage.fit_for_stage(word) is False, word
    # An ordinary word is not collateral damage of the fix — see stage.py's
    # own comment on why "schei" and "arsch" were rejected as stems.
    for word in ("entscheiden", "bescheiden", "erscheinen", "Marsch", "harsch"):
        assert stage.fit_for_stage(word) is True, word


def test_fit_for_stage_blocks_spast_and_accepts_the_trade() -> None:
    """Ruling 1: "Spast" is an ableist slur with no innocent reading, and is
    producible by these rings, so the stem is blocked — even though that
    also costs "spastisch", a genuine clinical adjective (also producible).
    That trade is deliberate, so both directions are pinned here."""
    assert stage.fit_for_stage("Spast") is False
    assert stage.fit_for_stage("spastisch") is False


def test_fit_for_stage_blocks_schlampen_precisely() -> None:
    """Ruling 2, fix round 3: "schlampen" is blocked as an *exact* whole
    word (`_BLOCKED_EXACT`), not a substring stem, because "Schlampe"
    itself is not producible by this device at all (`pieces_for` returns
    None) while "Schlampen" is. The first version of this ruling matched
    "schlampen" as a substring, which is precise enough to spare
    "schlampig" (sloppy) but not "verschlampen" (to mislay something
    through carelessness) — both ordinary, producible German words, and
    both pinned here so a future substring regression is caught."""
    assert stage.pieces_for("Schlampe") is None
    assert stage.pieces_for("verschlampen") is not None
    assert stage.fit_for_stage("Schlampen") is False
    assert stage.fit_for_stage("schlampig") is True
    assert stage.fit_for_stage("verschlampen") is True


def test_fit_for_stage_blocks_untermensch_and_strullen_without_collateral() -> None:
    """Round two's two new stems. Both are producible by these rings, both
    are the register this list exists to catch, and both were audited against
    the whole shipped lexicon before being added as stems rather than exact
    forms: nothing but the slur itself contains "untermensch", and nothing but
    the vulgar verb contains "strull", so neither takes an ordinary word down
    with it."""
    for word in ("Untermensch", "Untermenschen", "strullen", "gestrullt"):
        assert stage.fit_for_stage(word) is False, word
    assert stage.pieces_for("Untermensch") is not None
    assert stage.pieces_for("strullen") is not None


def test_fit_for_stage_blocks_poppen_precisely() -> None:
    """An exact-form entry, for the same reason "schlampen" is one: "poppen"
    is the crude register the blocked "bums" belongs to, but a "popp" stem
    would take "poppig" (garish), "aufpoppen" and "verpoppen" with it — all
    ordinary, all producible. Every form of the vulgar verb these rings can
    spell is blocked; the ordinary neighbours survive, and so does "Popper",
    which names a youth subculture rather than anything vulgar."""
    for word in ("Popp", "poppen", "Poppet"):
        assert stage.fit_for_stage(word) is False, word
        assert stage.pieces_for(word) is not None, word
    for word in ("poppig", "aufpoppen", "verpoppen", "Popper"):
        assert stage.fit_for_stage(word) is True, word


def test_turn_them_for_me_never_shows_a_draw_that_was_never_checked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fix round 3, Important 2: the retry loop used to check the current
    word, then redraw on failure — so a run that missed on every one of
    TURN_ATTEMPTS draws exited having just redrawn, and that final,
    unchecked draw reached the page. The measured ~0.0315% per-draw failure
    rate makes that need ~50 consecutive misses, which no ordinary test run
    will ever hit by chance, so the failure path is forced directly here
    rather than trusted to the odds. With every draw failing, the route must
    show no word that was never checked — and must say so rather than come
    back as an empty panel, which is what `find_word`'s own failure path has
    always done and what this one only claimed in a comment to do."""
    monkeypatch.setattr(stage, "fit_for_stage", lambda word: False)
    response = client.post("/stage/denckring/act", data={"turn": "1"})
    assert response.status_code == 200
    assert "data-positions=" not in response.text
    assert "verdict-rings" not in response.text
    assert "verdict-known" not in response.text
    normalised = " ".join(response.text.split())
    assert (
        f"all {stage.TURN_ATTEMPTS:,} turns landed on something this stage will not show"
    ) in normalised


def test_rhyme_sweep_locked_positions_are_true_indices() -> None:
    """`RhymeSweep.mittelbuchstabe_index`, `.endbuchstabe_index` and
    `.nachsylbe_index` are the true positions the client sets those three
    rings to — pinned here by reading each one back through `_label` against
    the real slot, the same way the client's own `label()` would, rather
    than trusting the number is merely *an* int."""
    slots = stage.rings().slots
    mittelbuchstabe = next(s for s in slots if s.name == "mittelbuchstabe")
    endbuchstabe = next(s for s in slots if s.name == "endbuchstabe")
    nachsylbe = next(s for s in slots if s.name == "nachsylbe")
    for ending in stage.RHYME_ENDINGS:
        sweep = stage.rhyme_sweep(ending)
        assert _label(mittelbuchstabe.alternatives, sweep.mittelbuchstabe_index) == (
            ending.mittelbuchstabe
        )
        assert _label(endbuchstabe.alternatives, sweep.endbuchstabe_index) == ending.endbuchstabe
        assert _label(nachsylbe.alternatives, sweep.nachsylbe_index) == ending.nachsylbe


def test_the_second_occurrence_of_a_repeated_part_still_yields_a_true_position() -> None:
    """The ring-positioning bug, pinned against the real data that made it
    possible: `endbuchstabe` genuinely repeats two of its 120 parts — 'f'
    and 'ls', each twice, at two different indices. `parts.indexOf(piece)`
    — the old client's own computation, searching a ring's parts for
    matching *text* — can only ever resolve to the *first* of those two,
    never the second, however a ring actually came to stand on it (a manual
    click moves a ring by index alone, exactly like this).

    Driving `endbuchstabe` directly to its second occurrence — the same way
    `test_a_manual_turn_still_spells_a_denckring_word` drives any ring to any
    index — still spells a real denckring word. Reading that word back
    through `stage.pieces_for` must give back a genuine index for
    `endbuchstabe`, checked here by type, not merely by value: the pre-fix
    contract handed back the piece's own *text* ("f"), and `isinstance("f",
    int)` is `False` where `isinstance(15, int)` is `True` — this is what
    makes the assertion fail against the old code specifically, not only
    against a data fixture that no longer matches. Only the first occurrence
    is reachable this way (both occurrences show identical text, which is
    the defect in the first place, not something this fix changes) — the
    fix is that the position is now an index a client uses directly, never
    text it has to re-search a ring for."""
    from denckring import check

    slots = stage.rings().slots
    endbuchstabe_index = next(i for i, s in enumerate(slots) if s.name == "endbuchstabe")
    endbuchstabe = slots[endbuchstabe_index]
    alternatives = endbuchstabe.alternatives
    first = alternatives.index("f")
    second = first + 1 + alternatives[first + 1 :].index("f")
    assert alternatives[second] == "f"
    assert second != first  # the repeat is real, not a mistaken premise

    # Drive the ring directly to the second occurrence — an index, not a
    # text search — the same way a manual click would.
    word = "".join(
        _label(slot.alternatives, second if i == endbuchstabe_index else 0)
        for i, slot in enumerate(slots)
    )
    assert check("denckring", word).satisfied is True

    positions = stage.pieces_for(word)
    assert positions is not None
    assert isinstance(positions[endbuchstabe_index], int)
    assert _label(alternatives, positions[endbuchstabe_index]) == "f"
    reassembled = "".join(
        _label(slot.alternatives, p) for slot, p in zip(slots, positions, strict=True)
    )
    assert reassembled == word


def test_rhyme_endings_are_all_curated_and_clean() -> None:
    """Every offered ending is one this project chose to show on camera for
    its yield, and every word its sweep can produce is both real and passes
    `fit_for_stage` — the actual safety property, not the shape of the
    ending, which `rhyme_sweep` guarantees regardless of what the list
    contains and so proves nothing about cleanliness on its own."""
    for ending in stage.RHYME_ENDINGS:
        sweep = stage.rhyme_sweep(ending)
        hits = [word for word in sweep.words if word]
        assert hits, ending.label
        for word in hits:
            assert stage.german_pack().is_word(word) is True
            assert stage.fit_for_stage(word) is True, word
            assert word.casefold().endswith(
                (ending.mittelbuchstabe + ending.endbuchstabe + ending.nachsylbe).casefold()
            )


def test_the_acken_sweep_no_longer_puts_kacken_on_screen() -> None:
    """The exact regression a review caught by hand, pinned against the
    real sweep rather than only the predicate in isolation."""
    ending = stage.rhyme_ending("-acken")
    assert ending is not None
    hits = [word for word in stage.rhyme_sweep(ending).words if word]
    assert "Kacken" not in hits
    assert "Backen" in hits  # the filter did not overreach into the rest of the list


def test_rhyme_sweep_yields_match_the_measured_counts() -> None:
    """The report's own headline numbers, pinned against the shipped lexicon
    once `fit_for_stage` has run: -acken 23 (24 minus "Kacken"), -ecken 23,
    -allen 17."""
    expected = {"-acken": 23, "-ecken": 23, "-allen": 17}
    for label, count in expected.items():
        ending = stage.rhyme_ending(label)
        assert ending is not None
        hits = [word for word in stage.rhyme_sweep(ending).words if word]
        assert len(hits) == count


def test_the_rhyme_route_sweeps_a_locked_ending() -> None:
    response = client.post("/stage/denckring/rhyme", data={"ending": "-acken"})
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert "23 of 60 real — -acken" in normalised
    assert "Backen" in normalised
    assert "Kacken" not in normalised

    # The three locked rings' true positions travel on the fragment as
    # plain indices — never text a client would have to relocate on a ring
    # itself — and match `rhyme_sweep`'s own numbers exactly.
    ending = stage.rhyme_ending("-acken")
    assert ending is not None
    sweep = stage.rhyme_sweep(ending)
    assert f'data-mittelbuchstabe-index="{sweep.mittelbuchstabe_index}"' in response.text
    assert f'data-endbuchstabe-index="{sweep.endbuchstabe_index}"' in response.text
    assert f'data-nachsylbe-index="{sweep.nachsylbe_index}"' in response.text


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


def test_default_lang_follows_the_corpus_styles_suggestion() -> None:
    """The one fact the toggle's own default rests on — Jean Paul's excerpts
    suggest German, anything else suggests English, exactly like
    `register_for` but as a language rather than a look."""
    assert stage.default_lang("jean_paul") == "de"
    assert stage.default_lang("modern") == "en"
    assert stage.default_lang("anything-else") == "en"


def _stub_one_corpus(monkeypatch: pytest.MonkeyPatch, style: str) -> None:
    """A corpus that never touches disk: `stage.corpus_choices` and
    `corpora.load` are stubbed directly, so the language toggle can be pinned
    against `bench.generate` without a real corpus file on disk — the corpus
    reading itself is already covered by the tests above."""
    monkeypatch.setattr(
        stage,
        "corpus_choices",
        lambda: [
            stage.CorpusChoice(
                path="x",
                name="stub",
                entries=3,
                style=style,
                register="modern",
                lang=stage.default_lang(style),
            )
        ],
    )
    monkeypatch.setattr(corpora, "load", lambda path: ("stub corpus text", ""))


def test_the_language_toggle_reaches_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    """The toggle's whole job: a German throw and an English throw must differ
    in the `lang` `bench.generate` (and so `apply`) is called with. Pinned
    against a stubbed corpus, since this is a claim about the toggle wiring,
    not about drawing a real throw."""
    _stub_one_corpus(monkeypatch, "modern")
    seen: list[str] = []

    def fake_generate(
        procedure_id: str, text: str, lang: str, params: dict[str, object]
    ) -> tuple[str, str]:
        seen.append(lang)
        return "a line\n", ""

    monkeypatch.setattr(bench, "generate", fake_generate)
    client.post("/stage/ideenwuerfeln/act", data={"corpus_path": "x", "lang": "de"})
    client.post("/stage/ideenwuerfeln/act", data={"corpus_path": "x", "lang": "en"})
    assert seen == ["de", "en"]


def test_the_language_defaults_to_the_corpus_style_and_the_toggle_can_override_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No `lang` field at all — never sent by the picker itself, which always
    submits one of its two options, but exactly what a bare POST like the
    corpus-absent test already sends — falls back to what the chosen corpus's
    `style` suggests. An explicit `lang` overrides that default outright,
    even when it disagrees with the corpus's own suggestion: a German toggle
    over an English corpus is legitimate and must not be second-guessed."""
    _stub_one_corpus(monkeypatch, "jean_paul")
    seen: list[str] = []

    def fake_generate(
        procedure_id: str, text: str, lang: str, params: dict[str, object]
    ) -> tuple[str, str]:
        seen.append(lang)
        return "a line\n", ""

    monkeypatch.setattr(bench, "generate", fake_generate)
    client.post("/stage/ideenwuerfeln/act", data={"corpus_path": "x"})
    client.post("/stage/ideenwuerfeln/act", data={"corpus_path": "x", "lang": "en"})
    assert seen == ["de", "en"]


def test_the_stage_pre_selects_the_toggle_from_the_first_corpuss_style(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """First paint has no submitted toggle yet to read — the option the page
    pre-selects is what carries the corpus's own suggestion until a reader
    changes it."""
    _write_corpus(tmp_path, [{"text": "excerpt", "domain": "Alpha"}])
    monkeypatch.setenv("DENCKRING_CORPORA", str(tmp_path))
    response = client.get("/stage/ideenwuerfeln")
    assert response.status_code == 200
    # The fixture corpus carries style "modern" (see `_write_corpus`), which
    # suggests English — its option should be the one marked selected.
    assert '<option value="en" selected>English</option>' in response.text
    assert '<option value="de" >German</option>' in response.text
    # And the corpus option carries that same suggestion as `data-lang`, so
    # the shared sync script reads `default_lang`'s answer rather than
    # re-running its rule in JavaScript, which is what it used to do.
    assert 'data-lang="en"' in response.text
    _assert_sync_wiring(response.text, [("lang-select", "lang")])


def test_the_stage_offers_the_first_corpuss_headwords_at_first_paint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The picker beside the corpus selector is populated from whichever
    corpus loads first — the same corpus the pre-selected toggle option above
    it names, per `test_the_stage_pre_selects_the_toggle_from_the_first_corpuss_style`."""
    _write_corpus(
        tmp_path,
        [
            {"text": "excerpt one", "domain": "Alpha", "headwords": ["Licht"]},
            {"text": "excerpt two", "domain": "Beta", "headwords": ["Schatten"]},
        ],
    )
    monkeypatch.setenv("DENCKRING_CORPORA", str(tmp_path))
    response = client.get("/stage/ideenwuerfeln")
    assert response.status_code == 200
    assert '<option value="Licht">' in response.text
    assert '<option value="Schatten">' in response.text


def test_the_headword_field_route_follows_whichever_corpus_is_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Switching the corpus select reloads the headword picker from the corpus
    that was actually named — never the previous corpus's own list left over,
    which is exactly the stale-state failure mode the brief warns this scene
    has a history of."""
    first = _write_corpus(
        tmp_path, [{"text": "excerpt one", "domain": "Alpha", "headwords": ["Licht"]}]
    )
    second_dir = tmp_path / "second"
    second_dir.mkdir()
    second = _write_corpus(
        second_dir, [{"text": "excerpt two", "domain": "Beta", "headwords": ["Schatten"]}]
    )
    monkeypatch.setenv("DENCKRING_CORPORA", str(tmp_path))

    first_response = client.get(
        "/stage/ideenwuerfeln/headword-field", params={"corpus_path": str(first)}
    )
    assert first_response.status_code == 200
    assert '<option value="Licht">' in first_response.text
    assert "Schatten" not in first_response.text

    second_response = client.get(
        "/stage/ideenwuerfeln/headword-field", params={"corpus_path": str(second)}
    )
    assert second_response.status_code == 200
    assert '<option value="Schatten">' in second_response.text
    assert "Licht" not in second_response.text


def test_a_hand_typed_headword_absent_from_the_index_still_throws(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The picker offers a list; it must never become the only way in. A
    headword that is not one of the corpus's own entries — the free-text case
    a plain `<select>` would have refused outright — still reaches `apply`
    and still produces a throw."""
    corpus_path = _write_corpus(
        tmp_path,
        [
            {"text": "excerpt alpha", "domain": "Alpha"},
            {"text": "excerpt beta", "domain": "Beta"},
            {"text": "excerpt gamma", "domain": "Gamma"},
        ],
    )
    monkeypatch.setenv("DENCKRING_CORPORA", str(tmp_path))
    response = client.post(
        "/stage/ideenwuerfeln/act",
        data={"corpus_path": str(corpus_path), "headword": "not-in-the-index"},
    )
    assert response.status_code == 200
    for domain in ("Alpha", "Beta", "Gamma"):
        assert domain in response.text


def test_the_witz_form_carries_the_throws_own_language(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Witz reading has to be asked for in the same language the throw
    itself used, not whatever the toggle happens to show after a corpus swap
    — the hidden `lang` field on the witz-form is what carries that forward."""
    corpus_path = _write_corpus(
        tmp_path,
        [
            {"text": "excerpt alpha", "domain": "Alpha", "headwords": ["word"]},
            {"text": "excerpt beta", "domain": "Beta", "headwords": ["word"]},
            {"text": "excerpt gamma", "domain": "Gamma", "headwords": ["word"]},
        ],
    )
    monkeypatch.setenv("DENCKRING_CORPORA", str(tmp_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-a-real-one")
    response = client.post(
        "/stage/ideenwuerfeln/act",
        data={"corpus_path": str(corpus_path), "headword": "word", "lang": "de"},
    )
    assert response.status_code == 200
    assert '<input type="hidden" name="lang" value="de">' in response.text


def test_reduced_motion_settles_slips_instead_of_stranding_them() -> None:
    """`explorer.css`'s blanket `prefers-reduced-motion` rule kills every
    animation, which would otherwise strand a `.slip` at its pre-animation
    `opacity: 0` forever. Read the actual CSS rather than trusting the
    keyframe alone — a reduced-motion viewer never runs the keyframe to find
    out whether something restores the settled state, and the settled state
    has to include the slip's own resting angle, not just visibility, or
    "already settled" would be a lie under reduced motion specifically."""
    css_path = Path(__file__).parent.parent / "src" / "explorer" / "static" / "stage.css"
    normalised = " ".join(css_path.read_text(encoding="utf-8").split())
    assert (
        "@media (prefers-reduced-motion: reduce) { .slip { opacity: 1; "
        "transform: translateY(0) rotate(var(--rot)); } }"
    ) in normalised


# ── scene three: N+7 ────────────────────────────────────────────────────────


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


def test_the_n_plus_7_scene_offers_a_language_toggle_defaulting_to_english() -> None:
    """`stage.N_PLUS_7_DEFAULT_LANG` is what the toggle pre-selects at first paint —
    the brief's own instruction, not a corpus-style guess the way Ideenwürfeln's is."""
    assert stage.N_PLUS_7_DEFAULT_LANG == "en"
    response = client.get("/stage/n_plus_7")
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert '<option value="en" data-example="the cat sat on the table" selected>' in normalised
    assert 'data-example="die Katze saß auf dem Tisch" >German</option>' in normalised


def test_a_german_source_displaces_through_the_german_list() -> None:
    """The toggle genuinely changes the output here, unlike Ideenwürfeln's own: German
    walks its own noun list, not the English one read in a different voice."""
    from denckring import check
    from denckring.procedures.n_plus_7 import displace

    source = "die Katze saß auf dem Tisch"
    produced = displace(source, stage.pack("de"), 7)
    assert produced == "die Katzenbesitzerin saß auf dem Tischbürste"
    assert check("n_plus_7", produced, source=source, lang="de").satisfied is True

    response = client.post("/stage/n_plus_7/act", data={"source": source, "lang": "de"})
    assert response.status_code == 200
    assert "Katzenbesitzerin" in response.text
    assert "Tischbürste" in response.text
    assert "verdict yes" in response.text
    # The catafalque story is English's own — a German reel must never carry it.
    assert "catacomb" not in response.text
    assert "catafalque" not in response.text


def test_the_german_reel_shows_the_words_a_noun_travels_past() -> None:
    """Pinned against the shipped German lexicon: `Katze` sits at index 79197 and
    lands on `Katzenbesitzerin`, eight entries inclusive — the same shape
    `test_the_scene_shows_the_words_a_noun_travels_past` pins for English."""
    steps = stage.displacement("die Katze saß auf dem Tisch", 7, lang="de")
    katze = next(step for step in steps if step.word == "Katze")
    assert katze.replacement == "Katzenbesitzerin"
    assert len(katze.neighbours) == 8
    assert katze.neighbours[0] == "Katze" and katze.neighbours[-1] == "Katzenbesitzerin"


def test_an_unrecognised_lang_falls_back_to_english() -> None:
    """A hand-made request with a `lang` the picker never offers narrows to English
    (`bench.as_lang`'s own rule) rather than raising `UnknownLanguage` at the route."""
    response = client.post(
        "/stage/n_plus_7/act", data={"source": "the cat sat on the table", "lang": "xx"}
    )
    assert response.status_code == 200
    assert "catacomb" in response.text


# ── scene four: Cent mille milliards de poèmes ──────────────────────────────

#: (line A, line B), 1-indexed as the brief itself states the scheme — ABAB
#: CDCD EFEF GG — converted to 0-indexed pairs at the point of use.
_RHYME_PAIRS = [(1, 3), (2, 4), (5, 7), (6, 8), (9, 11), (10, 12), (13, 14)]


def _line_rhyme(line: str, pack: LanguagePack) -> tuple[str, frozenset[str], bool]:
    """A single line's own final word, and the rhyme keys the library's
    pronouncing dictionary gives it — `denckring.core.prosody.rhyme_keys`,
    the same lookup `scheme_violations` checks a rhyme scheme with, not a
    second, ad hoc reading of spelling.

    An earlier version of this test compared final letters directly, on the
    brief's own instruction that "the strips are built so the final words
    themselves rhyme". That instruction was wrong about one pair: "trite"
    was written next to "sight" and "right", and true rhymes though they
    are, "trite" shares not one literal trailing letter with them. The
    orthographic workaround that let a literal test pass anyway — strip a
    trailing silent "e", drop the silent "gh" digraph — was itself unsafe:
    it collapses vowel length along with the silent letters, so "page"
    (`EY1 JH`) and "rag" (`AE1 G`) both reduce to "-ag" and would wrongly
    "match" under it, though they do not rhyme. The pronouncing dictionary
    gets both cases right without any spelling surgery: `light`, `bright`,
    `sight`, `trite`, `tonight` and `right` all key to `AY1 T`, and `page`
    keys to `EY1 JH` alone."""
    from denckring.core import prosody

    (result,) = prosody.rhyme_keys(line, pack)
    _, word, keys, exact = result
    assert exact, f"{word!r} is not in the pronouncing dictionary — fix the strip, not this test"
    return word, keys, exact


def _lines_rhyme(line_a: str, line_b: str, pack: LanguagePack) -> bool:
    """Whether two lines' own final words share a pronunciation, per the
    library's own rhyme-key lookup — see `_line_rhyme`."""
    _, keys_a, _ = _line_rhyme(line_a, pack)
    _, keys_b, _ = _line_rhyme(line_b, pack)
    return bool(keys_a & keys_b)


def test_the_scene_lists_a_real_procedure() -> None:
    scene = stage.scene("cent_mille_milliards")
    assert scene.procedure_id == "cent_mille_milliards"


def test_the_strips_are_fourteen_positions_of_three() -> None:
    """The shape the brief promises: fourteen positions, three alternatives
    each, so 3**14 poems — read from the shipped file, not asserted against
    a hard-coded 14."""
    offered = stage.queneau_offered()
    assert len(offered) == 14
    assert all(len(options) == 3 for options in offered)


def test_the_count_is_computed_from_what_actually_loaded() -> None:
    """The page's one number needs no argument because it is arithmetic, not
    a claim — pinned here against both the brief's own figure and a fresh
    product over whatever `queneau_offered` actually returns, so a strip
    added or removed could not leave a stale count on screen."""
    offered = stage.queneau_offered()
    assert stage.queneau_combinations() == math.prod(len(options) for options in offered)
    assert stage.queneau_combinations() == 4_782_969


def test_first_paint_reads_the_first_alternative_at_every_position() -> None:
    """Deterministic, the way Denckring's own rings start every disc at index
    0 — so first paint is the same poem on every load, not a draw a test
    would have to pin against randomness."""
    state = stage.queneau_initial_state()
    assert state == [0] * 14
    poem = stage.queneau_poem(state)
    offered = stage.queneau_offered()
    assert poem.lines == [options[0] for options in offered]


def test_first_paints_poem_satisfies_the_checker() -> None:
    from denckring import check

    poem = stage.queneau_poem(stage.queneau_initial_state())
    report = check("cent_mille_milliards", poem.text, source=stage.queneau_source())
    assert report.satisfied is True


def test_every_line_a_deal_shows_is_one_its_position_actually_offers() -> None:
    """Asserted against `queneau_offered()` itself, not a second, copied-out
    transcription of the strips — the two could otherwise drift apart and
    this test would never notice."""

    offered = stage.queneau_offered()
    for seed in range(20):
        state = stage.queneau_deal(random.Random(seed))
        poem = stage.queneau_poem(state)
        for line, options in zip(poem.lines, offered, strict=True):
            assert line in options


def test_a_deal_satisfies_the_checker() -> None:

    from denckring import check

    for seed in range(10):
        state = stage.queneau_deal(random.Random(seed))
        poem = stage.queneau_poem(state)
        report = check("cent_mille_milliards", poem.text, source=stage.queneau_source())
        assert report.satisfied is True, poem.text


def test_a_flip_changes_only_the_position_it_touched() -> None:
    """The scene's whole claim: flip one strip, and the other thirteen hold."""

    offered = stage.queneau_offered()
    for seed in range(20):
        rng = random.Random(seed)
        before = stage.queneau_deal(rng)
        position = rng.randrange(len(offered))
        after = stage.queneau_flip(before, position, rng)
        for i in range(len(offered)):
            if i == position:
                assert after[i] != before[i]
                assert offered[i][after[i]] in offered[i]
            else:
                assert after[i] == before[i]


def test_a_flip_can_still_land_on_every_alternative_but_the_current_one() -> None:
    """`queneau_flip` excludes the index already showing — a flip that
    redrew the same line would look, on camera, like nothing happened."""

    state = [0] * 14
    seen = {stage.queneau_flip(state, 0, random.Random(i))[0] for i in range(30)}
    assert seen == {1, 2}


def test_a_flipped_poem_satisfies_the_checker() -> None:

    from denckring import check

    rng = random.Random(1)
    state = stage.queneau_deal(rng)
    state = stage.queneau_flip(state, 3, rng)
    poem = stage.queneau_poem(state)
    report = check("cent_mille_milliards", poem.text, source=stage.queneau_source())
    assert report.satisfied is True


def test_state_text_round_trips() -> None:
    state = [0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1]
    text = stage.queneau_state_to_text(state)
    assert stage.queneau_state_from_text(text) == state


def test_state_from_text_refuses_the_wrong_shape() -> None:
    """A hand-crafted or stale post — never one this page's own markup would
    send — must not be trusted at face value."""
    assert stage.queneau_state_from_text("0,1,2") is None  # too short
    assert stage.queneau_state_from_text("0,1,2,3,4,5,6,7,8,9,10,11,12,13") is None  # 3 not valid
    assert stage.queneau_state_from_text("a,b,c,d,e,f,g,h,i,j,k,l,m,n") is None  # not integers


def test_the_rhyme_scheme_survives_random_draws() -> None:
    """The brief's own property: for a handful of random draws, each pair the
    ABAB CDCD EFEF GG scheme names ends on the same rhyme — verified against
    the library's own pronouncing dictionary, not spelling. See `_line_rhyme`
    for why a literal comparison is not safe here."""
    pack = stage.pack("en")
    for seed in range(15):
        state = stage.queneau_deal(random.Random(seed))
        poem = stage.queneau_poem(state)
        lines = poem.lines
        for line_a, line_b in _RHYME_PAIRS:
            assert _lines_rhyme(lines[line_a - 1], lines[line_b - 1], pack), (
                line_a,
                line_b,
                lines[line_a - 1],
                lines[line_b - 1],
            )


def test_the_rhyme_pairing_holds_for_every_combination_of_alternatives() -> None:
    """Not just a sample of draws: every one of the three alternatives at one
    end of a pair shares a pronounced rhyme, per the pronouncing dictionary,
    with every one of the three at the other end — the actual guarantee the
    brief asks a viewer to be able to trust regardless of which two strips a
    flip happens to land on together."""
    pack = stage.pack("en")
    offered = stage.queneau_offered()
    for line_a, line_b in _RHYME_PAIRS:
        for option_a in offered[line_a - 1]:
            for option_b in offered[line_b - 1]:
                assert _lines_rhyme(option_a, option_b, pack), (line_a, line_b, option_a, option_b)


def test_no_deal_can_rhyme_a_word_with_itself() -> None:
    """A pair the scheme names must rhyme, and `rhyme_keys` is satisfied by a
    word rhymed with itself — so the pairing test above passed while positions
    5 and 7 could both deal "again", 6 and 8 both "before" or "more", 9 and 11
    both "spell" or "tell", and 10 and 12 both "day". Four of the seven pairs.
    An identical rhyme is weak in English practice and a viewer can deal one,
    so this pins the property the other test cannot see: across a pair, no
    alternative ends on the word any alternative at the other end ends on.

    Compared on the final word `rhyme_keys` itself reports, not on the raw
    line, so punctuation and capitalisation cannot make two identical words
    look distinct."""
    pack = stage.pack("en")
    offered = stage.queneau_offered()
    for line_a, line_b in _RHYME_PAIRS:
        words_a = {_line_rhyme(option, pack)[0] for option in offered[line_a - 1]}
        words_b = {_line_rhyme(option, pack)[0] for option in offered[line_b - 1]}
        assert not (words_a & words_b), (line_a, line_b, sorted(words_a & words_b))


def test_the_scene_renders_the_first_paint_poem_and_its_verdict() -> None:
    response = client.get("/stage/cent_mille_milliards")
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert "The paper discs are turning in the light." in normalised
    assert "checked — every line is one of the three these strips offer" in normalised
    assert "4,782,969" in normalised


def test_the_scene_credits_the_strips_to_this_project_not_queneau() -> None:
    """The exact wording the golden fixture uses for the same situation
    (`src/denckring/eval/fixtures/golden/cent_mille_milliards.yaml`)."""
    response = client.get("/stage/cent_mille_milliards")
    assert "the machine is Queneau" not in response.text  # not the fixture's own sentence case
    normalised = " ".join(response.text.split())
    assert "The machine is Queneau's, the strips are not" in normalised


def test_the_deal_route_redraws_the_whole_poem_and_it_still_checks() -> None:
    response = client.post("/stage/cent_mille_milliards/deal")
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert "checked — every line is one of the three these strips offer" in normalised
    offered = stage.queneau_offered()
    import re

    state_match = re.search(r'name="state" value="([\d,]+)"', response.text)
    assert state_match is not None
    state = [int(part) for part in state_match.group(1).split(",")]
    assert len(state) == 14
    for line, options in zip([offered[i][state[i]] for i in range(14)], offered, strict=True):
        assert line in options


def test_the_flip_route_changes_only_the_posted_position() -> None:
    initial_state = stage.queneau_state_to_text(stage.queneau_initial_state())
    response = client.post(
        "/stage/cent_mille_milliards/flip", data={"state": initial_state, "position": "2"}
    )
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert 'id="strip-2"' in normalised
    assert 'id="strip-1"' not in normalised  # only the touched strip comes back
    offered = stage.queneau_offered()
    assert offered[2][0] not in normalised  # the line that was showing is gone
    assert any(alt in normalised for alt in offered[2][1:])
    assert "checked — every line is one of the three these strips offer" in normalised


def test_the_flip_route_falls_back_to_first_paint_on_a_malformed_state() -> None:
    """A request this page's own markup would never send — handled rather
    than trusted at face value or allowed to 500."""
    response = client.post(
        "/stage/cent_mille_milliards/flip", data={"state": "not,a,real,state", "position": "0"}
    )
    assert response.status_code == 200
    assert 'id="strip-0"' in response.text


def test_the_flip_route_clamps_a_position_outside_the_strips() -> None:
    initial_state = stage.queneau_state_to_text(stage.queneau_initial_state())
    response = client.post(
        "/stage/cent_mille_milliards/flip",
        data={"state": initial_state, "position": "99"},
    )
    assert response.status_code == 200
    assert 'id="strip-0"' in response.text


def test_reduced_motion_states_the_settled_strip_line_explicitly() -> None:
    """Unlike `.slip`, `.strip-line`'s own base rule sets no static `opacity`
    or `transform` outside its `animation` shorthand — so explorer.css's
    blanket `animation: none !important` under this preference already
    leaves it at the browser's own defaults (opacity 1, no transform) with
    nothing to strand it; this rule is belt-and-braces, not load-bearing,
    for this element (see the comment above it in stage.css). Pinned here
    anyway, because the rule states plainly what the settled state is meant
    to be, and a future change that gives `.strip-line` a static
    pre-animation style must not silently start relying on this having
    always been correct by coincidence."""
    css_path = Path(__file__).parent.parent / "src" / "explorer" / "static" / "stage.css"
    normalised = " ".join(css_path.read_text(encoding="utf-8").split())
    assert (
        "@media (prefers-reduced-motion: reduce) { .strip-line { opacity: 1; transform: none; } }"
    ) in normalised


# ── scene five: word ladder ──────────────────────────────────────────────────


def test_the_english_ladder_satisfies_the_checker() -> None:
    """The scene's whole claim, in the language the toggle starts on: what
    `apply` finds is a real word_ladder step from start to target."""
    from denckring import check

    result = stage.word_ladder("cold", "warm", "en")
    assert result.problem == ""
    assert check("word_ladder", result.text, lang="en").satisfied is True


def test_the_german_ladder_satisfies_the_checker() -> None:
    """The pair worth showing beside the English one: the same destination,
    reached through a different lexicon."""
    from denckring import check

    result = stage.word_ladder("kalt", "warm", "de")
    assert result.problem == ""
    assert check("word_ladder", result.text, lang="de").satisfied is True


def test_every_rung_is_a_real_word_and_differs_from_its_predecessor_by_one_letter() -> None:
    """Asserted against the pack itself, not a copy of the ladder this project
    happens to expect — the same discipline
    `test_every_line_a_deal_shows_is_one_its_position_actually_offers` already
    holds the Queneau strips to."""
    from denckring.lang import get_pack

    for lang, (start, target) in stage.WORD_LADDER_EXAMPLES.items():
        result = stage.word_ladder(start, target, lang)
        assert result.problem == ""
        pack = get_pack(lang)
        for rung in result.rungs:
            assert pack.is_word(rung.word), (lang, rung.word)
        for previous, current in pairwise(result.rungs):
            differences = sum(1 for a, b in zip(previous.word, current.word, strict=True) if a != b)
            assert differences == 1, (lang, previous.word, current.word)


def test_the_english_ladder_marks_the_letter_that_actually_changed() -> None:
    """Pinned against the position itself, not merely that some tile is
    marked — a marked letter that was not the one substituted would be
    exactly wrong for a scene whose whole explanatory burden is this mark."""
    result = stage.word_ladder("cold", "warm", "en")
    assert [rung.word for rung in result.rungs] == ["cold", "wold", "wald", "ward", "warm"]
    assert [rung.changed for rung in result.rungs] == [None, 0, 1, 2, 3]


def test_the_german_ladder_marks_the_letter_that_actually_changed() -> None:
    result = stage.word_ladder("kalt", "warm", "de")
    assert [rung.word for rung in result.rungs] == ["kalt", "kart", "wart", "warm"]
    assert [rung.changed for rung in result.rungs] == [None, 2, 0, 3]


def test_a_pair_with_no_connecting_ladder_says_so_distinctly() -> None:
    """Both endpoints are real words the lexicon knows; the search itself
    found no path within its own bounds — a true and interesting answer, not
    an error (see the brief)."""
    result = stage.word_ladder("crime", "sound", "en")
    assert result.problem == "no_ladder"
    assert result.rungs == []
    assert "no ladder" in result.message


def test_a_word_the_lexicon_does_not_know_says_so_distinctly() -> None:
    """The search is never even run here — a different, more basic failure
    than a search that ran and found nothing, and the message must say so."""
    result = stage.word_ladder("zzzz", "warm", "en")
    assert result.problem == "unknown_word"
    assert result.rungs == []
    assert "lexicon does not have" in result.message


def test_a_pair_the_search_cannot_even_be_asked_about_says_why() -> None:
    """The third refusal, and the only one reachable by typing into the
    scene's own two fields without hitting the lexicon at all: two words of
    different lengths, an empty field, or anything that is not letters. The
    search is never run — `apply` would raise `InvalidParams` on it — so the
    scene answers with the rule instead of a failure, and does not dress the
    three refusals up as one."""
    for start, target in (("cold", "warmth"), ("", "warm"), ("co1d", "warm")):
        result = stage.word_ladder(start, target, "en")
        assert result.problem == "invalid", (start, target)
        assert result.rungs == []
        assert result.message == "both words must be the same length, letters only."


def test_the_invalid_pair_case_renders_without_raising() -> None:
    """Trivially reachable from the scene's own typed fields, so the fragment
    that renders it is exercised too, not just the function behind it."""
    response = client.post(
        "/stage/word_ladder/act", data={"start": "cold", "target": "warmth", "lang": "en"}
    )
    assert response.status_code == 200
    assert "both words must be the same length, letters only." in response.text
    assert "verdict" not in response.text


def test_the_two_failure_modes_are_never_the_same_sentence() -> None:
    unknown = stage.word_ladder("zzzz", "warm", "en")
    no_ladder = stage.word_ladder("crime", "sound", "en")
    assert unknown.problem != no_ladder.problem
    assert unknown.message != no_ladder.message


def test_the_word_ladder_scene_renders_a_real_ladder_and_its_verdict() -> None:
    response = client.get("/stage/word_ladder")
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert "checked — a real ladder from start to target" in normalised
    assert 'class="tile changed"' in normalised


def test_the_word_ladder_route_finds_a_german_ladder() -> None:
    """The toggle genuinely changes the search, the way N+7's own does: a
    German request must not silently fall back to the English lexicon."""
    response = client.post(
        "/stage/word_ladder/act", data={"start": "kalt", "target": "warm", "lang": "de"}
    )
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert "checked — a real ladder from start to target" in normalised


def test_the_no_ladder_case_renders_without_raising() -> None:
    response = client.post(
        "/stage/word_ladder/act", data={"start": "crime", "target": "sound", "lang": "en"}
    )
    assert response.status_code == 200
    assert "no ladder from" in response.text
    assert "verdict" not in response.text


def test_the_unknown_word_case_renders_without_raising() -> None:
    response = client.post(
        "/stage/word_ladder/act", data={"start": "zzzz", "target": "warm", "lang": "en"}
    )
    assert response.status_code == 200
    assert "lexicon does not have" in response.text
    assert "verdict" not in response.text


def test_the_scene_offers_a_language_toggle_defaulting_to_english() -> None:
    assert stage.WORD_LADDER_DEFAULT_LANG == "en"
    response = client.get("/stage/word_ladder")
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert '<option value="en" data-start="cold" data-target="warm" selected>' in normalised
    assert 'data-start="kalt" data-target="warm" >German</option>' in normalised


def test_reduced_motion_settles_rungs_instead_of_stranding_them() -> None:
    """The same fix `.slip` and `.strip-line` need, for the same reason:
    `explorer.css`'s blanket `prefers-reduced-motion` rule kills every
    animation, which would otherwise strand a `.rung` at its pre-animation
    `opacity: 0, translateY(-14px)` forever. Read the actual CSS rather than
    trusting the keyframe alone."""
    css_path = Path(__file__).parent.parent / "src" / "explorer" / "static" / "stage.css"
    normalised = " ".join(css_path.read_text(encoding="utf-8").split())
    assert (
        "@media (prefers-reduced-motion: reduce) { .rung { opacity: 1; transform: none; } }"
    ) in normalised


# ── scene six: haikuization ──────────────────────────────────────────────────


def test_the_default_source_reduces_to_its_own_line_ends() -> None:
    """Assert against the source's own lines, not a hardcoded string — the
    remnant has to be exactly each line's last word, in order, whatever the
    shipped source happens to say, not merely what it says today."""
    from denckring.core.text import line_spans as _line_spans
    from denckring.core.text import word_spans as _word_spans
    from denckring.lang import get_pack

    pack = get_pack("en")
    expected = [
        _word_spans(line, pack)[-1][1] for _, line in _line_spans(stage.HAIKUIZATION_SOURCE)
    ]
    haiku = stage.haikuize(stage.HAIKUIZATION_SOURCE, lang="en")
    assert haiku.remnant == " ".join(expected)


def test_the_default_remnant_is_the_one_the_brief_verified() -> None:
    """Pinned as a second, independent assertion on top of the line-ends check
    above — this is the exact remnant the brief verified before this scene was
    built, and it reads as a sentence as well as a poem."""
    haiku = stage.haikuize(stage.HAIKUIZATION_SOURCE, lang="en")
    assert haiku.remnant == "paper turns word stands language sheet"


def test_the_default_remnant_satisfies_the_checker() -> None:
    from denckring import check

    haiku = stage.haikuize(stage.HAIKUIZATION_SOURCE, lang="en")
    report = check("haikuization", haiku.remnant, lang="en", source=stage.HAIKUIZATION_SOURCE)
    assert report.satisfied is True


def test_the_scene_renders_the_default_source_and_its_verdict() -> None:
    response = client.get("/stage/haikuization")
    assert response.status_code == 200
    assert "paper turns word stands language sheet" in response.text
    assert "checked — every word above ends its own line" in response.text


def test_first_paint_settles_the_scene_and_the_button_plays_it() -> None:
    """ "Scenes do not autoplay. The recording is a person using the thing" —
    and this was the one scene of six whose whole demonstration, the dissolve
    and the remnant's entrance both, ran on load with nobody touching it, so a
    recorder who started capture after the page loaded had missed the shot.
    First paint marks itself `settled`, which cancels both animations; the
    action's own response carries no such mark and plays them."""
    first_paint = client.get("/stage/haikuization")
    assert first_paint.status_code == 200
    assert 'class="haiku-source settled"' in first_paint.text
    assert 'class="haiku-remnant settled"' in first_paint.text

    played = client.post("/stage/haikuization/act", data={"source": stage.HAIKUIZATION_SOURCE})
    assert played.status_code == 200
    assert 'class="haiku-source"' in played.text
    assert 'class="haiku-remnant"' in played.text


def test_the_settled_state_cancels_both_of_the_scenes_animations() -> None:
    """The markup above only names a class; this is the half that makes it do
    something. `.haiku-fade` needs the animation cancelled and nothing else —
    it starts visible and only the animation moves it — while `.haiku-remnant`
    carries a static `opacity: 0` on its base rule and would be left invisible
    by a cancelled animation alone, so its settled values are stated too. Read
    from the stylesheet, the same way the reduced-motion rules are: no test
    here runs a browser."""
    css_path = Path(__file__).parent.parent / "src" / "explorer" / "static" / "stage.css"
    normalised = " ".join(css_path.read_text(encoding="utf-8").split())
    assert ".haiku-source.settled .haiku-fade { animation: none; }" in normalised
    assert (
        ".haiku-remnant.settled { animation: none; opacity: 1; transform: none; }"
    ) in normalised


def test_a_prose_source_reduces_to_one_word_correctly() -> None:
    """Prose has one line, so the reduction is a single word — correct, by the
    procedure's own rule (see the brief's own "prose is a real input"), and
    the checker must agree it is correct rather than merely unsurprising."""
    from denckring import check

    prose = "This is just a plain sentence with no line breaks at all, nothing special."
    haiku = stage.haikuize(prose, lang="en")
    assert haiku.prose is True
    assert haiku.remnant == "special"
    assert check("haikuization", haiku.remnant, lang="en", source=prose).satisfied is True


def test_the_prose_case_renders_its_explanation_not_a_bare_word() -> None:
    """A single word on screen with nothing beside it would look broken; the
    explanation is what makes it read as correct instead (see the brief)."""
    response = client.post(
        "/stage/haikuization/act",
        data={
            "source": "This is just a plain sentence with no line breaks at all, nothing special."
        },
    )
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert "haiku-prose-note" in response.text
    assert "the procedure keeps line ends, and this" in normalised
    assert "checked — every word above ends its own line" in normalised


def test_a_multi_line_source_does_not_carry_the_prose_note() -> None:
    haiku = stage.haikuize(stage.HAIKUIZATION_SOURCE, lang="en")
    assert haiku.prose is False


def test_an_empty_source_does_not_raise() -> None:
    haiku = stage.haikuize("", lang="en")
    assert haiku.lines == []
    assert haiku.remnant == ""
    response = client.post("/stage/haikuization/act", data={"source": ""})
    assert response.status_code == 200
    assert "Nothing to reduce yet" in response.text


def test_a_whitespace_only_source_does_not_raise_either() -> None:
    """`line_spans` counts a blank line as no line at all, so a source of
    pure whitespace has to reach the same empty-box handling a genuinely
    empty field does, rather than the `NoCandidateWord` `apply` itself would
    raise on it."""
    haiku = stage.haikuize("   \n\n  \n", lang="en")
    assert haiku.lines == []
    assert haiku.remnant == ""


def test_every_word_shown_is_marked_word_or_gap_never_both() -> None:
    """The token reconstruction has to cover the whole line with no overlap
    and no gap of its own — otherwise the rendered line would silently drop
    or duplicate a character of the source it claims to show verbatim."""
    from denckring.core.text import line_spans as _line_spans

    haiku = stage.haikuize(stage.HAIKUIZATION_SOURCE, lang="en")
    for line, source_line in zip(
        haiku.lines,
        [text for _, text in _line_spans(stage.HAIKUIZATION_SOURCE)],
        strict=True,
    ):
        assert "".join(token.text for token in line.tokens) == source_line


def test_exactly_one_word_per_line_is_marked_kept() -> None:
    haiku = stage.haikuize(stage.HAIKUIZATION_SOURCE, lang="en")
    for line in haiku.lines:
        kept = [token for token in line.tokens if token.is_word and token.kept]
        assert len(kept) == 1


def test_reduced_motion_settles_the_remnant_instead_of_stranding_it() -> None:
    """`.haiku-remnant` starts hidden (`opacity: 0`) and only its own
    animation ever brings it to `opacity: 1` — the same pattern `.slip`,
    `.strip-line` and `.rung` already need an explicit reduced-motion
    override for, since explorer.css's blanket `animation: none !important`
    would otherwise strand it invisible forever."""
    css_path = Path(__file__).parent.parent / "src" / "explorer" / "static" / "stage.css"
    normalised = " ".join(css_path.read_text(encoding="utf-8").split())
    assert (
        "@media (prefers-reduced-motion: reduce) { .haiku-remnant { opacity: 1; "
        "transform: none; } }"
    ) in normalised
