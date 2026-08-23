"""The stage. Appearance is not tested; the claims underneath it are."""

from __future__ import annotations

import html
import math
import random
import re
from itertools import pairwise
from pathlib import Path

import pytest
from explorer import bench, corpora, stage
from explorer.app import app
from fastapi.testclient import TestClient

from denckring import check as denckring_check
from denckring.core.protocol import Lang, LanguagePack

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
    scene's own version of describing what it did not do."""
    response = client.post("/stage/n_plus_7/act", data={"source": "the dog ran home"})
    assert response.status_code == 200
    assert 'id="n7-reels"' in response.text
    assert 'hx-swap-oob="true"' in response.text
    assert "doggedness" in response.text
    assert "homefolk" in response.text
    assert "catacomb" not in response.text


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
    # English's own reel words must never survive a German displacement.
    assert "catacomb" not in response.text


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


@pytest.mark.parametrize("lang", stage.QUENEAU_SETS)
def test_the_strips_are_fourteen_positions_of_three(lang: Lang) -> None:
    """The shape the brief promises, for every set this scene ships:
    fourteen positions, three alternatives each, so 3**14 poems — read from
    the shipped file, not asserted against a hard-coded 14."""
    offered = stage.queneau_offered(lang)
    assert len(offered) == 14
    assert all(len(options) == 3 for options in offered)


@pytest.mark.parametrize("lang", stage.QUENEAU_SETS)
def test_the_count_is_computed_from_what_actually_loaded(lang: Lang) -> None:
    """The page's one number needs no argument beyond which set it is
    describing, because it is arithmetic, not a claim — pinned here against
    both the brief's own figure and a fresh product over whatever
    `queneau_offered` actually returns for that set, so a strip added or
    removed, in either set, could not leave a stale count on screen."""
    offered = stage.queneau_offered(lang)
    assert stage.queneau_combinations(lang) == math.prod(len(options) for options in offered)
    assert stage.queneau_combinations(lang) == 4_782_969


@pytest.mark.parametrize("lang", stage.QUENEAU_SETS)
def test_first_paint_reads_the_first_alternative_at_every_position(lang: Lang) -> None:
    """Deterministic, the way Denckring's own rings start every disc at index
    0 — so first paint is the same poem on every load, or every switch of
    strip set, rather than a draw a test would have to pin against
    randomness."""
    state = stage.queneau_initial_state(lang)
    assert state == [0] * 14
    poem = stage.queneau_poem(state, lang)
    offered = stage.queneau_offered(lang)
    assert poem.lines == [options[0] for options in offered]


@pytest.mark.parametrize("lang", stage.QUENEAU_SETS)
def test_first_paints_poem_satisfies_the_checker(lang: Lang) -> None:
    from denckring import check

    poem = stage.queneau_poem(stage.queneau_initial_state(lang), lang)
    report = check("cent_mille_milliards", poem.text, lang=lang, source=stage.queneau_source(lang))
    assert report.satisfied is True


@pytest.mark.parametrize("lang", stage.QUENEAU_SETS)
def test_every_line_a_deal_shows_is_one_its_position_actually_offers(lang: Lang) -> None:
    """Asserted against `queneau_offered()` itself, not a second, copied-out
    transcription of the strips — the two could otherwise drift apart and
    this test would never notice. Both sets: the German strips get the same
    discipline the English ones already had."""

    offered = stage.queneau_offered(lang)
    for seed in range(20):
        state = stage.queneau_deal(lang, random.Random(seed))
        poem = stage.queneau_poem(state, lang)
        for line, options in zip(poem.lines, offered, strict=True):
            assert line in options


@pytest.mark.parametrize("lang", stage.QUENEAU_SETS)
def test_a_deal_satisfies_the_checker(lang: Lang) -> None:

    from denckring import check

    for seed in range(10):
        state = stage.queneau_deal(lang, random.Random(seed))
        poem = stage.queneau_poem(state, lang)
        report = check(
            "cent_mille_milliards", poem.text, lang=lang, source=stage.queneau_source(lang)
        )
        assert report.satisfied is True, poem.text


@pytest.mark.parametrize("lang", stage.QUENEAU_SETS)
def test_a_flip_changes_only_the_position_it_touched(lang: Lang) -> None:
    """The scene's whole claim: flip one strip, and the other thirteen hold —
    in whichever set is on screen."""

    offered = stage.queneau_offered(lang)
    for seed in range(20):
        rng = random.Random(seed)
        before = stage.queneau_deal(lang, rng)
        position = rng.randrange(len(offered))
        after = stage.queneau_flip(before, position, lang, rng)
        for i in range(len(offered)):
            if i == position:
                assert after[i] != before[i]
                assert offered[i][after[i]] in offered[i]
            else:
                assert after[i] == before[i]


@pytest.mark.parametrize("lang", stage.QUENEAU_SETS)
def test_a_flip_can_still_land_on_every_alternative_but_the_current_one(lang: Lang) -> None:
    """`queneau_flip` excludes the index already showing — a flip that
    redrew the same line would look, on camera, like nothing happened."""

    state = [0] * 14
    seen = {stage.queneau_flip(state, 0, lang, random.Random(i))[0] for i in range(30)}
    assert seen == {1, 2}


@pytest.mark.parametrize("lang", stage.QUENEAU_SETS)
def test_a_flipped_poem_satisfies_the_checker(lang: Lang) -> None:

    from denckring import check

    rng = random.Random(1)
    state = stage.queneau_deal(lang, rng)
    state = stage.queneau_flip(state, 3, lang, rng)
    poem = stage.queneau_poem(state, lang)
    report = check("cent_mille_milliards", poem.text, lang=lang, source=stage.queneau_source(lang))
    assert report.satisfied is True


def test_state_text_round_trips() -> None:
    state = [0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1]
    text = stage.queneau_state_to_text(state)
    assert stage.queneau_state_from_text(text) == state


@pytest.mark.parametrize("lang", stage.QUENEAU_SETS)
def test_state_from_text_refuses_the_wrong_shape(lang: Lang) -> None:
    """A hand-crafted or stale post — never one this page's own markup would
    send — must not be trusted at face value, against either set's own
    shape."""
    assert stage.queneau_state_from_text("0,1,2", lang) is None  # too short
    assert (
        stage.queneau_state_from_text("0,1,2,3,4,5,6,7,8,9,10,11,12,13", lang) is None
    )  # 3 not valid
    not_integers = "a,b,c,d,e,f,g,h,i,j,k,l,m,n"
    assert stage.queneau_state_from_text(not_integers, lang) is None


def test_queneau_lang_narrows_to_a_set_this_scene_actually_ships() -> None:
    """Whatever a hand-crafted or stale request names, only the two sets the
    picker itself can send come back — the same discipline `bench.as_lang`
    applies for `Lang`'s own three values, narrowed further here because
    this scene has strips behind only two of them."""
    assert stage.queneau_lang("en") == "en"
    assert stage.queneau_lang("de") == "de"
    assert stage.queneau_lang("fr") == "en"  # a real Lang, but no strips ship for it
    assert stage.queneau_lang("") == "en"
    assert stage.queneau_lang("not a language") == "en"


def test_the_rhyme_scheme_survives_random_draws() -> None:
    """The brief's own property, for the English set: for a handful of
    random draws, each pair the ABAB CDCD EFEF GG scheme names ends on the
    same rhyme — verified against the library's own pronouncing dictionary,
    not spelling. See `_line_rhyme` for why a literal comparison is not safe
    even for English. The German set cannot be verified this same way; see
    `test_the_german_pack_ships_no_phonemes_so_rhyme_keys_cannot_run` and
    `test_the_german_rhyme_pairing_holds_by_the_only_check_available` below
    for what runs in its place, and why."""
    pack = stage.pack("en")
    for seed in range(15):
        state = stage.queneau_deal("en", random.Random(seed))
        poem = stage.queneau_poem(state, "en")
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
    flip happens to land on together. English only — see the German tests
    below for why the same exhaustive check cannot run against that pack."""
    pack = stage.pack("en")
    offered = stage.queneau_offered("en")
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
    look distinct. English only, for the same reason as the two tests above."""
    pack = stage.pack("en")
    offered = stage.queneau_offered("en")
    for line_a, line_b in _RHYME_PAIRS:
        words_a = {_line_rhyme(option, pack)[0] for option in offered[line_a - 1]}
        words_b = {_line_rhyme(option, pack)[0] for option in offered[line_b - 1]}
        assert not (words_a & words_b), (line_a, line_b, sorted(words_a & words_b))


def test_the_german_pack_ships_no_phonemes_so_rhyme_keys_cannot_run() -> None:
    """The honest limit the brief itself names: "the German pack ships no
    phonemes". Not taken on faith here — checked. `rhyme_keys` is the exact
    call the three English tests above use; run against the German pack it
    raises `MissingCapability` rather than returning a weaker answer, because
    `word_rhyme_keys` re-raises when the *pack itself* lacks the capability
    (as opposed to a single word the dictionary happens not to carry, which
    it catches and reports as unknown instead).

    Pinned here, rather than left as a comment only, so that if a German
    phonemes pack is ever added, this assertion is the one that fails —
    telling whoever changes it that the weaker, orthographic tests below
    have stopped being the ceiling of what can be verified and should be
    replaced with a real `rhyme_keys` test, the same one English already
    gets, rather than left in place proving less than the pack now allows.
    """
    from denckring.core import prosody
    from denckring.core.errors import MissingCapability

    pack = stage.pack("de")
    with pytest.raises(MissingCapability):
        prosody.rhyme_keys("ein Wort geht", pack)


def _german_rhyme_suffix(line: str, length: int = 3) -> str:
    """The orthographic proxy the brief allows in place of `rhyme_keys` for
    German ("I verified those by suffix and by ear"): the final word's last
    `length` letters, after the two normalisations German spelling needs
    that a bare suffix comparison does not supply on its own —

    - final-obstruent devoicing: a word-final "d", "b" or "g" is pronounced
      "t", "p" or "k" in German, so "Zeit" and "Leid" both end the same
      rhyme (-eit) despite the different final letter — folded here by
      mapping the final letter to its voiceless counterpart;
    - a doubled consonant immediately before the ending, which in German
      spelling marks a short preceding vowel rather than a doubled sound —
      "Ort" and "verdorrt" both end -ort once the doubled "rr" collapses to
      one "r".

    This is spelling, not pronunciation, and is weaker than `rhyme_keys` on
    purpose: it cannot see a rhyme spelled two different ways the way the
    pronouncing dictionary would, or catch a false match spelled the same
    but pronounced differently. It is the strongest check possible without
    phonemes, not a claim to have replaced them — see the test above.
    """
    word = re.findall(r"[^\W\d_]+", line, re.UNICODE)[-1].lower()
    collapsed = re.sub(r"(.)\1", r"\1", word)
    fold = {"d": "t", "b": "p", "g": "k"}
    devoiced = collapsed[:-1] + fold.get(collapsed[-1], collapsed[-1])
    return devoiced[-length:]


def test_the_german_rhyme_pairing_holds_by_the_only_check_available() -> None:
    """Not a phonetic rhyme test — `rhyme_keys` cannot run on this pack at
    all (see the test above). This checks the weaker, orthographic property
    the strips were actually verified by, across every one of the three
    alternatives at each end of every pair the scheme names — the same
    exhaustiveness `test_the_rhyme_pairing_holds_for_every_combination_...`
    gives English, over a weaker property than that test checks."""
    offered = stage.queneau_offered("de")
    for line_a, line_b in _RHYME_PAIRS:
        for option_a in offered[line_a - 1]:
            for option_b in offered[line_b - 1]:
                assert _german_rhyme_suffix(option_a) == _german_rhyme_suffix(option_b), (
                    line_a,
                    line_b,
                    option_a,
                    option_b,
                )


def test_no_german_deal_can_rhyme_a_word_with_itself() -> None:
    """The German counterpart to `test_no_deal_can_rhyme_a_word_with_itself`,
    which could only be written for English because `rhyme_keys` cannot run
    on the German pack at all (see
    `test_the_german_pack_ships_no_phonemes_so_rhyme_keys_cannot_run`).

    The property is the same and does not need phonemes to state: a pair the
    scheme names must rhyme, and `_german_rhyme_suffix` is satisfied by a
    word rhymed with itself, so the exhaustive pairing test above would pass
    while both ends of a pair could deal the same final word. An identical
    rhyme is as weak in German practice as in English, and a viewer can deal
    one — 4,782,969 poems is a lot of chances.

    Compared on the final word `_german_rhyme_suffix` itself extracts, not on
    the raw line, so punctuation and capitalisation cannot make two identical
    words look distinct."""

    def final_word(line: str) -> str:
        words: list[str] = re.findall(r"[^\W\d_]+", line, re.UNICODE)
        return words[-1].lower()

    offered = stage.queneau_offered("de")
    for line_a, line_b in _RHYME_PAIRS:
        words_a = {final_word(option) for option in offered[line_a - 1]}
        words_b = {final_word(option) for option in offered[line_b - 1]}
        assert not (words_a & words_b), (line_a, line_b, sorted(words_a & words_b))


def test_the_scene_renders_the_first_paint_poem_and_its_verdict() -> None:
    response = client.get("/stage/cent_mille_milliards")
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert "The paper discs are turning in the light." in normalised
    assert "checked — every line is one of the three these strips offer" in normalised
    assert "4,782,969" in normalised


def test_the_german_set_first_paints_its_own_poem_and_verdict() -> None:
    """The same first paint, for the set the picker's other option names —
    the count and the verdict following the German strips, not carried over
    from the English default."""
    response = client.get("/stage/cent_mille_milliards", params={"lang": "de"})
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert "Fünf Scheiben aus Papier, und etwas Zeit." in normalised
    assert "checked — every line is one of the three these strips offer" in normalised
    assert "4,782,969" in normalised


def test_the_scene_credits_the_strips_to_this_project_not_queneau() -> None:
    """The exact wording the golden fixture uses for the same situation
    (`src/denckring/eval/fixtures/golden/cent_mille_milliards.yaml`)."""
    response = client.get("/stage/cent_mille_milliards")
    assert "the machine is Queneau" not in response.text  # not the fixture's own sentence case
    normalised = " ".join(response.text.split())
    assert "The machine is Queneau's, the strips are not" in normalised


def test_the_set_picker_offers_both_sets_with_the_current_one_selected() -> None:
    response = client.get("/stage/cent_mille_milliards", params={"lang": "de"})
    selected = re.search(r'value="(en|de)"\s*selected', response.text)
    assert selected is not None
    assert selected.group(1) == "de"
    assert 'value="en"' in response.text
    assert 'value="de"' in response.text


def test_the_set_route_switches_to_the_german_strips() -> None:
    """The picker's own `change` request: a fresh first paint of whichever
    set it now names, not a patch onto the poem already on screen — the
    count and the verdict both following, not just the lines."""
    response = client.get("/stage/cent_mille_milliards/set", params={"lang": "de"})
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert "Fünf Scheiben aus Papier, und etwas Zeit." in normalised
    assert "The paper discs are turning in the light." not in normalised
    assert "4,782,969" in normalised
    assert "checked — every line is one of the three these strips offer" in normalised


def test_the_set_route_falls_back_to_english_for_an_unknown_lang() -> None:
    response = client.get("/stage/cent_mille_milliards/set", params={"lang": "fr"})
    assert response.status_code == 200
    assert "The paper discs are turning in the light." in response.text


def test_the_scene_itself_falls_back_to_english_for_an_unknown_lang() -> None:
    """The `/set` route's own fallback was covered at this level; the scene
    route's was not, though it reads the same `lang` off the query string and
    narrows it the same way. A hand-typed `?lang=xyz` must first-paint the
    English strips rather than raising at the route."""
    response = client.get("/stage/cent_mille_milliards", params={"lang": "xyz"})
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert "The paper discs are turning in the light." in normalised
    assert "Fünf Scheiben aus Papier, und etwas Zeit." not in normalised
    # The picker follows the set that actually painted, never the unknown
    # value that was asked for.
    assert '<option value="en" selected>English</option>' in normalised


def test_the_poem_state_carries_which_set_it_belongs_to() -> None:
    """`#poem-lang` names the set `#poem-state`'s own indices are indices
    into — read back by every flip form's `hx-include`, so a flip can never
    be run against the wrong sheet."""
    response = client.get("/stage/cent_mille_milliards", params={"lang": "de"})
    assert 'id="poem-lang" name="lang" value="de"' in response.text


def test_flip_forms_include_both_the_state_and_the_set_fields() -> None:
    response = client.get("/stage/cent_mille_milliards")
    assert 'hx-include="#poem-state, #poem-lang"' in response.text


def test_the_deal_route_redraws_the_whole_poem_and_it_still_checks() -> None:
    response = client.post("/stage/cent_mille_milliards/deal")
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert "checked — every line is one of the three these strips offer" in normalised
    offered = stage.queneau_offered("en")
    state_match = re.search(r'name="state" value="([\d,]+)"', response.text)
    assert state_match is not None
    state = [int(part) for part in state_match.group(1).split(",")]
    assert len(state) == 14
    for line, options in zip([offered[i][state[i]] for i in range(14)], offered, strict=True):
        assert line in options


def test_the_deal_route_redraws_the_german_poem_and_it_still_checks() -> None:
    response = client.post("/stage/cent_mille_milliards/deal", data={"lang": "de"})
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert "checked — every line is one of the three these strips offer" in normalised
    offered = stage.queneau_offered("de")
    state_match = re.search(r'name="state" value="([\d,]+)"', response.text)
    assert state_match is not None
    state = [int(part) for part in state_match.group(1).split(",")]
    assert len(state) == 14
    for line, options in zip([offered[i][state[i]] for i in range(14)], offered, strict=True):
        assert line in options


def test_the_flip_route_changes_only_the_posted_position() -> None:
    initial_state = stage.queneau_state_to_text(stage.queneau_initial_state("en"))
    response = client.post(
        "/stage/cent_mille_milliards/flip",
        data={"state": initial_state, "position": "2", "lang": "en"},
    )
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert 'id="strip-2"' in normalised
    assert 'id="strip-1"' not in normalised  # only the touched strip comes back
    offered = stage.queneau_offered("en")
    assert offered[2][0] not in normalised  # the line that was showing is gone
    assert any(alt in normalised for alt in offered[2][1:])
    assert "checked — every line is one of the three these strips offer" in normalised


def test_the_flip_route_changes_only_the_posted_position_in_german() -> None:
    initial_state = stage.queneau_state_to_text(stage.queneau_initial_state("de"))
    response = client.post(
        "/stage/cent_mille_milliards/flip",
        data={"state": initial_state, "position": "2", "lang": "de"},
    )
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert 'id="strip-2"' in normalised
    assert 'id="strip-1"' not in normalised
    offered = stage.queneau_offered("de")
    assert offered[2][0] not in normalised
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
    initial_state = stage.queneau_state_to_text(stage.queneau_initial_state("en"))
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


# ── scene six: cut-up ──────────────────────────────────────────────────────


def test_cut_up_is_the_sixth_scene_in_place() -> None:
    """The slot and its position are what the brief pins — replaced in
    place, not appended, and not merely present somewhere in the list. The
    scene it replaced is gone from `SCENES` entirely, and scene seven
    (`llull_figure`, added after cut-up) does not disturb cut-up's own
    position — it is appended, not inserted, and so is scene eight
    (`poesie_automat`) after it. The length is deliberately not pinned: it
    would have to be edited by every round that adds a scene, which makes it a
    line people change without reading rather than a guard."""
    assert stage.SCENES[5].slug == "cut_up"
    assert stage.scene("cut_up").procedure_id == "cut_up"
    assert {scene.slug for scene in stage.SCENES} == {
        "denckring",
        "ideenwuerfeln",
        "n_plus_7",
        "cent_mille_milliards",
        "word_ladder",
        "cut_up",
        "llull_figure",
        "poesie_automat",
    }


def test_the_source_tokenises_to_the_47_words_the_task_report_measured() -> None:
    """Pinned as a belt-and-suspenders check on top of the property test
    below: the exact count the quadrant cut has to conserve, and the count
    the checker reports back as `source_words`."""
    assert len(stage.cut_up_source_words(stage.CUT_UP_SOURCE)) == 47


def test_source_words_matches_word_spans_directly() -> None:
    """The property, not just the pinned count above: `cut_up_source_words`
    has to be exactly what `word_spans` (the same call `cut_up.check` itself
    makes) finds in the source, whatever the source says today."""
    from denckring.core.text import word_spans as _word_spans
    from denckring.lang import get_pack as _get_pack

    expected = [word for _, word in _word_spans(stage.CUT_UP_SOURCE, _get_pack("en"))]
    assert stage.cut_up_source_words(stage.CUT_UP_SOURCE) == expected


def test_source_lines_reproduce_source_words_in_order() -> None:
    """`cut_up_source_lines` tokenises line by line, for the printed page's
    own rendering; `cut_up_source_words` tokenises the whole text in one
    pass, the same call `cut_up.check` itself makes. The page's own
    `source_index` numbering only works if both fall in the same order —
    pinned here rather than assumed."""
    lines = stage.cut_up_source_lines(stage.CUT_UP_SOURCE)
    from_lines = [token.text for line in lines for token in line.tokens if token.is_word]
    assert from_lines == stage.cut_up_source_words(stage.CUT_UP_SOURCE)


def test_source_lines_render_every_character_of_the_source_verbatim() -> None:
    """The token reconstruction has to cover each line with no overlap and no
    gap — otherwise the printed page would silently drop or duplicate a
    character of the source it claims to show exactly as typed, punctuation
    and line breaks included. The blade's own arithmetic reads character
    offsets straight off these spans, so a gap here would move a cut."""
    from denckring.core.text import line_spans as _line_spans

    lines = stage.cut_up_source_lines(stage.CUT_UP_SOURCE)
    originals = [text for _, text in _line_spans(stage.CUT_UP_SOURCE)]
    for line, original in zip(lines, originals, strict=True):
        assert "".join(token.text for token in line.tokens) == original


# The quadrant cut, as a test fixture: two straight cuts and the D A over B C
# rearrangement. This is a *test-local* reimplementation, deliberately — the
# page itself cuts in the browser and posts what it ended up showing (see
# `stage_cut_up_act`), and nothing on the server ever computes an
# arrangement. What it buys is a deterministic way to name a cut by its two
# positions instead of pasting six lines of prose into an assertion.
def _quadrant_cut(source: str, after_line: int, splits: list[int]) -> str:
    """Cut `source` after `after_line` lines and, on each line, at the
    character index `splits` gives — the per-line landing a single vertical
    blade has, since one x meets a different character on every line — then
    read the quarters back as D A over B C."""
    lines = source.split("\n")
    assert len(splits) == len(lines)
    left = [line[:k].strip() for line, k in zip(lines, splits, strict=True)]
    right = [line[k:].strip() for line, k in zip(lines, splits, strict=True)]
    quarters = {
        "a": left[:after_line],
        "b": right[:after_line],
        "c": left[after_line:],
        "d": right[after_line:],
    }
    rows: list[str] = []
    for left_key, right_key in (("d", "a"), ("b", "c")):
        first, second = quarters[left_key], quarters[right_key]
        for i in range(max(len(first), len(second))):
            row = " ".join(part for part in (first[i : i + 1] + second[i : i + 1]) if part != "")
            if row != "":
                rows.append(row)
    return "\n".join(rows)


#: A cut that misses every word: after line 3, and on each line in the gap
#: after "nothing", "them,", "together", "yet", "of" and "one". Pinned by
#: position rather than by its text, so the assertion is about the cut and
#: not about a paragraph someone pasted.
CLEAN_CUT = (3, [21, 17, 19, 25, 14, 19])

#: The same cut with the blade four characters to the left on line one and
#: three to the left on line three — through "nothing" and through
#: "together". One x lands differently on every line, which is exactly why
#: the two lines it goes through are not the four it misses.
TORN_CUT = (3, [18, 17, 16, 25, 14, 19])


def test_a_clean_quadrant_cut_of_the_source_satisfies_the_checker() -> None:
    """The finding this scene is built on. A quadrant rearrangement moves
    words in blocks rather than one at a time, but it is still a
    provenance-preserving permutation, so `check` accepts it — every one of
    the source's 47 words is present, with multiplicity, and none is
    invented. Pinned to fixed cut positions so it is deterministic."""
    from denckring import check

    after_line, splits = CLEAN_CUT
    text = _quadrant_cut(stage.CUT_UP_SOURCE, after_line, splits)
    assert text.split("\n") == [
        "the strange thing stands Five discs of nothing",
        "everything a language and each of them,",
        "folded paper sheet. will bring together",
        "more than cut-out paper, no hand set down, and yet",
        "whenever someone turns, as evidence of",
        "parts that spell a word can hold inside one",
    ]
    report = check("cut_up", text, lang="en", source=stage.CUT_UP_SOURCE)
    assert report.satisfied is True
    assert report.violations == []
    assert report.metrics["words"] == 47
    assert report.metrics["source_words"] == 47


def test_a_cut_through_a_word_fails_and_the_checker_names_every_fragment() -> None:
    """The scene's real demonstration, and not merely `satisfied is False` —
    a test that only checked the boolean would pass if the page failed for
    the wrong reason. The failure has to arise from the physical act: the
    blade crossed "nothing" and "together", and the four pieces those two
    words became are named, each with its rule and its offset."""
    from denckring import check

    after_line, splits = TORN_CUT
    text = _quadrant_cut(stage.CUT_UP_SOURCE, after_line, splits)
    assert text.split("\n") == [
        "the strange thing stands Five discs of noth",
        "everything a language and each of them,",
        "folded paper sheet. will bring toget",
        "ing more than cut-out paper, no hand set down, and yet",
        "whenever someone turns, as evidence of",
        "her parts that spell a word can hold inside one",
    ]
    report = check("cut_up", text, lang="en", source=stage.CUT_UP_SOURCE)
    assert report.satisfied is False
    assert [v.rule for v in report.violations] == ["word_not_in_source"] * 4
    assert [v.found for v in report.violations] == ["noth", "toget", "ing", "her"]
    assert [v.offset for v in report.violations] == [39, 115, 121, 215]
    # Each fragment is named as absent from the source, by name.
    assert [v.expected for v in report.violations] == [
        "at most 0 of 'noth'",
        "at most 0 of 'toget'",
        "at most 0 of 'ing'",
        "at most 0 of 'her'",
    ]
    # And the words the blade went through are in the source, whole.
    folded = {w.casefold() for w in stage.cut_up_source_words(stage.CUT_UP_SOURCE)}
    assert {"nothing", "together"} <= folded


def test_a_straight_column_of_this_source_can_miss_every_word() -> None:
    """The property the scene's passing verdict depends on, and the reason
    the page is set in fixed pitch.

    A blade is one straight line across six lines of type. For the clean cut
    to be something a viewer can actually make, some column has to fall in a
    gap on all six at once. In a proportional face none does. Measured in a
    real browser, counting only columns that actually divide the page — a
    column out in the margin cuts nothing — the display face this scene used
    to carry gives **0** at 1.1rem (page 411px wide, 412 columns), and 0
    again at 1.5, 1.9 and 2.15rem, and 0 in the Georgia fallback at two
    sizes. On a character grid the same source has three clean columns, of
    which one — column 26 — divides the page, and it is the cut the page
    opens on; at the shipped size the browser resolves 14 pixel columns to
    it.

    Computed here from `word_spans`, the same tokenisation the checker uses,
    so a change to the source that took the last clean column away fails
    here rather than quietly making the passing case unreachable."""
    from denckring.core.text import word_spans as _word_spans
    from denckring.lang import get_pack as _get_pack

    pack = _get_pack("en")
    lines = stage.CUT_UP_SOURCE.split("\n")
    extents = [
        [(offset, offset + len(word)) for offset, word in _word_spans(line, pack)] for line in lines
    ]
    clean = [
        column
        for column in range(max(len(line) for line in lines) + 1)
        if all(not any(s < column < e for s, e in line) for line in extents)
    ]
    # 0 and 50 are the margins — a cut there is a horizontal cut alone.
    assert clean == [0, 26, 50]
    assert [line[:26].strip().split()[-1] for line in lines] == [
        "more",
        "whenever",
        "parts",
        "yet",
        "everything",
        "folded",
    ]


def test_first_paint_shows_the_page_uncut_with_two_blades_and_no_verdict() -> None:
    """ "Scenes do not autoplay. The recording is a person using the thing" —
    so first paint carries the page, uncut, the two blades lying across it,
    and an empty result region."""
    response = client.get("/stage/cut_up")
    assert response.status_code == 200
    for word in stage.cut_up_source_words(stage.CUT_UP_SOURCE):
        assert f">{word}<" in response.text
    # The page, not a flattened word list: the source's own punctuation and
    # its six line breaks both have to survive.
    assert response.text.count('class="cutup-line"') == 6
    # Both gaps sit right after a word's own closing tag, not in a contiguous
    # run of plain text — a comma closes the first line, and "cut-out"
    # tokenises to two words either side of a literal hyphen. That hyphen is
    # a *gap* as far as the blade is concerned, which is why the word extents
    # have to come from these spans rather than from splitting on whitespace.
    assert "</span>,</p>" in response.text
    assert "</span>-<span" in response.text
    assert 'id="cutup-result" class="cutup-area"></div>' in response.text
    # No verdict of either colour has been earned yet. Checked against the
    # rendered classes rather than the bare prefix: the script below carries
    # the placeholder's own markup as a string, which a naive `in` matches.
    assert '<p class="verdict yes"' not in response.text
    assert '<p class="verdict no"' not in response.text
    assert 'class="cutup-violations"' not in response.text
    # Two blades, and the submit that commits the cut carries the field the
    # page's own quadrants are read into.
    assert 'id="cutup-blade-v"' in response.text
    assert 'id="cutup-blade-h"' in response.text
    assert 'name="text" id="cutup-text" value=""' in response.text
    # Nothing is in pieces yet.
    assert 'id="cutup-pieces" hidden' in response.text
    assert 'class="cutup-piece cutup-piece-' not in response.text


def test_the_act_route_checks_the_text_the_page_sent_and_echoes_it_back() -> None:
    """The honesty requirement, at the seam: the route checks exactly the
    text it was posted — the text the page read out of its own quadrants —
    and hands that same text back on the verdict, so the page can be held to
    it. Nothing here recomputes an arrangement."""
    after_line, splits = CLEAN_CUT
    text = _quadrant_cut(stage.CUT_UP_SOURCE, after_line, splits)
    response = client.post("/stage/cut_up/act", data={"text": text})
    assert response.status_code == 200
    assert '<p class="verdict yes"' in response.text
    assert "every one of 47 words across the join is the page" in response.text
    echoed = re.search(r'data-checked="(.*?)"', response.text, re.S)
    assert echoed is not None
    assert html.unescape(echoed.group(1)) == text
    assert response.text.count('<p class="verdict') == 1


def test_the_act_route_names_every_fragment_a_torn_cut_made() -> None:
    """The failing verdict runs through the exact same route, template and
    `check` call the passing one does — no special case — and it lists every
    fragment rather than only the first, which is what connects the blade's
    position to the consequence."""
    after_line, splits = TORN_CUT
    text = _quadrant_cut(stage.CUT_UP_SOURCE, after_line, splits)
    response = client.post("/stage/cut_up/act", data={"text": text})
    assert response.status_code == 200
    normalised = " ".join(response.text.split())
    assert '<p class="verdict no"' in normalised
    assert "4 pieces across the join are not words" in normalised
    assert normalised.count("<li>word not in source at offset") == 4
    for fragment in ("noth", "toget", "ing", "her"):
        assert f"&ldquo;{fragment}&rdquo;" in normalised
    assert response.text.count('<p class="verdict') == 1


def test_the_smuggle_route_is_gone() -> None:
    """Retired. The blade produces `word_not_in_source` from the act itself —
    the actual hazard of cutting up a printed page — which is strictly better
    than appending a word by hand, and one demonstration of a rule is
    enough."""
    assert client.post("/stage/cut_up/smuggle").status_code == 404
    assert not hasattr(stage, "cut_up_smuggled")
    assert not hasattr(stage, "CUT_UP_SMUGGLE")
    # And the shuffle the scene used to animate: `apply`'s method, not this
    # scene's. `cut_up.apply` itself is untouched in the library.
    assert not hasattr(stage, "cut_up")
    from denckring.core.registry import get

    assert hasattr(get("cut_up"), "apply")


def test_the_page_and_its_quarters_set_type_from_one_css_rule() -> None:
    """Read from the stylesheet, the same way the reduced-motion rules
    elsewhere on this page are: no test here runs a browser. A quarter that
    set its face, size or leading even slightly differently from the page it
    was cut out of would not read as the same sheet — so the two share one
    rule rather than two copies that can drift."""
    css_path = Path(__file__).parent.parent / "src" / "explorer" / "static" / "stage.css"
    normalised = " ".join(css_path.read_text(encoding="utf-8").split())
    group = ".cutup-line, .cutup-piece-line {"
    assert group in normalised
    body = normalised.split(group, 1)[1].split("}", 1)[0]
    # Fixed pitch, and not by taste: measured on this source in a real
    # browser, no column that actually divides the page missed a word on all
    # six lines in any proportional variant tried (display at 1.1/1.5/1.9/
    # 2.15rem, Georgia at two sizes — zero every time), so the passing
    # verdict was unreachable by hand. In fixed pitch the six lines share a
    # character grid and column 26 is a gap on every one of them.
    assert "font-family: var(--mono);" in body
    assert "font-size: 1.5rem;" in body
    assert "line-height: 2.1;" in body
    assert "white-space: nowrap;" in body
    # A quarter is a window on the lines inside it: a blade that landed
    # mid-glyph has to leave half of it on each piece.
    assert ".cutup-piece { position: absolute; overflow: hidden;" in normalised


def _cut_up_scene_script() -> str:
    """Scene six's own inline script, as the page actually ships it."""
    body = client.get("/stage/cut_up").text
    match = re.search(r"<script>\n(.*?)\n</script>", body, re.S)
    assert match is not None
    return match.group(1)


def test_the_cut_source_checks_the_text_read_from_the_pages_own_quadrants() -> None:
    """A source-level guard, and named as one: the test client runs no
    JavaScript, so what the page actually assembles is out of its reach.
    `tests/browser/cut-blade.mjs clean` is what measures it, by comparing the
    quarters' own text against the `data-checked` the verdict came back with.

    What this holds on to is the shape that makes it true. The text is read
    out of the rendered quarters — `.cutup-piece-line` elements, by
    `textContent`, in the order the eye reads them — and that read is the
    last thing to happen before the submit, so nothing can be shown that was
    not checked or checked that was not shown. The route on the other side
    takes the posted text and nothing else."""
    script = _cut_up_scene_script()
    read = re.search(r"function readAssembledText\(\) \{(.*?)\n\}", script, re.S)
    assert read is not None
    body = read.group(1)
    assert ".cutup-piece-line`" in body
    assert "el.textContent.trim()" in body
    # top row is D then A, bottom row is B then C — Gysin's own rearrangement
    assert "[['d', 'a'], ['b', 'c']]" in body
    cut = re.search(r"async function cutItUp\(\) \{(.*?)\n\}", script, re.S)
    assert cut is not None
    assert "textEl.value = readAssembledText();" in cut.group(1)
    assert cut.group(1).index("readAssembledText()") < cut.group(1).index("requestSubmit()")
    app_src = (Path(__file__).parent.parent / "src" / "explorer" / "app.py").read_text(
        encoding="utf-8"
    )
    route = app_src.split("async def stage_cut_up_act", 1)[1].split("\n@app.", 1)[0]
    assert 'text = str(form.get("text", ""))' in route
    assert 'denckring_check("cut_up", text,' in route
    # Nothing on the server recomputes an arrangement, and nothing reaches
    # for the library's own shuffle — a different method from the one this
    # scene depicts. The comment saying so is in the route; the guard is that
    # the call is not there.
    assert ".apply(" not in route
    assert "Deliberately **not** `cut_up.apply`." in route


def test_the_blade_source_arms_the_placeholder_from_every_path_that_moves_one() -> None:
    """A source-level guard, and named as one; `tests/browser/cut-blade.mjs
    stale` is what measures it in a real browser.

    The invariant this codebase has had broken four times: a real `check()`
    verdict must never stand over a state the viewer has since changed. A
    blade is such a state. Every path that can move one — the pointer drag's
    own `grab`, the arrow keys, and the fresh-sheet button — goes through one
    choke point, which puts the sheet back together, replaces any standing
    verdict with the placeholder, and invalidates the token any in-flight
    check was asked under."""
    script = _cut_up_scene_script()
    invalidate = re.search(r"function invalidate\(\) \{(.*?)\n\}", script, re.S)
    assert invalidate is not None
    body = invalidate.group(1)
    assert "cutToken++;" in body
    assert "restoreWhole();" in body
    assert "setVerdictCutting();" in body
    begin = re.search(r"function beginBladeMove\(\) \{(.*?)\n\}", script, re.S)
    assert begin is not None
    assert "activeBlades++;" in begin.group(1)
    assert "invalidate();" in begin.group(1)
    # the drag's grab, the keyboard, and the fresh-sheet button
    grab = re.search(r"  grab: \(\) => \{(.*?)\n  \},", script, re.S)
    assert grab is not None
    assert "beginBladeMove();" in grab.group(1)
    key = re.search(r"function bladeKey\(evt, key\) \{(.*?)\n\}", script, re.S)
    assert key is not None
    assert "beginBladeMove();" in key.group(1)
    assert key.group(1).index("beginBladeMove();") < key.group(1).index("drawBlades();")
    fresh = re.search(r"freshBtn\.addEventListener\('click', \(\) => \{(.*?)\n\}\);", script, re.S)
    assert fresh is not None
    assert "invalidate();" in fresh.group(1)
    # and the submit is gated while a blade is under a hand
    refresh = re.search(r"function refreshControls\(\) \{(.*?)\n\}", script, re.S)
    assert refresh is not None
    assert "cutBtn.disabled = inert || activeBlades > 0 || cutState !== 'whole';" in refresh.group(
        1
    )


def test_the_cut_source_refuses_a_verdict_for_a_cut_the_viewer_has_undone() -> None:
    """A source-level guard, and named as one; the browser reproduction is
    `tests/browser/cut-blade.mjs stale`.

    The other end of the same invariant, and the exact case the volvelles'
    own Critical was: the viewer moves a blade *during* the check's round
    trip, and the real, checked verdict lands afterwards over a page that is
    no longer showing what it was checked against. The token the request was
    submitted under is compared with the current one on the swap, and a
    verdict that has been overtaken is replaced by the placeholder.

    Deliberately lighter than scenes one and seven's ~150 lines, and for a
    reason that is a property of this scene rather than a shortcut: moving a
    ring leaves a new arrangement that still owes a fresh read, which is why
    those two have to defer and settle that debt. Moving a blade leaves *no*
    cut at all — the correct end state is no verdict, which the placeholder
    already is — so there is nothing to re-read and nothing to replay."""
    script = _cut_up_scene_script()
    before = re.search(
        r"document\.body\.addEventListener\('htmx:beforeRequest', \(evt\) => \{(.*?)\n\}\);",
        script,
        re.S,
    )
    assert before is not None
    assert "submittedToken = cutToken;" in before.group(1)
    after = re.search(
        r"document\.body\.addEventListener\('htmx:afterSwap', \(evt\) => \{(.*?)\n\}\);",
        script,
        re.S,
    )
    assert after is not None
    body = after.group(1)
    assert "if (cutToken !== submittedToken || activeBlades > 0 || cutState !== 'cut') {" in body
    assert body.index("setVerdictCutting();") > body.index("cutToken !== submittedToken")
    # The placeholder is the shared `turning` one, not a third colour.
    turning = re.search(r"function setVerdictCutting\(\) \{(.*?)\n\}", script, re.S)
    assert turning is not None
    assert 'class="verdict turning"' in turning.group(1)


def test_the_blade_drag_reuses_the_shared_pointer_module() -> None:
    """A source-level guard, and named as one; `tests/browser/cut-blade.mjs
    drag` measures the blade actually moving under the pointer.

    The blade's gesture is the volvelles': pointer down grabs, the thing
    follows the pointer live while held, release settles. That is shared at
    the module rather than copied — `attachLinearDrag` sits beside
    `attachDrag` in `hold_turn.js`, using the same page-level release
    registry (so a blur or a backgrounded tab lets go of a blade exactly as
    it lets go of a ring), the same pointer capture, and the same
    per-pointer-id map. Only the arithmetic differs: a blade slides along an
    axis, so there is no centre to sweep about and no detent angle, and
    faking those to reuse `attachDrag` would be a lie about the gesture."""
    js_path = Path(__file__).parent.parent / "src" / "explorer" / "static" / "hold_turn.js"
    js = js_path.read_text(encoding="utf-8")
    assert "function attachLinearDrag(root, handlers) {" in js
    assert "attachLinearDrag," in js  # exported alongside `attach` and `attachDrag`
    linear = js.split("function attachLinearDrag(root, handlers) {", 1)[1]
    linear = linear.split("\n  // The two cadence numbers", 1)[0]
    # the same registry the ring drag and the held buttons use
    assert "active.add(drag.stop);" in linear
    assert "active.delete(drag.stop);" in linear
    # the same capture, and the same per-pointer bookkeeping
    assert "root.setPointerCapture(evt.pointerId);" in linear
    assert "drags.set(evt.pointerId, drag);" in linear
    assert "root.addEventListener('lostpointercapture', (evt) => finish(evt.pointerId));" in linear
    # Live, on every move — not on release. Pinned inside the `pointermove`
    # handler itself: the grab reports an offset too, and a guard that only
    # looked for the call would pass on a blade that jumped once and then
    # sat still until the pointer came up.
    moves = re.search(
        r"root\.addEventListener\('pointermove', \(evt\) => \{(.*?)\n    \}\);", linear, re.S
    )
    assert moves is not None
    assert "drag.offset = offsetOf(drag, evt);" in moves.group(1)
    assert "onMove(drag.key, drag.offset);" in moves.group(1)
    script = _cut_up_scene_script()
    assert "HoldTurn.attachLinearDrag(bladesEl, {" in script
    move = re.search(r"  move: \(key, offset\) => \{(.*?)\n  \},", script, re.S)
    assert move is not None
    assert "drawBlades();" in move.group(1)


def test_the_page_re_measures_itself_once_its_type_has_arrived() -> None:
    """A source-level guard, and named as one, for a defect measured in a
    real browser rather than reasoned about.

    Every cut this scene makes is decided by where each character of the page
    sits, measured with a `Range` per character. That measurement runs in an
    inline script at parse time — before the webfont this page is set in has
    necessarily loaded. Measured against the fallback, every boundary was out
    by about a seventh: a left quarter 595px wide holding 689px of text,
    clipped mid-word at an edge the arithmetic had never seen, and a blade
    that cut somewhere other than where it was drawn. So the page measures
    itself again when the fonts have actually settled, and again if it is
    resized."""
    script = _cut_up_scene_script()
    assert "document.fonts.ready.then(() => relayout(true));" in script
    assert "window.addEventListener('resize', () => relayout(false));" in script
    relayout = re.search(r"function relayout\(reaim\) \{(.*?)\n\}", script, re.S)
    assert relayout is not None
    body = relayout.group(1)
    assert "layout();" in body
    assert "drawBlades();" in body
    # A re-measure invalidates a cut made against the old measurement, the
    # same way moving a blade does.
    assert "if (cutState !== 'whole') invalidate();" in body
    # The character metrics themselves come from a real Range per character,
    # not from an assumed advance width.
    assert "range.setStart(node, i);" in script
    assert "range.getBoundingClientRect();" in script


def test_the_cut_lands_at_once_under_reduced_motion() -> None:
    """A source-level guard, and named as one, for two separate things.

    The house rule first: `explorer.css` sets `transition: none !important`
    under `prefers-reduced-motion`, so an animation that waited on
    `transitionend` would never be told to go on and would strand its
    quarters halfway across the page. This scene cannot be bitten by that,
    because it never listens for the event at all — its three beats are
    chained on timers sized to their own durations, which an interrupted or
    backgrounded transition cannot drop either.

    Then promptness, which is a separate claim and is what the branch below
    is actually for. The brief requires the quarters to *arrive* at once
    under reduced motion, and chained timers do not do that by themselves —
    measured in a real browser with the branch deleted, the cut still landed
    correctly (every transition having been killed, each step applied
    instantly) but took **1390.0ms** of dead waiting to do it, against
    **94.3ms** with the branch. So the branch is not what keeps the quarters
    from being stranded; it is what keeps them from arriving a second and a
    half late.

    The blades keep working either way — nothing about the drag is inside
    this branch."""
    script = _cut_up_scene_script()
    play = re.search(r"function playCut\(\) \{(.*?)\n\}\n", script, re.S)
    assert play is not None
    body = play.group(1)
    assert "if (prefersReducedMotion()) {" in body
    reduced = body.split("if (prefersReducedMotion()) {", 1)[1].split("\n  }", 1)[0]
    assert "place(0, { gap: 0, travel: 1 });" in reduced
    assert "return Promise.resolve(token);" in reduced
    # and it returns before anything with a duration is started
    assert body.index("return Promise.resolve(token);") < body.index("new Promise")
    # Nothing in this scene ever waits on a transition event. Comments are
    # stripped first: the code says why, and that explanation must not be
    # what satisfies this.
    code = "\n".join(line for line in script.splitlines() if not line.strip().startswith("//"))
    assert "transitionend" not in code
    assert "addEventListener('transitionend'" not in script


def test_the_cut_source_frees_itself_when_a_request_never_comes_back() -> None:
    """A source-level guard, and named as one; the browser reproduction is
    `tests/browser/cut-blade.mjs wedge`.

    `inert` is set before the request goes out and cleared in
    `htmx:afterSwap` — and htmx does not swap on a non-2xx, so a 500 or a
    dropped connection left it true forever. That is a *liveness* failure,
    which the token and the placeholder cannot see: they are about a verdict
    being stale, and here no verdict ever arrives. Measured before this
    existed, with the route stubbed, both a 500 and an aborted request left
    `{inert: true, cutDisabled: true, freshDisabled: true}` — every control
    on the scene dead for the rest of the session — and moving a blade did
    not recover it, because the gate reads `inert` too.

    Both volvelles already carried these two lines. This scene now does."""
    script = _cut_up_scene_script()
    failed = re.search(r"function requestFailed\(\) \{(.*?)\n\}", script, re.S)
    assert failed is not None
    body = failed.group(1)
    assert "inert = false;" in body
    assert "refreshControls();" in body
    assert "document.body.addEventListener('htmx:responseError', requestFailed);" in script
    assert "document.body.addEventListener('htmx:sendError', requestFailed);" in script
    # The same safety net every other interactive scene carries, reached the
    # same way. Scene eight joined this guard when it was written: the two
    # volvelles clear the flag through `clearInert`, and scene eight — which
    # can owe a read when the flag comes back — through its own
    # `requestFailed`, which drops that debt rather than paying it into a
    # request that has just failed.
    for other in (_denckring_scene_script(), _llull_scene_script()):
        assert "document.body.addEventListener('htmx:responseError', clearInert);" in other
        assert "document.body.addEventListener('htmx:sendError', clearInert);" in other
    automat = _automat_scene_script()
    assert "document.body.addEventListener('htmx:responseError', requestFailed);" in automat
    assert "document.body.addEventListener('htmx:sendError', requestFailed);" in automat


def test_the_placeholder_describes_the_page_not_what_happened_to_it() -> None:
    """A source-level guard, and named as one.

    Three paths reach the placeholder — a blade moved, the fresh-sheet
    button, and a request that never came back — and a message naming any
    one of them is wrong on the other two. So it names the page's own state
    instead: the sheet is whole and nothing is cut, or it is in pieces no
    verdict ever came back for. Both readings are true whichever path
    arrived at them."""
    script = _cut_up_scene_script()
    turning = re.search(r"function setVerdictCutting\(\) \{(.*?)\n\}", script, re.S)
    assert turning is not None
    body = turning.group(1)
    assert "cutState === 'cut'" in body
    assert "the check did not come back" in body
    assert "nothing cut" in body
    # And nothing the page can *say* claims a blade moved when none did.
    # Comments are stripped first: the code says why the old wording went,
    # and that explanation must not be what fails this.
    code = "\n".join(line for line in script.splitlines() if not line.strip().startswith("//"))
    assert "the blade moved" not in code


def test_every_scene_that_checks_reads_one_verdict_rule() -> None:
    """The trap the brief names: the old sixth scene's own container class
    shared a rule with N+7's and the word ladder's own, and deleting the
    whole block rather than renaming its one arm would have broken both
    other scenes. This pins that `.cutup-area` took over that arm rather
    than the group being deleted — and that the sonnet's own verdict, which
    had grown a private rule at a fourth size, reads the same group now.

    Size and margin are pinned here too. They were the two declarations
    every scene used to override, which is how one sentence came to be set
    four ways. Scene seven's own `.llull-reading-panel .verdict` joined the
    same group rather than writing a private copy — see the task report.

    Restored after the blade round deleted it. Scene six was rewritten from
    the ground up that round and this went with the rewrite, which is
    exactly the failure it exists to catch: four of the five scenes it
    protects have nothing to do with cut-up, and the group it guards
    survived untouched with nothing left pinning it."""
    css_path = Path(__file__).parent.parent / "src" / "explorer" / "static" / "stage.css"
    normalised = " ".join(css_path.read_text(encoding="utf-8").split())
    group = (
        ".displaced-area .verdict, .ladder-wrap .verdict, .cutup-area .verdict, "
        ".poem-verdict, .llull-reading-panel .verdict, .automat-reading .verdict"
    )
    assert group in normalised
    body = normalised.split(group + " {", 1)[1].split("}", 1)[0]
    assert "font-size: 0.78rem;" in body
    assert "margin: 0.5rem 0 0;" in body
    # No scene may quietly take its size or margin back in a rule of its own.
    # Compared against whole selector lists, not substrings: `.poem-verdict`
    # is the tail of the shared list above and would match a naive `in`.
    stripped = re.sub(r"/\*.*?\*/", " ", normalised, flags=re.S)
    selectors = {
        " ".join(block.split("{", 1)[0].split()) for block in stripped.split("}") if "{" in block
    }
    assert selectors.isdisjoint(
        {
            ".displaced-area .verdict",
            ".ladder-wrap .verdict",
            ".cutup-area .verdict",
            ".poem-verdict",
            ".llull-reading-panel .verdict",
            ".automat-reading .verdict",
        }
    )


# ── scene seven: Llull's rotating figure ─────────────────────────────────────


def test_llull_glosses_cover_exactly_the_figures_letters_at_every_level() -> None:
    """The brief's own instruction: a test asserting the gloss table covers
    exactly the figure's nine letters at all six levels, so a future change
    to the figure data cannot silently leave a term untranslated — and so
    that a stray extra entry (a typo'd letter, a level that no longer
    exists) is caught too, not just a missing one."""
    figure = stage.llull_figure_data()
    assert set(stage.LLULL_LEVELS) == set(figure.level_names())
    for level in stage.LLULL_LEVELS:
        assert set(stage.LLULL_GLOSSES[level]) == set(figure.letters)


def test_the_librarys_own_apply_example_still_holds() -> None:
    """The brief's own worked examples, pinned directly against the library
    — not this scene's code, which never calls `apply` itself, but the
    ground truth the scene's design leans on."""
    from denckring.core.protocol import Constructive
    from denckring.core.registry import get

    procedure = get("llull_figure")
    assert isinstance(procedure, Constructive)
    assert procedure.apply("", lang="en", seed=1) == "Bonitas Potestas Gloria"
    assert procedure.apply("", lang="en", seed=5, arity=2) == "Aeternitas Sapientia"
    assert procedure.apply("", lang="en", seed=5, level="relative") == "Medium Aequalitas Minoritas"


def test_llull_positions_are_true_indices_not_text_search() -> None:
    """`llull_positions` must hand back each letter's own place in the
    figure's alphabet — the index a wheel is turned to, never a piece of
    text a client would have to search a wheel's own parts for (see the
    house rule this pins, shared with `pieces_for`)."""
    alphabet = stage.llull_alphabet()
    assert alphabet == ["B", "C", "D", "E", "F", "G", "H", "I", "K"]
    assert stage.llull_positions(["B", "C", "D"]) == [0, 1, 2]
    assert stage.llull_positions(["K", "B"]) == [8, 0]


def test_llull_default_letters_open_on_b_c_d() -> None:
    """First paint's own chamber, deterministic — the alphabet's own first
    combination, matching the brief's own worked example table exactly."""
    assert stage.llull_default_letters(3) == ["B", "C", "D"]
    assert stage.llull_default_letters(2) == ["B", "C"]


def test_llull_random_letters_are_always_a_real_registered_chamber() -> None:
    """`Figure.chambers` is `itertools.combinations`, so every draw is
    `arity` distinct letters by construction — pinned across a spread of
    seeds rather than trusted."""
    figure = stage.llull_figure_data()
    for seed in range(30):
        letters = stage.llull_random_letters(3, rng=random.Random(seed))
        assert len(letters) == 3
        assert len(set(letters)) == 3
        assert "".join(sorted(letters)) in figure.chambers(3)


def test_llull_letters_from_text_rejects_anything_outside_the_alphabet() -> None:
    assert stage.llull_letters_from_text("BCD") == ["B", "C", "D"]
    assert stage.llull_letters_from_text("b c d") == ["B", "C", "D"]
    # Duplicates travel through unchanged — a hand-turned chamber can
    # genuinely repeat a letter, and that is `check`'s own business to
    # refuse, not this parser's.
    assert stage.llull_letters_from_text("BB") == ["B", "B"]
    assert stage.llull_letters_from_text("BJ") is None  # J is not in the alphabet
    assert stage.llull_letters_from_text("") is None
    assert stage.llull_letters_from_text("123") is None


def test_llull_arity_narrows_to_the_two_offered_values() -> None:
    assert stage.llull_arity("3") == 3
    assert stage.llull_arity("2") == 2
    assert stage.llull_arity("9") == 3
    assert stage.llull_arity("not a number") == 3
    assert stage.llull_arity("") == 3


def test_llull_client_data_carries_every_letter_at_every_level() -> None:
    """The JSON blob a held wheel reads locally (see the scene's own
    script) has to carry the same Latin and gloss the server-rendered panel
    does, for every letter of the alphabet — a partial table would leave a
    held wheel landing on a letter with nothing to show for it."""
    data = stage.llull_client_data()
    assert data["levelOrder"] == list(stage.LLULL_LEVELS)
    figure = stage.llull_figure_data()
    for level in stage.LLULL_LEVELS:
        for letter in figure.letters:
            entry = data["levels"][level][letter]
            assert entry["latin"] == figure.levels[level][letter]
            assert entry["gloss"] == stage.LLULL_GLOSSES[level][letter]


def test_first_paint_shows_the_default_chamber_and_satisfies_check() -> None:
    """The scene renders, and the chamber it opens on satisfies a real
    `check()` — the brief's own first requirement."""
    from denckring import check

    response = client.get("/stage/llull_figure")
    assert response.status_code == 200
    assert 'data-arity="3"' in response.text
    assert '<p class="llull-chamber" data-arity="3">B C D</p>' in response.text
    report = check("llull_figure", "BCD", lang="en", figure=stage.LLULL_FIGURE_ID, arity=3)
    assert report.satisfied is True
    assert report.metrics["chambers"] == 84
    # Not two facts side by side — the page shows B C D, and B C D happens to
    # pass — but one: the verdict the page renders is this report's own,
    # down to the numbers it quotes.
    normalised = " ".join(response.text.split())
    assert '<p class="verdict yes">' in normalised
    principles = int(report.metrics["principles"])
    assert f"checked &mdash; a genuine chamber of {principles} distinct principles" in normalised
    chambers = int(report.metrics["chambers"])
    assert f'<span class="count count-true">{chambers:,}</span>' in normalised


def test_first_paint_shows_all_six_levels_with_latin_and_gloss() -> None:
    """Every one of the six tables, each with the chamber's Latin *and* its
    English gloss — the brief's own second requirement."""
    response = client.get("/stage/llull_figure")
    normalised = " ".join(response.text.split())
    expected = [
        ("Bonitas", "goodness"),
        ("Magnitudo", "greatness"),
        ("Aeternitas", "eternity"),
        ("Differentia", "difference"),
        ("Concordantia", "concordance"),
        ("Contrarietas", "contrariety"),
        ("Utrum", "whether?"),
        ("Quid", "what?"),
        ("De quo", "of what?"),
        ("Deus", "God"),
        ("Angelus", "angel"),
        ("Caelum", "heaven"),
        ("Iustitia", "justice"),
        ("Prudentia", "prudence"),
        ("Fortitudo", "fortitude"),
        ("Avaritia", "avarice"),
        ("Gula", "gluttony"),
        ("Luxuria", "lust"),
    ]
    for latin, gloss in expected:
        assert f'<span class="llull-latin">{latin}</span>' in normalised
        # The parentheses around a gloss are CSS-generated content
        # (`.llull-gloss::before`/`::after`, see `stage.css`), not markup —
        # so the plain text is what a rendered response actually carries.
        assert f'<span class="llull-gloss">{gloss}</span>' in normalised
    for level in stage.LLULL_LEVELS:
        assert f'<dt class="llull-level-name">{level}</dt>' in response.text


def test_arity_two_yields_a_two_principle_chamber_and_36_count() -> None:
    """The brief's own third requirement: arity 2 yields a two-principle
    chamber and a chamber count of 36."""
    response = client.post("/stage/llull_figure/act", data={"set_arity": "2"})
    assert response.status_code == 200
    assert 'data-arity="2"' in response.text
    assert 'data-positions="0|1"' in response.text
    assert '<p class="llull-chamber" data-arity="2" data-positions="0|1">B C</p>' in response.text
    normalised = " ".join(response.text.split())
    assert "36" in normalised
    assert "chambers at this arity" in normalised
    assert "a genuine chamber of 2 distinct principles" in normalised


def test_turn_the_wheels_draws_a_real_distinct_chamber_with_positions() -> None:
    """Not pinned to one draw (the route itself never pins a seed) — the
    property: whatever comes back is `arity` distinct letters from the
    figure's own alphabet, each with a true wheel position to animate to."""
    response = client.post("/stage/llull_figure/act", data={"turn": "1", "arity": "3"})
    assert response.status_code == 200
    match = re.search(r'data-arity="3" data-positions="([\d|]+)">([^<]+)<', response.text)
    assert match is not None
    positions = [int(p) for p in match.group(1).split("|")]
    letters = match.group(2).split(" ")
    assert len(letters) == 3
    assert len(set(letters)) == 3
    figure = stage.llull_figure_data()
    assert [figure.letters[p] for p in positions] == letters


def test_reading_a_hand_turned_duplicate_fails_with_repeated_principle() -> None:
    """The organic fail case: two wheels landed, by hand, on the same
    letter. `check` refuses it by name — the same "the validator is the
    eval" shape cut-up's own tamper control demonstrates, reached here
    without a special-cased smuggle button."""
    from denckring import check

    response = client.post("/stage/llull_figure/act", data={"chamber": "BB", "arity": "2"})
    assert response.status_code == 200
    assert '<p class="llull-chamber" data-arity="2">B B</p>' in response.text
    normalised = " ".join(response.text.split())
    assert '<p class="verdict no">' in normalised
    assert "repeated principle: B" in normalised
    report = check("llull_figure", "BB", lang="en", figure=stage.LLULL_FIGURE_ID, arity=2)
    assert report.satisfied is False
    assert report.violations[0].rule == "repeated_principle"


def test_a_malformed_read_falls_back_to_the_aritys_own_default_with_positions() -> None:
    """A stale or hand-crafted `chamber` field (never one this page's own
    script sends) falls back to the arity's own default chamber, and the
    discs are told to sync back to it — `data-positions` present, unlike a
    genuine "Read it" of wheels already sitting where they are."""
    response = client.post("/stage/llull_figure/act", data={"chamber": "ZZ!!", "arity": "2"})
    assert response.status_code == 200
    assert '<p class="llull-chamber" data-arity="2" data-positions="0|1">B C</p>' in response.text


def test_a_plain_read_of_wheels_already_in_place_carries_no_positions() -> None:
    """The complementary case: a chamber the wheels genuinely show needs no
    animation, so the response carries no `data-positions` at all."""
    response = client.post("/stage/llull_figure/act", data={"chamber": "BCD", "arity": "3"})
    assert response.status_code == 200
    assert '<p class="llull-chamber" data-arity="3">B C D</p>' in response.text
    assert "data-positions" not in response.text


def test_hold_turn_js_is_shared_and_wired_into_every_stage_page() -> None:
    """Not a private script of this scene's own template: `hold_turn.js`
    lives in `static/` and `stage.html` includes it for every scene, so a
    follow-up giving scene one the same hold-to-turn controls needs only to
    call `HoldTurn.attach` — the interaction itself, and its release-safety
    net, does not need writing twice."""
    js_path = Path(__file__).parent.parent / "src" / "explorer" / "static" / "hold_turn.js"
    assert js_path.is_file()
    js = js_path.read_text(encoding="utf-8")
    assert "window.HoldTurn" in js
    assert "data-hold-ring" in js
    assert "data-hold-dir" in js
    # Release has to be reachable more than one way — pointer, keyboard, and
    # the two "something took focus/visibility away" backstops.
    for event in ("pointerup", "pointercancel", "lostpointercapture", "keyup"):
        assert event in js
    assert "visibilitychange" in js

    stage_html = (
        Path(__file__).parent.parent / "src" / "explorer" / "templates" / "stage.html"
    ).read_text(encoding="utf-8")
    assert '<script src="/static/hold_turn.js"></script>' in stage_html


def test_hold_controls_css_group_is_shared_not_scene_scoped() -> None:
    """The look lives in `stage.css`'s own shared-machinery section, under
    bare `.hold-controls`/`.hold-btn` selectors — not `.llull-` prefixed —
    so scene one can join it without a second, private copy."""
    css_path = Path(__file__).parent.parent / "src" / "explorer" / "static" / "stage.css"
    normalised = " ".join(css_path.read_text(encoding="utf-8").split())
    assert ".hold-controls {" in normalised
    assert ".hold-btn {" in normalised
    assert ".llull-hold" not in normalised
    assert ".llull-controls" not in normalised
    # The `turning…` placeholder's colour is one rule for both volvelles, not
    # a copy per scene — scene one shipped a byte-identical duplicate of it
    # for a round, which is the drift this file's own shared-machinery note
    # warns about.
    assert (
        ".cutup-area .verdict.turning, .llull-reading-panel .verdict.turning, "
        ".word-panel .verdict.turning, .automat-reading .verdict.turning {"
    ) in normalised
    assert normalised.count(".verdict.turning {") == 1


def _denckring_scene_script() -> str:
    """Scene one's own inline script, as the page actually ships it."""
    body = client.get("/stage/denckring").text
    match = re.search(r"<script>\n(.*?)\n</script>", body, re.S)
    assert match is not None
    return match.group(1)


def _llull_scene_script() -> str:
    """The scene's own inline script, as the page actually ships it."""
    body = client.get("/stage/llull_figure").text
    match = re.search(r"<script>\n(.*?)\n</script>", body, re.S)
    assert match is not None
    return match.group(1)


def test_the_hold_release_source_gates_its_submit_on_no_wheel_still_held() -> None:
    """A source-level guard, and named as one: the test client runs no
    JavaScript, so the drain's own race — a tap on one wheel followed within
    ~50ms by a press on another, which used to exit the drain through the
    ~70ms gap between one step landing and the next repeat being queued, and
    submit while the second button was still down — is out of its reach
    entirely. The browser measurement that does cover it is
    `tests/browser/hold-race.mjs`.

    What this can hold on to is that the gate has not gone away: the release
    path must consult `activeHolds` *before* it submits, and the only
    `requestSubmit` in the scene must be the one behind that gate."""
    script = _llull_scene_script()
    release = re.search(r"async function releaseRead\(\) \{(.*?)\n\}", script, re.S)
    assert release is not None
    body = release.group(1)
    assert body.count(".requestSubmit()") == 1
    assert script.count(".requestSubmit()") == 1
    gate = body.index("activeHolds > 0")
    assert gate < body.index(".requestSubmit()")


def test_the_hold_source_rearms_the_turning_placeholder_from_every_path() -> None:
    """The other half of the same fix, also source-level (see above), and the
    name is only true if *each* path is pinned separately — an earlier version
    of this counted call sites against a threshold it had outgrown, so any one
    of them could be deleted and stay green. Four paths can leave a real
    verdict on screen under a wheel that is about to move or is already
    moving, and each is asserted where it lives:

    1. a hold starting (every start, not the `activeHolds` 0-to-1 transition);
    2. the drain declining to submit because a hold is still running;
    3. a swap landing while a hold runs;
    4. the deferred catch-up replaying after a swap has already put a real
       verdict up — the fix that closed this finding's second instance.
    """
    script = _llull_scene_script()
    assert "function setVerdictTurning() {" in script  # no unused parameter, no dead branch

    def body_of(pattern: str) -> str:
        match = re.search(pattern + r"(.*?)\n\}", script, re.S)
        assert match is not None, pattern
        return match.group(1)

    # 1. every hold start, and the transition still gates the control refresh
    start = body_of(r"function onHoldStart\(\) \{")
    assert "setVerdictTurning();" in start
    assert "if (activeHolds === 1) {" in start
    assert "refreshControls();" in start
    # 2. the drain, which re-arms instead of submitting while a hold runs
    release = body_of(r"async function releaseRead\(\) \{")
    gate = release.index("if (activeHolds > 0) {")
    assert "setVerdictTurning();" in release[gate:]
    assert gate < release.index(".requestSubmit()")
    # 3. a swap landing mid-hold — which also has to redraw the six rows from
    #    where the wheels actually are, or the swap's own (older) chamber
    #    stands under a hand that is resting between two detents
    after_swap = re.search(r"'htmx:afterSwap', \(evt\) => \{(.*?)\n\}\);", script, re.S)
    assert after_swap is not None
    swap = after_swap.group(1)
    assert "if (activeHolds > 0) {" in swap
    guarded = swap[swap.index("if (activeHolds > 0) {") :]
    assert "setVerdictTurning();" in guarded
    assert "renderLocalReading(currentLetters());" in guarded
    # 4. the catch-up replay, before it submits again
    flush = body_of(r"function flushDeferredSteps\(\) \{")
    assert "setVerdictTurning();" in flush
    assert flush.index("setVerdictTurning();") < flush.index("releaseRead()")
    # backstop: the definition and its four callers. A fifth caller is welcome
    # and should be pinned above rather than left to this line.
    assert script.count("setVerdictTurning()") >= 5


def test_the_step_source_defers_a_round_trips_ticks_rather_than_dropping_them() -> None:
    """Source-level again. A round trip that owns the wheels used to make
    `stepWheel` discard the ticks of a button whose finger was still down —
    invisible on a 20ms local response, several real steps on a slow link.
    They are accumulated per wheel now and replayed when the wheels come
    back (`tests/browser/hold-slow-link.mjs` measures the real
    thing: three ticks asked for during an 800ms response, three letters
    moved)."""
    script = _llull_scene_script()
    step = re.search(r"function stepWheel\(wheelIndex, advance\) \{(.*?)\n\}", script, re.S)
    assert step is not None
    assert "deferredAdvance.set" in step.group(1)
    clear = re.search(r"function clearInert\(\) \{(.*?)\n\}", script, re.S)
    assert clear is not None
    assert "flushDeferredSteps();" in clear.group(1)


def test_the_reading_markup_declares_one_scoped_live_region() -> None:
    """Markup, which is all this can see (the announcements themselves are a
    browser's, and were measured — see the task report). Six readings and a
    verdict change under a held button, and the panel is rewritten wholesale
    on every step, so the live region is deliberately *not* the panel: one
    stable, atomic status line outside the swapped region carries the
    chamber and its verdict, and nothing announces the six rows."""
    response = client.get("/stage/llull_figure")
    normalised = " ".join(response.text.split())
    assert 'id="llull-reading" aria-live' not in normalised
    assert 'id="llull-status" role="status" aria-live="polite" aria-atomic="true"' in normalised
    assert 'class="visually-hidden"' in normalised
    css_path = Path(__file__).parent.parent / "src" / "explorer" / "static" / "stage.css"
    css = " ".join(css_path.read_text(encoding="utf-8").split())
    # Clipped, never `display: none` — a hidden live region announces nothing.
    assert ".visually-hidden {" in css
    body = css.split(".visually-hidden {", 1)[1].split("}", 1)[0]
    assert "display: none" not in body
    assert "clip-path: inset(50%);" in body


def test_the_hold_turn_source_focuses_a_mouse_hold_and_only_a_mouse_hold() -> None:
    """Source-level, like the scene's own guards: `preventDefault` on
    `pointerdown` suppresses the focus a click would give the button, which
    left the `blur` release path unreachable for a pointer hold. Focusing
    explicitly restores it — but focus is exclusive, so doing it for touch
    ended a second finger's hold on another wheel (measured: `activeHolds` 1
    instead of 2, see `tests/browser/hold-two-finger.mjs`). The pointer-type
    gate is what keeps both, and nothing else in the suite pins it."""
    js_path = Path(__file__).parent.parent / "src" / "explorer" / "static" / "hold_turn.js"
    js = js_path.read_text(encoding="utf-8")
    assert "evt.pointerType === 'mouse'" in js
    assert js.count(".focus(") >= 1
    # the gate and the focus call are the same statement, not two neighbours
    gate = js.index("evt.pointerType === 'mouse'")
    assert js.index("btn.focus({ preventScroll: true })") > gate


def test_hold_turn_cadence_is_an_attach_option_not_only_a_module_constant() -> None:
    """The adoption precondition scene one needs: `HoldTurn.REPEAT_MS` is a
    copy of a closure constant, so assigning to it does nothing. A scene
    that wants its own rate — scene one's 120-part rings did — passes it to
    `attach`, per attachment, so one scene's preference cannot become
    another's surprise."""
    js_path = Path(__file__).parent.parent / "src" / "explorer" / "static" / "hold_turn.js"
    js = js_path.read_text(encoding="utf-8")
    assert "handlers.initialDelayMs" in js
    assert "handlers.repeatMs" in js
    # and the timers actually use the resolved options, not the defaults
    assert "setTimeout(tick, repeatMs)" in js
    assert "setTimeout(tick, initialDelayMs)" in js
    assert "const DEFAULT_INITIAL_DELAY_MS" in js
    assert "const DEFAULT_REPEAT_MS" in js


def test_hold_turn_cadence_may_also_be_a_function_of_the_ring() -> None:
    """The adoption precondition scene one actually needed. Its five rings run
    from 12 parts to 120, and one number cannot suit both — a rate that reads
    as deliberate on `mittelbuchstabe` is most of a minute of holding to cross
    `endbuchstabe`. So a cadence option may be a function of the ring, resolved
    per hold rather than per attachment, and scene one passes one."""
    js_path = Path(__file__).parent.parent / "src" / "explorer" / "static" / "hold_turn.js"
    js = js_path.read_text(encoding="utf-8")
    assert "function msFor(option, ring, dir, fallback) {" in js
    assert "typeof option === 'function' ? option(ring, dir) : option" in js
    # and both cadences go through it, so neither is a plain number only
    assert "msFor(handlers.repeatMs, ring, dir, DEFAULT_REPEAT_MS)" in js
    assert "msFor(handlers.initialDelayMs, ring, dir, DEFAULT_INITIAL_DELAY_MS)" in js
    script = _denckring_scene_script()
    assert "repeatMs: repeatMsFor," in script


def test_the_drag_source_turns_a_ring_under_the_pointer_not_on_release() -> None:
    """A source-level guard, and named as one: the test client runs no
    JavaScript, so whether the ring actually follows a finger is out of its
    reach. `tests/browser/drag-turn.mjs` is what measures it (22 of 22
    samples carrying a live transform while the pointer was down, worst
    residual half a detent).

    What this holds on to is the shape that makes it true: the shared module
    reports whole detents *and* the fraction between them as the pointer
    moves, and each scene's `turn` callback writes that fraction straight to
    the dial with the transition explicitly off. A `turn` that queued an
    animation, or that only ran on release, would be the one thing this
    gesture cannot be."""
    js_path = Path(__file__).parent.parent / "src" / "explorer" / "static" / "hold_turn.js"
    js = js_path.read_text(encoding="utf-8")
    assert "function attachDrag(root, handlers) {" in js
    assert "attachDrag," in js  # exported alongside `attach`
    # committed whole detents, and the residual, both handed over on move
    assert "const target = Math.round(-drag.sweep / drag.step);" in js
    assert "drag.residual = drag.sweep + target * drag.step;" in js
    assert "onTurn(drag.ring, delta, drag.residual);" in js
    # the sweep is unwrapped, so crossing twelve o'clock is a small move
    assert "function shortestArc(delta) {" in js
    assert "if (d > 180) d -= 360;" in js
    assert "if (d <= -180) d += 360;" in js
    # per pointer id, so two fingers can turn two rings
    assert "const drags = new Map();" in js
    assert "drags.set(evt.pointerId, drag);" in js

    for script in (_denckring_scene_script(), _llull_scene_script()):
        turn = re.search(r"  turn: \(ring, delta, residualDeg\) => \{(.*?)\n  \},", script, re.S)
        assert turn is not None
        body = turn.group(1)
        assert "dragCommit(ring, delta);" in body
        assert ".dial.style.transition = 'none';" in body
        assert ".dial.style.transform = `rotate(${residualDeg}deg)`;" in body


def test_the_drag_source_counts_a_grab_as_a_hold_and_reads_after_the_snap() -> None:
    """The invariant, extended to the new gesture. A drag is a fourth way to
    move a ring (`stepWheel` funnels two of the others and `spinWheelTo`
    reaches `microStep` directly), so it has to arm the `turning…`
    placeholder for the whole grab and count toward the same "a ring is being
    moved" state the submit gate reads — and the read must wait for the
    settle, not fire at the instant the pointer lifts, or a checked verdict
    lands over a ring still visibly moving to its detent.

    Both are structural here: `grab` goes through the same `onHoldStart`
    every held button uses, and `onHoldStop` is called from inside the snap's
    own `.then`, so `activeHolds` stays positive until the ring has landed.

    A release also does nothing *but* snap and stop. Scene one used to step
    one part on a press that crossed no detent, carrying over its old
    click-to-turn; measured, a hand rested on a disc for two seconds and
    lifted off advanced it, and a grab the scene had deliberately refused to
    move still moved. Single-stepping belongs to the step buttons and the
    keyboard, both of which scene one now has."""
    for script in (_denckring_scene_script(), _llull_scene_script()):
        grab = re.search(r"  grab: \(ring\) => \{(.*?)\n  \},", script, re.S)
        assert grab is not None
        assert "onHoldStart();" in grab.group(1)
        release = re.search(r"  release: \(ring, residualDeg\) => \{(.*?)\n  \},", script, re.S)
        assert release is not None
        body = release.group(1)
        snap = re.search(r"(snapRing|snapWheel)\(ring, residualDeg\)\.then\(", body)
        assert snap is not None
        assert body.index("onHoldStop();") > snap.start()
        # No step of any kind on the way out, and no tap to trigger one.
        # Comments are stripped first: the code says why the tap went, and
        # that explanation must not be what satisfies this.
        code = "\n".join(line for line in body.splitlines() if not line.strip().startswith("//"))
        assert "stepRing(" not in code
        assert "stepWheel(" not in code
        assert "tap" not in code
    js_path = Path(__file__).parent.parent / "src" / "explorer" / "static" / "hold_turn.js"
    assert "tapSlopDeg" not in js_path.read_text(encoding="utf-8")


def test_the_drag_source_owes_a_read_for_a_ring_turned_during_a_round_trip() -> None:
    """The Critical this round closed, source-level and named as one; the
    browser measurement is `tests/browser/drag-turn.mjs release-inside`.

    A release-read leaves `wheelsOwned` false, which deliberately lets a
    viewer grab a ring again while that read is still in flight. If the
    second gesture also *ends* before the response lands, nothing is being
    held when the swap arrives — so `htmx:afterSwap` skips its re-arm,
    `releaseRead` has already returned at `if (inert)`, and the server's real,
    checked verdict stands over rings it was never about. It did not decay:
    scene one showed "a word German knows — no" over `Aas`, which German
    does, permanently.

    A drag cannot defer its movement — that is the whole gesture — so what it
    defers is the *read*. `dragCommit` records the debt while `inert`, and
    `flushDeferredSteps` settles it from `clearInert`, the one place the rings
    come back to the client, exactly as it settles a held button's deferred
    ticks. Note the earlier re-arm guard passes either way: the missing piece
    was a re-read, not a re-arm."""
    for script, mover in (
        (_denckring_scene_script(), "dragCommit(ringIndex, delta)"),
        (_llull_scene_script(), "dragCommit(wheelIndex, delta)"),
    ):
        commit = re.search(r"function " + re.escape(mover) + r" \{(.*?)\n\}", script, re.S)
        assert commit is not None, mover
        assert "if (inert) deferredRead = true;" in commit.group(1)
        flush = re.search(r"function flushDeferredSteps\(\) \{(.*?)\n\}", script, re.S)
        assert flush is not None
        body = flush.group(1)
        # consumed once, before anything can return early on it
        assert "let moved = deferredRead;" in body
        assert "deferredRead = false;" in body
        assert body.index("let moved = deferredRead;") < body.index("return;")
        assert "if (deferredAdvance.size === 0 && !moved) return;" in body
        # and an owed read is actually asked for
        assert body.index("releaseRead()") > body.index("if (moved) {")
        clear = re.search(r"function clearInert\(\) \{(.*?)\n\}", script, re.S)
        assert clear is not None
        assert "flushDeferredSteps();" in clear.group(1)
        # The choke point itself, pinned rather than left true by luck. What
        # makes this a funnel and not a fourth way to move a ring is that the
        # debt has one writer and one consumer, and that the consumer has one
        # caller. Each of the four previous instances of this defect arrived by
        # a movement path that did not go where the others went, so a second
        # consumer appearing later is exactly the shape to guard against — and
        # every assertion above would still pass if one did.
        code = "\n".join(line for line in script.splitlines() if not line.strip().startswith("//"))
        # `let deferredRead = false;`, the write in the mover, and the read and
        # the clear in `flushDeferredSteps` — four, and no fifth.
        assert code.count("deferredRead") == 4, mover
        # The definition, and `clearInert` as its only caller.
        assert code.count("flushDeferredSteps") == 2, mover


def test_the_denckring_source_turns_its_rings_backwards_by_index() -> None:
    """Source-level, for the two defects that made scene one one-directional.
    Both were reproduced in a browser before being fixed (see the task
    report): `(0 + -1) % 120` is `-1` in JavaScript, and `` `rotate(-${advance
    * angleStep(r)}deg)` `` builds the literal `rotate(--45deg)`, which the
    browser rejects outright — `style.transform` reads back `""` and the disc
    does not move at all.

    Both are guarded by their fixed form *and* by the absence of the broken
    one, because either alone can be reintroduced without the other."""
    script = _denckring_scene_script()
    assert "r.index = (r.index + advance + r.total) % r.total;" in script
    assert "r.index = (r.index + advance) % r.total;" not in script
    assert "r.dial.style.transform = `rotate(${-advance * angleStep(r)}deg)`;" in script
    assert "`rotate(-${advance * angleStep(r)}deg)`" not in script
    # and the drag commits the same way, on rings whose totals differ
    assert "r.index = (((r.index + delta) % r.total) + r.total) % r.total;" in script


def test_the_denckring_markup_carries_step_buttons_outside_the_swapped_region() -> None:
    """Markup, which is what a test client can see. Scene one never had the
    hold controls; it has them now, one pair per ring, as real `<button>`s so
    a keyboard reaches them — and in `#ring-holds`, which sits outside `#word`,
    the only region htmx ever swaps here. `HoldTurn.attach` scans its
    container once, so a control rendered by a later swap would be silently
    unwired."""
    body = client.get("/stage/denckring").text
    normalised = " ".join(body.split())
    assert 'class="hold-controls" id="ring-holds"' in normalised
    for ring in range(5):
        for direction in ("-1", "1"):
            assert (
                f'<button type="button" class="hold-btn" data-hold-ring="{ring}" '
                f'data-hold-dir="{direction}"' in normalised
            )
    # every button names the ring it turns, in the device's own German
    for name in stage.rings().slots:
        assert f'aria-label="Turn the {name.name} disc back"' in normalised
        assert f'aria-label="Turn the {name.name} disc on"' in normalised
    # the controls are not inside the swapped `#word`
    word_start = normalised.index('<div id="word">')
    word_end = normalised.index("</form>", word_start)
    assert 'id="ring-holds"' not in normalised[word_start:word_end]


def test_the_denckring_markup_declares_one_scoped_live_region() -> None:
    """The same choice scene seven settled on, for the same reason: the word
    panel is rewritten on every step of a held or dragged disc, so announcing
    the panel would announce it several times a second. One stable, atomic
    status line outside the swapped region instead."""
    normalised = " ".join(client.get("/stage/denckring").text.split())
    assert 'id="word" aria-live' not in normalised
    assert 'id="denckring-status" role="status" aria-live="polite" aria-atomic="true"' in normalised


def test_the_denckring_source_rearms_the_turning_placeholder_from_every_path() -> None:
    """Scene one's copy of the invariant three rounds went into on scene
    seven: a real, checked verdict must never stand over discs that have
    since moved. The same four paths can leave one there, and each is pinned
    where it lives — a hold or a grab starting, the drain declining to submit
    while a hand is still down, a swap landing mid-hold, and the deferred
    catch-up replaying after a swap has already put a real verdict up.

    Source-level, and named as one; `tests/browser/drag-turn.mjs` is what
    actually watches the panel while a disc turns."""
    script = _denckring_scene_script()
    assert "function setVerdictTurning() {" in script

    def body_of(pattern: str) -> str:
        match = re.search(pattern + r"(.*?)\n\}", script, re.S)
        assert match is not None, pattern
        return match.group(1)

    start = body_of(r"function onHoldStart\(\) \{")
    assert "setVerdictTurning();" in start
    assert "if (activeHolds === 1) {" in start
    assert "refreshControls();" in start
    release = body_of(r"async function releaseRead\(\) \{")
    gate = release.index("if (activeHolds > 0) {")
    assert "setVerdictTurning();" in release[gate:]
    assert gate < release.index(".requestSubmit()")
    assert release.count(".requestSubmit()") == 1
    assert script.count(".requestSubmit()") == 1
    after_swap = re.search(r"'htmx:afterSwap', \(evt\) => \{(.*?)\n\}\);", script, re.S)
    assert after_swap is not None
    guarded = after_swap.group(1)
    guarded = guarded[guarded.index("if (activeHolds > 0) {") :]
    assert "setVerdictTurning();" in guarded
    assert "renderLocalWord();" in guarded
    flush = body_of(r"function flushDeferredSteps\(\) \{")
    assert "setVerdictTurning();" in flush
    assert flush.index("setVerdictTurning();") < flush.index("releaseRead()")
    assert script.count("setVerdictTurning()") >= 5


def test_the_denckring_step_source_defers_a_round_trips_ticks_and_yields_to_a_grab() -> None:
    """Two refusals in one function, and they are not the same refusal. A
    round trip that owns the discs defers a still-held button's ticks rather
    than dropping them (scene seven measured the difference as a whole
    gesture producing nothing on a slow link); a *grab* on that ring drops
    them outright, because the hand on the disc is the more direct claim on
    it and the two would otherwise fight over the same transform. Measured
    for real in `tests/browser/drag-turn.mjs contend`: 700ms of a held step
    button on a ring a second finger was grabbing moved it no detents."""
    script = _denckring_scene_script()
    step = re.search(r"function stepRing\(ringIndex, advance\) \{(.*?)\n\}", script, re.S)
    assert step is not None
    body = step.group(1)
    assert "if (dragging.has(ringIndex)) return pendingStep;" in body
    assert "deferredAdvance.set" in body
    clear = re.search(r"function clearInert\(\) \{(.*?)\n\}", script, re.S)
    assert clear is not None
    assert "flushDeferredSteps();" in clear.group(1)
    llull = _llull_scene_script()
    assert "if (dragging.has(wheelIndex)) return pendingStep;" in llull


def test_both_volvelles_declare_their_figure_grabbable() -> None:
    """The affordance and the thing that makes a touch drag possible at all,
    in shared CSS rather than two private copies. Without `touch-action:
    none` the gesture scrolls the page instead of turning a ring, so this is
    not decoration."""
    css_path = Path(__file__).parent.parent / "src" / "explorer" / "static" / "stage.css"
    css = " ".join(css_path.read_text(encoding="utf-8").split())
    figure = css.split(".turnable-figure {", 1)[1].split("}", 1)[0]
    assert "touch-action: none;" in figure
    assert (
        ".turnable-figure .ring-disc, .turnable-figure .wheel-disc, .turnable-figure .flap "
        "{ cursor: grab; }"
    ) in css
    assert "cursor: grabbing;" in css
    # Scene eight is not a volvelle and its drums do not sweep an angle, but it
    # is the third scene whose figure is taken hold of, and the affordance and
    # the `touch-action` that makes a touch gesture possible at all are the
    # same two declarations. It joins the group rather than copying it.
    for scene in ("denckring", "llull_figure", "poesie_automat"):
        markup = " ".join(client.get(f"/stage/{scene}").text.split())
        assert "turnable-figure" in markup


# ── scene eight: Enzensberger's Poesie-Automat ────────────────────────────────


def _automat_scene_script() -> str:
    """Scene eight's own inline script, as the page actually ships it."""
    body = client.get("/stage/poesie_automat").text
    match = re.search(r"<script>\n(.*?)\n</script>", body, re.S)
    assert match is not None
    return match.group(1)


def _automat_page() -> str:
    return str(client.get("/stage/poesie_automat").text)


def test_the_boards_two_layouts_measure_134_and_155_characters() -> None:
    """The measurement the whole scene's layout turns on, derived from the
    shipped device rather than quoted from the brief.

    A drum is as wide as the widest of its own ten flaps. Sized per line
    (**A**), the widest line is its six drums plus the five gaps between
    them; aligned into six true columns across all six lines (**B**), every
    column is as wide as the widest module standing anywhere in it. A is 134
    characters and B is 155, and that difference is why this board's drums do
    not line up.

    Characters, not pixels: what the browser makes of them is measured in
    `tests/browser/flap-board.mjs widths`, and the figures it reported are in
    the CSS beside the rule they decided and in the task report.
    """
    board = stage.flap_board()
    per_line = [[len(module.widest) for module in line.modules] for line in board.lines]
    a = max(sum(widths) + len(widths) - 1 for widths in per_line)
    columns = [max(widths[j] for widths in per_line) for j in range(len(per_line[0]))]
    b = sum(columns) + len(columns) - 1
    assert a == 134
    assert b == 155
    # And the scene says so on the page rather than only in a comment: a
    # viewer looking at drums that do not line up is owed the reason.
    note = html.unescape(" ".join(_automat_page().split()))
    assert "155 characters across and does not fit this stage" in note
    assert "the widest line needs 134" in note


def test_no_module_repeats_a_flap() -> None:
    """Why `automat_positions` may look a flap up by its text at all.

    The rule everywhere else in this codebase is that a position is an index
    and never the words printed at it — scene one's `endbuchstabe` repeats two
    of its 120 parts, so a ring found by matching text can only ever land on
    the first occurrence. Nothing on this board repeats within a module, which
    is what makes the one text-to-index lookup on the server unambiguous. If
    that ever stops being true this test says so, rather than the scene
    quietly sending a drum to the wrong flap.
    """
    for line in stage.flap_board().lines:
        for module in line.modules:
            folded = [alternative.casefold() for alternative in module.alternatives]
            assert len(set(folded)) == len(folded)


def test_the_board_reads_back_every_poem_it_presses() -> None:
    """`automat_positions` and `automat_poem` are inverses, over poems the
    library itself composes — so what the client is told to show and what the
    server built it from cannot drift apart."""
    for seed in range(12):
        poem, positions = stage.automat_press(seed)
        assert len(positions) == 36
        assert stage.automat_poem(positions) == poem
        assert stage.automat_positions(poem) == positions
        assert denckring_check("poesie_automat", poem, lang="de").satisfied


def test_the_board_refuses_a_poem_it_cannot_show() -> None:
    """`None`, not an exception and not a guess: a text with the wrong number
    of lines, and a text of the right shape whose words are not on any
    drum."""
    assert stage.automat_positions("nothing like a poem") is None
    poem = stage.automat_poem(stage.automat_default_positions())
    assert stage.automat_positions(poem + "\na seventh line") is None
    assert stage.automat_positions(poem.replace("Morgens", "Mittwochs", 1)) is None


def test_first_paint_is_a_settled_board_and_a_real_verdict() -> None:
    """Every drum on its own first flap, deterministic, with a checked verdict
    for the poem those flaps spell — the scene does not autoplay, and it does
    not open on a claim it has not earned."""
    assert stage.automat_default_positions() == [0] * 36
    body = _automat_page()
    assert 'class="verdict yes"' in body
    assert "checked &mdash; all 6 lines are ones this board can show" in body
    # Every drum's first flap is the one in its window, and the drum says so
    # in the accessible tree too.
    board = stage.flap_board()
    for line in board.lines:
        for module in line.modules:
            assert f'aria-valuetext="{html.escape(module.alternatives[0])}"' in body
    assert body.count('role="slider"') == 36


def test_the_count_is_the_exact_integer_rendered_as_a_power() -> None:
    """`dev.combinations` is a Python `int` and holds 10^36 exactly;
    `metrics["combinations"]` is the same number through a float and comes out
    `1e+36`. The page prints the power, and never the float."""
    board = stage.flap_board()
    assert board.combinations == 10**36
    assert stage.power_of_ten(board.combinations) == 36
    body = _automat_page()
    assert "10<sup>36</sup>" in body
    # Neither the float nor the thirty-seven digits reach the page.
    assert "1e+36" not in body
    assert str(10**36) not in body
    template = (
        Path(__file__).parent.parent
        / "src"
        / "explorer"
        / "templates"
        / "stage_poesie_automat.html"
    ).read_text(encoding="utf-8")
    assert "metrics.combinations" not in template
    assert "metrics['combinations']" not in template


def test_power_of_ten_refuses_a_count_that_is_not_one() -> None:
    """The rendering has to be true of the count it is given. A board whose
    modules were edited to something other than ten alternatives would fall
    out of this and the page would print the digits instead of a power that
    had quietly become a lie."""
    assert stage.power_of_ten(10**36) == 36
    assert stage.power_of_ten(1) == 0
    assert stage.power_of_ten(97_209_600) is None
    assert stage.power_of_ten(11) is None
    assert stage.power_of_ten(0) is None
    assert stage.power_of_ten(-10) is None


def test_the_press_branch_sends_the_drums_somewhere_and_says_nothing_else() -> None:
    """The reply to a press carries the 36 flaps `apply` chose and **no
    verdict**. That is the invariant at the moment it is easiest to break: the
    board is still showing the previous poem and will go on showing it for the
    whole length of the clatter, so anything printed here that looked like a
    verdict would stand over a poem it was not about for a second and a
    half."""
    response = client.post("/stage/poesie_automat/act", data={"press": "1"})
    assert response.status_code == 200
    body = response.text
    assert 'class="verdict turning"' in body
    assert "checked" not in body
    match = re.search(r'data-positions="([^"]+)"', body)
    assert match is not None
    positions = [int(value) for value in match.group(1).split("|")]
    assert len(positions) == 36
    assert all(0 <= value < 10 for value in positions)
    # And they are flaps a real poem is made of.
    assert stage.automat_positions(stage.automat_poem(positions)) == positions


def test_the_read_branch_checks_the_text_it_was_handed() -> None:
    """The other branch: whatever the page says the drums are showing is what
    `check` is asked about, right or wrong."""
    good = stage.automat_poem(stage.automat_default_positions())
    response = client.post("/stage/poesie_automat/act", data={"poem": good})
    assert 'class="verdict yes"' in response.text
    assert f'data-checked="{html.escape(good)}"' in response.text
    bad = good.replace("Morgens", "Mittwochs", 1)
    response = client.post("/stage/poesie_automat/act", data={"poem": bad})
    assert 'class="verdict no"' in response.text
    assert "module not on the board" in response.text


def test_the_automat_route_never_recomputes_the_poem_from_the_seed() -> None:
    """A source-level guard, and named as one; `tests/browser/flap-board.mjs
    press` is what measures it, by comparing the drums' own cells against the
    `data-checked` the verdict came back with.

    The read branch takes the posted text and nothing else. A route that
    pressed the button again and checked *that* poem would be judging a
    second, invisible board that merely resembled the one on screen — and
    would have nothing at all to say about a drum a viewer turned by hand
    afterwards."""
    app_src = (Path(__file__).parent.parent / "src" / "explorer" / "app.py").read_text(
        encoding="utf-8"
    )
    route = app_src.split("async def stage_poesie_automat_act", 1)[1].split("\n@app.", 1)[0]
    read = route.split('if form.get("press"):', 1)[1].split("return page", 1)[1]
    assert 'text = str(form.get("poem", ""))' in read
    assert 'denckring_check("poesie_automat", text,' in read
    # `automat_press` is reached from the press branch and from nowhere else.
    assert route.count("automat_press()") == 1
    assert route.index("automat_press()") < route.index('form.get("poem"')


def test_the_flap_source_reads_the_poem_out_of_the_drums_own_cells() -> None:
    """A source-level guard, and named as one: the test client runs no
    JavaScript, so what the page actually reads off the board is out of its
    reach. `tests/browser/flap-board.mjs press` and `drag` are what measure
    it.

    What this holds on to is the shape that makes it true. The poem is read
    from the cell standing in each drum's window — the element on screen, by
    `textContent` — and that read is the last thing to happen before the
    submit, so nothing can be shown that was not checked or checked that was
    not shown. There is no second copy of the device on the client for it to
    read instead."""
    script = _automat_scene_script()
    window = re.search(r"function windowCell\(slot\) \{(.*?)\n\}", script, re.S)
    assert window is not None
    assert "drums[slot].cells[drums[slot].pos]" in window.group(1)
    read = re.search(r"function readBoard\(\) \{(.*?)\n\}", script, re.S)
    assert read is not None
    body = read.group(1)
    assert "windowCell(Number(el.dataset.slot)).textContent.trim()" in body
    submit = re.search(r"function submitRead\(\) \{(.*?)\n\}", script, re.S)
    assert submit is not None
    assert "poemEl.value = readBoard();" in submit.group(1)
    assert submit.group(1).index("readBoard()") < submit.group(1).index("requestSubmit()")
    # And what a drum *says* is read the same way, so the accessible tree and
    # the checked text can never disagree.
    sync = re.search(r"function syncDrum\(slot\) \{(.*?)\n\}", script, re.S)
    assert sync is not None
    assert "windowCell(slot).textContent.trim()" in sync.group(1)


def test_the_flap_source_arms_the_placeholder_from_every_path_that_moves_a_drum() -> None:
    """A source-level guard, and named as one; `tests/browser/flap-board.mjs
    stale` is what measures it in a real browser.

    The invariant this codebase has had broken five times: a real `check()`
    verdict must never stand over a state the viewer has since changed. A
    drum is such a state, and so is the whole board while it is clattering.
    Every path that can change what the board shows — the pointer drag's own
    `grab`, the arrow keys, and the press's own clatter — goes through one
    choke point, which replaces any standing verdict with the placeholder and
    invalidates the token any in-flight check was asked under."""
    script = _automat_scene_script()
    invalidate = re.search(r"function invalidate\(\) \{(.*?)\n\}", script, re.S)
    assert invalidate is not None
    body = invalidate.group(1)
    assert "boardToken++;" in body
    assert "setVerdictTurning();" in body
    begin = re.search(r"function beginDrumMove\(\) \{(.*?)\n\}", script, re.S)
    assert begin is not None
    assert "activeDrums++;" in begin.group(1)
    assert "invalidate();" in begin.group(1)
    grab = re.search(r"  grab: \(slot\) => \{(.*?)\n  \},", script, re.S)
    assert grab is not None
    assert "beginDrumMove();" in grab.group(1)
    key = re.search(r"function drumKey\(evt, slot\) \{(.*?)\n\}", script, re.S)
    assert key is not None
    assert "beginDrumMove();" in key.group(1)
    assert key.group(1).index("beginDrumMove();") < key.group(1).index("stepDrum(")
    # The clatter arms it too, and arms it as a board that is *running* — the
    # placeholder reads the board's own state for which of its two true things
    # to say, so the flag has to be set before the choke point is called.
    swap = re.search(
        r"document\.body\.addEventListener\('htmx:afterSwap', \(evt\) => \{(.*?)\n\}\);",
        script,
        re.S,
    )
    assert swap is not None
    press = swap.group(1).split("if (raw) {", 1)[1]
    assert press.index("clattering = true;") < press.index("invalidate();")
    # and the submit is gated while anything is moving
    refresh = re.search(r"function refreshControls\(\) \{(.*?)\n\}", script, re.S)
    assert refresh is not None
    assert "const blocked = inert || clattering || activeDrums > 0;" in refresh.group(1)
    assert "pressBtn.disabled = blocked;" in refresh.group(1)
    assert "readBtn.disabled = blocked;" in refresh.group(1)


def test_the_flap_source_refuses_a_verdict_for_a_board_that_has_moved_since() -> None:
    """A source-level guard, and named as one; the browser reproduction is
    `tests/browser/flap-board.mjs stale`.

    The other end of the same invariant, and the exact case the volvelles'
    own Critical was: the viewer turns a drum *during* the check's round trip,
    and the real, checked verdict lands afterwards over a board that is no
    longer showing what it was checked against. The token the request was
    submitted under is compared with the current one on the swap, and a
    verdict that has been overtaken is replaced by the placeholder.

    Unlike scene six, a moved drum leaves a *new* poem that still owes a fresh
    read — the placeholder is not the correct end state here, it is only the
    honest one until the read lands. So the debt is recorded and settled the
    moment the board is the client's again."""
    script = _automat_scene_script()
    before = re.search(
        r"document\.body\.addEventListener\('htmx:beforeRequest', \(evt\) => \{(.*?)\n\}\);",
        script,
        re.S,
    )
    assert before is not None
    assert "submittedToken = boardToken;" in before.group(1)
    swap = re.search(
        r"document\.body\.addEventListener\('htmx:afterSwap', \(evt\) => \{(.*?)\n\}\);",
        script,
        re.S,
    )
    assert swap is not None
    body = swap.group(1)
    assert "if (boardToken !== submittedToken || activeDrums > 0 || clattering) {" in body
    assert body.index("setVerdictTurning();") < body.index("announceReading();")
    # The debt, and the one place it is settled.
    release = re.search(r"function releaseRead\(\) \{(.*?)\n\}", script, re.S)
    assert release is not None
    assert "if (activeDrums > 0 || clattering) return;" in release.group(1)
    assert "deferredRead = true;" in release.group(1)
    clear = re.search(r"function clearInert\(\) \{(.*?)\n\}", script, re.S)
    assert clear is not None
    assert "inert = false;" in clear.group(1)
    assert "deferredRead = false;" in clear.group(1)
    assert "submitRead();" in clear.group(1)


def test_the_flap_source_frees_itself_when_a_request_never_comes_back() -> None:
    """A source-level guard, and named as one; the browser reproduction is
    `tests/browser/flap-board.mjs wedge`.

    `inert` is set before the request goes out and cleared in
    `htmx:afterSwap` — and htmx does not swap on a non-2xx, so a 500 or a
    dropped connection would leave it true forever and both buttons dead for
    the rest of the recording. That is a *liveness* failure, which the token
    and the placeholder cannot see: they are about a verdict being stale, and
    here no verdict ever arrives. Scene six was sent back for exactly this.

    Deliberately not `clearInert`: that settles a read this scene may owe,
    and a read submitted in answer to a failed request would fail in its own
    turn and owe another. The debt is dropped instead."""
    script = _automat_scene_script()
    failed = re.search(r"function requestFailed\(\) \{(.*?)\n\}", script, re.S)
    assert failed is not None
    body = failed.group(1)
    assert "inert = false;" in body
    assert "deferredRead = false;" in body
    assert "setVerdictTurning();" in body
    assert "refreshControls();" in body
    assert "submitRead();" not in body
    assert "document.body.addEventListener('htmx:responseError', requestFailed);" in script
    assert "document.body.addEventListener('htmx:sendError', requestFailed);" in script


def test_the_placeholder_describes_the_board_not_what_happened_to_it() -> None:
    """A source-level guard, and named as one, and scene six's own lesson
    taken second-hand rather than re-learned.

    Four paths reach the placeholder — the clatter, a drum under a hand, a
    verdict overtaken before it landed, and a request that never came back —
    and a message naming any one of them is wrong on the other three. So it
    names the board's own state instead: either something is moving, or
    nothing is and no verdict has been earned for the flaps now showing."""
    script = _automat_scene_script()
    turning = re.search(r"function setVerdictTurning\(\) \{(.*?)\n\}", script, re.S)
    assert turning is not None
    body = turning.group(1)
    assert "clattering || activeDrums > 0" in body
    assert "the flaps are still running" in body
    assert "no verdict for the flaps now showing" in body
    # Never `.yes`/`.no`, and never a stale `data-checked` left underneath it.
    assert "verdict.className = 'verdict turning';" in body
    assert "verdict.removeAttribute('data-checked');" in body
    # And nothing the page can *say* claims a particular path arrived at it.
    # Comments are stripped first — trailing ones too, which is how the first
    # draft of this assertion passed on prose rather than on code.
    code = re.sub(r"//.*", "", script)
    assert "the check did not come back" not in code
    assert "the board has changed" not in code
    # One assignment, and it is the one above: no other line on the page puts
    # words into the verdict.
    assert code.count("verdict.textContent =") == 1


def test_the_flap_source_never_waits_on_a_transition_alone() -> None:
    """The house rule: `explorer.css` sets `transition: none !important` under
    `prefers-reduced-motion`, so `transitionend` never fires there — a clatter
    chained on it would strand every drum on its first flap. The steps and the
    snap are chained on timers sized to their own durations instead, and
    reduced motion takes a separate branch that lands everything at once.

    Comments are stripped first: the code says why, and that explanation must
    not be what satisfies this."""
    script = _automat_scene_script()
    code = "\n".join(line for line in script.splitlines() if not line.strip().startswith("//"))
    assert "transitionend" not in code
    assert "addEventListener('transitionend'" not in script
    clatter = re.search(r"function clatterTo\(targets\) \{(.*?)\n\}", script, re.S)
    assert clatter is not None
    assert "if (prefersReducedMotion()) {" in clatter.group(1)
    assert "landBoard(targets);" in clatter.group(1)
    assert clatter.group(1).index("landBoard") < clatter.group(1).index("runDrum")
    land = re.search(r"function landBoard\(targets\) \{(.*?)\n\}", script, re.S)
    assert land is not None
    assert "drawDrum(slot, 0, 0);" in land.group(1)
    # And a drag still works under reduced motion: only the settle is theatre.
    snap = re.search(r"function snapDrum\(slot\) \{(.*?)\n\}", script, re.S)
    assert snap is not None
    assert "if (!residual || prefersReducedMotion()) {" in snap.group(1)


def test_the_strip_carries_three_turns_and_the_drum_rests_on_the_middle_one() -> None:
    """A source-level guard, and named as one. Measured in a browser before it
    was written: with two turns and the drum parked on the first, dragging
    down past the top flap exposed the blank above the strip, because a hand
    can rest half a cell either side of a detent and there was no cell above
    to show.

    Three turns, resting on the middle, means there is always a real cell
    above the window and a real cell below it. A clatter is at most nine steps
    and starts on the middle turn, so it can never run off the third."""
    body = _automat_page()
    board = stage.flap_board()
    # Every flap of every module, three times over.
    assert body.count('class="flap-cell"') == 36 * 10 * 3
    first = board.lines[0].modules[0]
    assert body.count(f">{first.alternatives[0]}</span>") == 3
    # And the drum opens on the middle turn: flap 0 of a ten-flap module is
    # cell 10, so first paint's own transform is -10 cells, not 0.
    assert "translateY(calc(var(--flap-h) * -10))" in body
    script = _automat_scene_script()
    assert "const HOME = FLAPS;" in script
    normalise = re.search(r"function normalise\(slot\) \{(.*?)\n\}", script, re.S)
    assert normalise is not None
    assert "d.pos = HOME + (((d.pos - HOME) % FLAPS) + FLAPS) % FLAPS;" in normalise.group(1)


def test_the_scene_turns_a_drum_by_index_and_never_by_the_words_on_it() -> None:
    """The rule `hold_turn.js`, `pieces_for` and `llull_positions` all keep.
    The client is handed the flap *numbers* the server worked out and moves
    drums by adding to them; nothing on the page searches a module's flaps for
    matching text, and there is no copy of the device on the client to search.
    """
    script = _automat_scene_script()
    step = re.search(r"function stepDrum\(slot, advance\) \{(.*?)\n\}", script, re.S)
    assert step is not None
    assert "drums[slot].pos += advance;" in step.group(1)
    code = "\n".join(line for line in script.splitlines() if not line.strip().startswith("//"))
    assert "indexOf(" not in code
    assert "textContent ===" not in code
    # The drag is `attachLinearDrag`: a split-flap drum turns about an axis
    # that runs into the screen, so there is no centre on the page to sweep an
    # angle about. Scene eight is the second user of the linear gesture and
    # adds no third shape to the shared module.
    assert "HoldTurn.attachLinearDrag(boardEl, {" in script
    assert "HoldTurn.attachDrag" not in script
    module = (
        Path(__file__).parent.parent / "src" / "explorer" / "static" / "hold_turn.js"
    ).read_text(encoding="utf-8")
    assert module.count("function attach") == 3


def test_the_board_checks_it_fits_the_stage_once_the_face_has_arrived() -> None:
    """A source-level guard, and named as one, and it exists because of a
    measurement rather than a worry.

    Every drum is exactly as wide as its own longest flap, so the board's
    width belongs to the face. At 14px IBM Plex Mono the widest line measures
    1148.68px against the 1184px the stage leaves; with the webfont blocked in
    a browser the fallback measured 1204.05px — twenty pixels of the board
    clipped off the right edge, silently, because `.stage` is `overflow:
    hidden`. Both figures are in the task report, off the rendered page.

    So the cell size is a custom property rather than a constant, and the
    board steps it down until the widest line fits — checked at first paint,
    again once the fonts have actually settled (the moment scene six's own
    measurement had to wait for), and again on a resize. On the face this
    scene was measured for the first size is the answer and nothing moves."""
    css_path = Path(__file__).parent.parent / "src" / "explorer" / "static" / "stage.css"
    normalised = " ".join(css_path.read_text(encoding="utf-8").split())
    assert "--flap-font: 0.875rem;" in normalised
    assert "font-size: var(--flap-font);" in normalised
    script = _automat_scene_script()
    fit = re.search(r"function fitBoard\(\) \{(.*?)\n\}", script, re.S)
    assert fit is not None
    body = fit.group(1)
    assert "const room = boardEl.clientWidth;" in body
    assert "boardEl.style.setProperty('--flap-font', `${size}px`);" in body
    assert "if (widestLine() <= room) return size;" in body
    # The width is measured, never derived from an advance times a count.
    widest = re.search(r"function widestLine\(\) \{(.*?)\n\}", script, re.S)
    assert widest is not None
    assert "el.getBoundingClientRect().width" in widest.group(1)
    assert "getComputedStyle(lineEl).gap" in widest.group(1)
    # And all three moments it is asked.
    assert "\nfitBoard();" in script
    assert "document.fonts.ready.then(fitBoard);" in script
    assert "window.addEventListener('resize', fitBoard);" in script


def test_the_clatter_runs_every_flap_in_between_and_starts_the_drums_apart() -> None:
    """The character of a split-flap display, and the reason to build this
    scene at all: a drum sent from flap a to flap b passes through every flap
    between them rather than cutting to the answer, and the drums are started
    one after another so the board resolves in a wave. What the whole press
    actually clocks is measured in `tests/browser/flap-board.mjs press`; this
    pins the shape that produces it."""
    script = _automat_scene_script()
    run = re.search(r"function runDrum\(slot, target\) \{(.*?)\n\}\n", script, re.S)
    assert run is not None
    body = run.group(1)
    # forward, one flap at a time, the whole way round
    assert "const distance = (target - flapIndex(slot) + FLAPS) % FLAPS;" in body
    assert "drums[slot].pos += 1;" in body
    assert "if (done < distance) {" in body
    # and each drum starts later than the one before it
    assert "setTimeout(tick, slot * STAGGER_MS);" in body
    assert re.search(r"const STAGGER_MS = \d+;", script) is not None
