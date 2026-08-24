"""Mutation harness: scene eight, and the readings behind the scenes.

Scene eight is the letter board and its two cartridges. The readings are the
companion pages at `/stage/{slug}/reading`, whose guards are almost all
assertions about numbers and about the absence of numbers — the kind that
passes most easily without meaning anything.

Every entry names a file, a fragment to change, what to change it to, and the
test that is supposed to notice. The fragment is replaced, the named test is
run, and the file is restored; a mutation the test does not notice is an
**escape** and means the guard is decorative.

It lives in the repository, and that is the point of it. Three rounds of this
project have had a claim rest on a tool nobody else could run — this one was
written in a scratch directory, quoted at 67/67, and then lost, so the number
could not be reproduced by a reviewer and rested on my word. The browser
reproductions under `tests/browser/` are committed for exactly this reason and
so is this.

    uv run --project apps/explorer python apps/explorer/tests/mutation/mutate.py

Nothing runs it automatically: it rewrites source files in place and runs the
suite once per mutation, which takes minutes. It restores every file it touches
and asserts the restore, but it should not be run against a dirty tree.

**It checks itself before it scores anything.** A previous harness in this
project scored a mutation as killed by a test that did not exist, and the first
version of this one reported every test in the suite as missing because
`pytest --collect-only -q` prints a per-file count rather than node ids. So:
the existence check must say yes to a real test and no to an invented one; every
named test must collect as exactly one item; and every named test must pass
before anything is mutated.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

#: apps/explorer, two parents up from tests/mutation/mutate.py.
APP = Path(__file__).resolve().parents[2]

TPL = APP / "src/explorer/templates/stage_poesie_automat.html"
CSS = APP / "src/explorer/static/stage.css"
STAGE = APP / "src/explorer/stage.py"
APPPY = APP / "src/explorer/app.py"
ENV = APP / "src/explorer/env.py"
YAML = APP / "src/explorer/data/devices/poesieautomat_pokemon.yaml"
SHELL = APP / "src/explorer/templates/stage.html"
R_SHELL = APP / "src/explorer/templates/reading/_shell.html"
R_RINGS = APP / "src/explorer/templates/reading/wheel-and-scissors.html"
R_OULIPO = APP / "src/explorer/templates/reading/oulipo-machines.html"
R_FIGURE = APP / "src/explorer/templates/reading/the-figure.html"
R_AUTOMAT = APP / "src/explorer/templates/reading/the-automat.html"
N7TPL = APP / "src/explorer/templates/stage_n_plus_7.html"
ARS = APP / "src/explorer/ars.py"
ARS_TPL = APP / "src/explorer/templates/_stage_ars.html"
DENCK = APP / "src/explorer/templates/stage_denckring.html"
CUTTPL = APP / "src/explorer/templates/stage_cut_up.html"
CUTFRAG = APP / "src/explorer/templates/_stage_cutup.html"
HOLDJS = APP / "src/explorer/static/hold_turn.js"

T = "tests/test_stage.py::"

#: (file, fragment to replace, replacement, the test that must notice).
MUTATIONS: list[tuple[Path, str, str, str]] = [
    # ── the fold ──────────────────────────────────────────────────────────
    (
        TPL,
        "cell.front.style.transform = 'rotateX(-90deg)';",
        "cell.front.style.transform = 'rotateX(0deg)';",
        T + "test_a_cell_is_two_halves_and_a_fold",
    ),
    (
        TPL,
        "cell.back.style.transform = 'rotateX(0deg)';",
        "cell.back.style.transform = 'rotateX(90deg)';",
        T + "test_a_cell_is_two_halves_and_a_fold",
    ),
    (
        CSS,
        "transform-origin: bottom center;",
        "transform-origin: center center;",
        T + "test_a_cell_is_two_halves_and_a_fold",
    ),
    (
        CSS,
        ".cell.folding .cell-front,\n.cell.folding .cell-back {\n  backface-visibility: hidden;\n}",
        ".cell.folding .cell-front,\n.cell.folding .cell-back {\n  opacity: 1;\n}",
        T + "test_a_cell_is_two_halves_and_a_fold",
    ),
    (
        TPL,
        "foldCell(cell, next, done === steps - 1);",
        "foldCell(cell, next, false);",
        T + "test_a_cell_is_two_halves_and_a_fold",
    ),
    (
        TPL,
        "const SETTLE = 'cubic-bezier(0.34, 1.42, 0.64, 1)';",
        "const SETTLE = 'cubic-bezier(0.34, 0.9, 0.64, 1)';",
        T + "test_a_cell_is_two_halves_and_a_fold",
    ),
    # ── the roll ──────────────────────────────────────────────────────────
    (
        TPL,
        "const next = alphabet[(alphabetIndex(cell.char) + 1) % alphabet.length];",
        "const next = want;",
        T + "test_a_cell_turns_through_every_character_in_between",
    ),
    (
        TPL,
        "landCell(cell, alphabet[((alphabetIndex(want) - cap) % size + size) % size]);",
        "landCell(cell, want);",
        T + "test_a_cell_turns_through_every_character_in_between",
    ),
    (
        TPL,
        "jobs.push(rollCell(cell, want, cap, column * stagger));",
        "jobs.push(rollCell(cell, want, cap, 0));",
        T + "test_a_cell_turns_through_every_character_in_between",
    ),
    (
        TPL,
        "const STAGGER_MS = 20;",
        "const STAGGER_MS = 0;",
        T + "test_a_cell_turns_through_every_character_in_between",
    ),
    (
        TPL,
        "return drawBoard(HAND_ROLL, 0);",
        "return drawBoard(MAX_ROLL, 0);",
        T + "test_a_cell_turns_through_every_character_in_between",
    ),
    (
        TPL,
        "((alphabetIndex(to) - alphabetIndex(from)) % size + size) % size",
        "alphabetIndex(to) - alphabetIndex(from)",
        T + "test_a_cell_turns_through_every_character_in_between",
    ),
    # ── the resting cell ──────────────────────────────────────────────────
    (
        TPL,
        "cell.el.classList.remove('folding');",
        "cell.el.dataset.folded = '1';",
        T + "test_a_resting_cell_holds_no_three_dimensional_transform",
    ),
    (
        TPL,
        "cell.front.style.transform = 'none';",
        "cell.front.style.transform = 'rotateX(0deg)';",
        T + "test_a_resting_cell_holds_no_three_dimensional_transform",
    ),
    (
        CSS,
        ".cell.folding {\n  perspective: 90px;\n}",
        ".cell {\n  perspective: 90px;\n}",
        T + "test_a_resting_cell_holds_no_three_dimensional_transform",
    ),
    (
        TPL,
        "if (element.textContent !== character) element.textContent = character;",
        "element.textContent = character;",
        T + "test_a_resting_cell_holds_no_three_dimensional_transform",
    ),
    # ── the layout ────────────────────────────────────────────────────────
    (
        STAGE,
        "return BLANK * left + text + BLANK * (BOARD_COLUMNS - left - len(text)), spans",
        "return text.center(BOARD_COLUMNS), spans",
        T + "test_the_row_is_centred_by_a_floor_on_both_sides",
    ),
    (
        TPL,
        "const left = Math.floor((COLUMNS - text.length) / 2);",
        "const left = Math.round((COLUMNS - text.length) / 2);",
        T + "test_the_row_is_centred_by_a_floor_on_both_sides",
    ),
    (
        TPL,
        "placeModules(line, drawn.spans);",
        "void drawn.spans;",
        T + "test_the_module_handles_sit_over_the_cells_their_flaps_spell",
    ),
    (
        CSS,
        "  z-index: 2;\n}\n\n.board-module {",
        "}\n\n.board-module {",
        T + "test_the_module_handles_sit_over_the_cells_their_flaps_spell",
    ),
    (
        CSS,
        "  isolation: isolate;",
        "  opacity: 1;",
        T + "test_the_module_handles_sit_over_the_cells_their_flaps_spell",
    ),
    # ── capitals and the alphabet ─────────────────────────────────────────
    (
        STAGE,
        'return text.replace("ß", "ẞ").upper()',
        "return text.upper()",
        T + "test_the_board_shows_capitals_without_widening_a_flap",
    ),
    (
        STAGE,
        "            characters.update(automat_display(alternative))",
        "            characters.update(alternative.upper())",
        T + "test_the_alphabet_is_computed_from_the_loaded_device",
    ),
    (
        STAGE,
        "    characters = {BLANK}",
        '    characters = set(" ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜẞ")',
        T + "test_the_alphabet_is_computed_from_the_loaded_device",
    ),
    # ── the cartridge ─────────────────────────────────────────────────────
    (
        TPL,
        "CARTRIDGES.filter((c) => c.id === document.getElementById('automat-device').value)[0] ||\n"
        "  CARTRIDGES[0];",
        "CARTRIDGES[0];",
        T + "test_the_client_starts_on_the_cartridge_the_server_drew",
    ),
    (
        APPPY,
        'cartridge = stage.automat_cartridge(str(form.get("device", "")))',
        "cartridge = stage.AUTOMAT_CARTRIDGES[0]",
        T + "test_the_scene_refuses_a_cartridge_it_does_not_carry",
    ),
    (
        STAGE,
        '    raise InvalidParams(\n        "poesie_automat",\n'
        '        f"{device_id!r} is not a cartridge this scene carries; "\n'
        '        f"try one of {[c.device_id for c in AUTOMAT_CARTRIDGES]}",\n    )',
        "    return AUTOMAT_CARTRIDGES[0]",
        T + "test_the_scene_refuses_a_cartridge_it_does_not_carry",
    ),
    (
        APPPY,
        "        device=cartridge.device_id,\n    )\n"
        '    return page(request, "_stage_flaps.html", report=report, positions=None, text=text)',
        "    )\n"
        '    return page(request, "_stage_flaps.html", report=report, positions=None, text=text)',
        T + "test_the_check_runs_against_the_cartridge_the_board_is_showing",
    ),
    (
        TPL,
        "deviceEl.value = cart.id;",
        "void cart.id;",
        T + "test_the_check_runs_against_the_cartridge_the_board_is_showing",
    ),
    (
        ENV,
        "*(e for e in existing if e != here)",
        "*existing",
        T + "test_the_second_cartridge_is_the_explorers_and_not_the_packages",
    ),
    (
        YAML,
        "against Bulbapedia's list of official German Pokemon names",
        "against a list of official German Pokemon names",
        T + "test_the_second_cartridge_is_the_explorers_and_not_the_packages",
    ),
    # ── the attribution ───────────────────────────────────────────────────
    (
        STAGE,
        'lexicon="Pokémon flaps, the explorer\'s own",',
        'lexicon="360 flaps written for this project",',
        T + "test_the_credit_follows_the_cartridge",
    ),
    (
        TPL,
        '<p class="scene-kicker" id="automat-kicker">{{ kicker }}</p>',
        '<p class="scene-kicker" id="automat-kicker">Hans Magnus Enzensberger '
        "&middot; Landsberger Poesieautomat, 2000</p>",
        T + "test_the_credit_follows_the_cartridge",
    ),
    (TPL, "  kickerEl.textContent = cart.kicker;", "", T + "test_the_credit_follows_the_cartridge"),
    (STAGE, '        "kicker": cartridge.kicker,', "", T + "test_the_credit_follows_the_cartridge"),
    # ── the invariant ─────────────────────────────────────────────────────
    (
        TPL,
        "  invalidate();\n  announce('Loading the '",
        "  announce('Loading the '",
        T + "test_the_flap_source_arms_the_placeholder_from_every_path_that_moves_the_board",
    ),
    (
        TPL,
        "    input.disabled = blocked;",
        "    input.disabled = false;",
        T + "test_the_flap_source_arms_the_placeholder_from_every_path_that_moves_the_board",
    ),
    (
        TPL,
        "  if (clattering || inert) return;\n  clattering = true;",
        "  clattering = true;",
        T + "test_a_round_trip_that_will_move_the_board_owns_it_and_a_read_does_not",
    ),
    (
        TPL,
        "  if (clattering || (inert && boardOwned)) return;\n  evt.preventDefault();",
        "  evt.preventDefault();",
        T + "test_a_round_trip_that_will_move_the_board_owns_it_and_a_read_does_not",
    ),
    (
        TPL,
        "  if (boardToken !== submittedToken || activeModules > 0 || clattering) {",
        "  if (false) {",
        T + "test_the_flap_source_refuses_a_verdict_for_a_board_that_has_moved_since",
    ),
    (
        TPL,
        "    deferredRead = true;",
        "    deferredRead = false;",
        T + "test_the_flap_source_refuses_a_verdict_for_a_board_that_has_moved_since",
    ),
    (
        TPL,
        "  if (settle && owed && activeModules === 0) submitRead();",
        "  void owed;",
        T + "test_the_flap_source_refuses_a_verdict_for_a_board_that_has_moved_since",
    ),
    (
        TPL,
        "function requestFailed() {\n  setVerdictTurning();\n  clearInert(false);\n}",
        "function requestFailed() {\n  setVerdictTurning();\n  clearInert(true);\n}",
        T + "test_the_flap_source_frees_itself_when_a_request_never_comes_back",
    ),
    (
        TPL,
        "document.body.addEventListener('htmx:sendError', requestFailed);",
        "",
        T + "test_the_flap_source_frees_itself_when_a_request_never_comes_back",
    ),
    (
        TPL,
        "      ? 'the flaps are still running'\n      : 'no verdict for the letters now showing';",
        "      ? 'the cartridge is loading'\n      : 'no verdict for the letters now showing';",
        T + "test_the_placeholder_describes_the_board_not_what_happened_to_it",
    ),
    (
        TPL,
        "  verdict.removeAttribute('data-checked');",
        "",
        T + "test_the_placeholder_describes_the_board_not_what_happened_to_it",
    ),
    # ── the reversal fix ──────────────────────────────────────────────────
    (
        TPL,
        "      if (cell.want === want) continue;\n      cell.want = want;",
        "      if (cell.char === want) continue;",
        T + "test_a_cell_that_is_asked_for_what_it_is_showing_calls_off_its_journey",
    ),
    (
        TPL,
        "  const run = ++cell.run;\n  if (cell.char === want) {",
        "  if (cell.char === want) {\n    const run = 0;\n    void run;",
        T + "test_a_cell_that_is_asked_for_what_it_is_showing_calls_off_its_journey",
    ),
    (
        TPL,
        "    landCell(cell, want);\n    return Promise.resolve();\n  }\n"
        "  if (prefersReducedMotion())",
        "    return Promise.resolve();\n  }\n  if (prefersReducedMotion())",
        T + "test_a_cell_that_is_asked_for_what_it_is_showing_calls_off_its_journey",
    ),
    (
        TPL,
        "      cell.want = alphabet[0];",
        "",
        T + "test_a_cell_that_is_asked_for_what_it_is_showing_calls_off_its_journey",
    ),
    # ── reduced motion ────────────────────────────────────────────────────
    (
        TPL,
        "  if (prefersReducedMotion()) {\n    landCell(cell, want);\n"
        "    return Promise.resolve();\n  }",
        "",
        T + "test_the_flap_source_never_waits_on_a_transition_alone",
    ),
    (
        TPL,
        "  if (prefersReducedMotion()) return Promise.resolve();",
        "  if (false) return Promise.resolve();",
        T + "test_the_flap_source_never_waits_on_a_transition_alone",
    ),
    # ── reading the board ─────────────────────────────────────────────────
    (
        TPL,
        "    .map((row) => row.map((cell) => cell.char).join('').trim())",
        "    .map((row, line) => slotsOfLine(line)"
        ".map((s) => cart.modules[s].flaps[positions[s]]).join(' '))",
        T + "test_the_flap_source_reads_the_poem_out_of_the_cells_themselves",
    ),
    (
        TPL,
        '<button type="button" id="automat-read">',
        '<button type="submit" id="automat-read">',
        T + "test_reading_the_board_is_never_a_native_submit",
    ),
    (
        TPL,
        "  poemEl.value = readBoard();",
        "",
        T + "test_reading_the_board_is_never_a_native_submit",
    ),
    # ── sizing ────────────────────────────────────────────────────────────
    (
        TPL,
        "  const byWidth = cellW / advanceRatio();",
        "  const byWidth = cellW / 0.6;",
        T + "test_the_board_sizes_itself_to_the_stage_once_the_face_has_arrived",
    ),
    (
        TPL,
        "window.addEventListener('resize', fitBoard);",
        "",
        T + "test_the_board_sizes_itself_to_the_stage_once_the_face_has_arrived",
    ),
    (
        TPL,
        "    boardEl.dataset.fits = 'false';",
        "",
        T + "test_the_board_sizes_itself_to_the_stage_once_the_face_has_arrived",
    ),
    # ── the keyboard ──────────────────────────────────────────────────────
    (
        TPL,
        "    case 'PageUp':\n      return 5;",
        "",
        T + "test_a_module_answers_every_key_its_role_promises",
    ),
    (
        TPL,
        "  moved.then(() => endModuleMove());",
        "  endModuleMove();",
        T + "test_a_module_answers_every_key_its_role_promises",
    ),
    # ── the two refusals ──────────────────────────────────────────────────
    (
        STAGE,
        "    if len(found) != len(machine.lines):\n        return None",
        "    if False:\n        return None",
        T + "test_the_board_refuses_a_poem_it_cannot_show",
    ),
    (
        STAGE,
        "        if pieces is None:\n            return None",
        "        if pieces is None:\n            pieces = board.slots[0].alternatives[:1] * 6",
        T + "test_the_board_refuses_a_poem_it_cannot_show",
    ),
    (
        STAGE,
        "    if len(text) > BOARD_COLUMNS:",
        "    if False:",
        T + "test_the_board_refuses_a_line_wider_than_itself",
    ),
    (
        STAGE,
        '            f"{text!r} needs {len(text)} columns and the board has {BOARD_COLUMNS}",',
        '            "the line does not fit",',
        T + "test_the_board_refuses_a_line_wider_than_itself",
    ),
    # ── the lexicon ───────────────────────────────────────────────────────
    (
        YAML,
        '      - "im Schlamm"',
        '      - "im Kalk"',
        T + "test_the_pokemon_cartridge_keeps_the_boards_own_shape",
    ),
    (
        YAML,
        '      - "am Kran"',
        '      - "am Bahndamm"',
        T + "test_the_pokemon_cartridge_keeps_the_boards_own_shape",
    ),
    (
        YAML,
        '      - "im Dreck"',
        '      - "aus Schlamm"',
        T + "test_the_pokemon_cartridge_shows_no_word_twice_on_one_line",
    ),
    (
        YAML,
        '      - "vor Anker"',
        '      - "um vier"',
        T + "test_the_pokemon_cartridge_shows_no_two_incompatible_time_anchors",
    ),
    (
        YAML,
        '      - "an der Mole"',
        '      - "an der Schleuse"',
        T + "test_both_cartridges_fit_the_same_seventy_one_column_board",
    ),
    (
        YAML,
        '      - "unentwegt"',
        '      - "langsam"',
        T + "test_no_adverb_module_carries_a_manner_adverb_or_a_bare_negation",
    ),
    (
        YAML,
        '      - "ringsum"',
        '      - "niemals"',
        T + "test_no_adverb_module_carries_a_manner_adverb_or_a_bare_negation",
    ),
    # ── the readings ──────────────────────────────────────────────────────
    #
    # Every one of these is a wrong number that a mockup of this page actually
    # printed, or a correction that a mockup actually omitted. Two of the
    # guards below were decorative when first written and were rewritten
    # because these mutations walked past them: the parts count, which the
    # page states twice so that retyping one of them still left the computed
    # figure on screen; and the noun list, which the sources footer named even
    # after the inventory making the argument had stopped naming it.
    (
        R_RINGS,
        "and states no total at all.",
        "and states no total at all. Multiplied out that is roughly 83 million words.",
        T + "test_the_rings_reading_states_computed_counts_and_not_the_printed_product",
    ),
    (
        R_RINGS,
        "on holds {{ parts }} word-parts",
        "on holds 254 word-parts",
        T + "test_the_rings_reading_states_computed_counts_and_not_the_printed_product",
    ),
    (
        R_RINGS,
        '<s>{{ "{:,}".format(rings.claimed) }}</s>',
        '{{ "{:,}".format(rings.claimed) }}',
        T + "test_the_rings_reading_states_computed_counts_and_not_the_printed_product",
    ),
    (
        R_RINGS,
        "Denckring is <em>not</em> in the <cite>Poetischer Trichter</cite>. It is in the second",
        "Denckring is in the second",
        T + "test_the_rings_reading_keeps_the_poetischer_trichter_correction",
    ),
    (
        R_OULIPO,
        "the Open English WordNet 2024, CC BY 4.0",
        "a large word list",
        T + "test_the_oulipo_reading_names_the_noun_lists_it_actually_walks",
    ),
    (
        R_FIGURE,
        "<cite>Tabula generalis</cite>, and this project has not checked it against a",
        "<cite>Tabula generalis</cite>, which runs to 1,680, and nobody has checked it against a",
        T + "test_the_figure_reading_states_no_count_nobody_has_checked",
    ),
    (
        R_AUTOMAT,
        "<b>10<sup>{{ exponent }}</sup></b>",
        "<b>a thousand trillion trillion trillion</b>",
        T + "test_the_automat_reading_reads_its_figures_off_the_device",
    ),
    (
        R_SHELL,
        '<article class="reading">',
        '<article class="reading" id="stage">',
        T + "test_a_reading_is_not_a_stage",
    ),
    (
        SHELL,
        '{% if not chrome_off %}\n<p class="stage-caption">',
        "{% if scene is defined %}{% set esc = reading_for(scene.slug) %}{% if esc %}"
        '<p class="stage-reading-link">escaped</p>{% endif %}{% endif %}\n'
        '{% if not chrome_off %}\n<p class="stage-caption">',
        T + "test_the_link_to_a_reading_goes_away_with_the_chrome",
    ),
    (
        STAGE,
        'scenes=("denckring", "cut_up"),',
        'scenes=("denckring", "cut_upp"),',
        T + "test_every_reading_stands_behind_real_scenes",
    ),
    # ── the N+7 offset ────────────────────────────────────────────────────
    #
    # The first two restore the code exactly as it stood while the offset was
    # hard-coded to 7. Both were correct at 7 and wrong at every other member
    # of the family, which is the shape of defect a new control introduces:
    # not a break in what was there, but a path that was never reachable.
    (
        STAGE,
        "                    nouns[(index + step * direction) % len(nouns)]\n"
        "                    for step in range(abs(offset) + 1)",
        "                    nouns[i]\n"
        "                    for i in range(index, index + offset + 1)",
        # At +7 this *is* the code as it stood, so it catches nothing; the
        # empty range only appears going backwards.
        T + "test_the_reel_and_the_text_land_on_the_same_word[-7]",
    ),
    (
        STAGE,
        "                replacement=nouns[(index + offset) % len(nouns)],",
        "                replacement=nouns[index + offset],",
        # Only a word at an end of the list can tell these two apart, which is
        # why the wrap test exists — the harness found that gap. It has to be
        # named at a *forward* offset: going backwards, Python's own negative
        # indexing gives `nouns[-7]` the same entry the modular expression
        # does, so the mutation and the original agree and this escaped when it
        # was named at [-7]. Forward from the last noun runs off the end.
        T + "test_the_reel_wraps_at_the_ends_of_the_list_exactly_as_the_text_does[11]",
    ),
    (
        APPPY,
        '        denckring_check("n_plus_7", produced, source=source, lang=lang, offset=offset)',
        '        denckring_check("n_plus_7", produced, source=source, lang=lang)',
        # At +7 the checker's own default is 7, so only another member of
        # the family separates a dropped offset from a passed one.
        T + "test_the_verdict_names_the_offset_it_was_checked_at[11]",
    ),
    (
        APPPY,
        '    produced = displace(source, stage.pack(lang), offset) if source else ""',
        "    produced = displace(source, stage.pack(lang), stage.N_PLUS_7_OFFSET)"
        ' if source else ""',
        # At +7 the checker's own default is 7, so only another member of
        # the family separates a dropped offset from a passed one.
        T + "test_the_verdict_names_the_offset_it_was_checked_at[11]",
    ),
    # Both of these used to mutate `N_PLUS_7_OFFSETS`, a tuple of seven fixed
    # offsets the scene offered as buttons. The slider replaced it, and the
    # harness's own self-test is what said so: it named two tests that no
    # longer exist and refused to score anything until they did. The
    # replacements mutate what the slider actually rests on.
    (
        STAGE,
        "    return max(-N_PLUS_7_REACH, min(N_PLUS_7_REACH, offset))",
        "    return offset",
        T + "test_an_offset_beyond_the_sliders_reach_is_clamped_to_it",
    ),
    (
        STAGE,
        "        return N_PLUS_7_OFFSET",
        "        return 0",
        T + "test_an_offset_beyond_the_sliders_reach_is_clamped_to_it",
    ),
    # Shortened to exactly the offset the procedure is named after, which is
    # the one value of the reach that makes the scene argue the opposite of
    # what it says. An earlier version of this entry moved 15 to 11 and
    # escaped: the guard rendered its bounds from the constant, so the markup
    # agreed with it whatever it said.
    (
        STAGE,
        "N_PLUS_7_REACH = 15",
        "N_PLUS_7_REACH = 7",
        T + "test_the_offset_control_is_a_slider_over_its_whole_reach",
    ),
    # ── scene six's four operations ──────────────────────────────────────
    #
    # The picker's whole risk is that one operation gets checked by another's
    # rule: these four produce texts each other's checkers sometimes accept,
    # and a green verdict about a method nobody performed is the worst thing
    # this scene could print.
    (
        APPPY,
        'method = stage.cut_method(str(form.get("method", "")))',
        "method = stage.CUT_METHODS[0]",
        T + "test_each_operation_is_checked_by_its_own_procedure_and_not_a_neighbour",
    ),
    (
        APPPY,
        '            column=stage.cut_up_column(str(form.get("column", ""))),',
        "            column=1,",
        T + "test_the_column_the_scene_checks_is_the_column_it_was_asked_for",
    ),
    (
        STAGE,
        "    return max(1, min(cut_up_max_column(), column))",
        "    return column",
        T + "test_the_column_the_scene_checks_is_the_column_it_was_asked_for",
    ),
    # The word bag's missing verdict, from both ends: the route that refuses
    # to check it and the fragment that refuses to draw one.
    (
        APPPY,
        "    if method.procedure is None:",
        '    if method.procedure is None and method.id != "bag":',
        T + "test_the_word_bag_is_given_no_verdict_because_it_can_have_none",
    ),
    (
        STAGE,
        '        procedure=None,\n        how=(\n            "Cut the page into single words',
        '        procedure="cut_up",\n        how=(\n            "Cut the page into single words',
        T + "test_the_word_bag_is_given_no_verdict_because_it_can_have_none",
    ),
    (
        CUTFRAG,
        '<p class="cutup-uncheckable cutup-uncheckable-head" data-checked="{{ text }}">',
        '<p class="verdict turning" data-checked="{{ text }}">',
        T + "test_the_word_bag_is_given_no_verdict_because_it_can_have_none",
    ),
    # And the four themselves, so a picker that quietly became three or four
    # copies of one operation is caught.
    (
        STAGE,
        '        verb="Fold it",',
        '        verb="Cut it",',
        T + "test_the_scene_offers_the_family_and_not_only_its_famous_member",
    ),
    # The fold reads its two halves back by the row they were built in. Pairing
    # them by where they are standing gave twelve lines for a six-line fold,
    # because page B's half only arrives at page A's line as a transform.
    (
        CUTTPL,
        "  el.dataset.row = String(row);",
        "  el.dataset.row = String(0);",
        T + "test_each_operation_is_checked_by_its_own_procedure_and_not_a_neighbour",
    ),
    (
        N7TPL,
        "Open English\n      WordNet 2024 (CC BY 4.0) for English",
        "a large word list for English",
        T + "test_the_scene_names_the_word_list_it_walks",
    ),
    # ── putting a question to the figure ──────────────────────────────────
    #
    # Every one of these is a way the feature could quietly stop being what its
    # own module docstring says it is: a reader with an opinion, clearly
    # labelled, that produces no verdict and turns the figure only to a chamber
    # the figure actually has.
    (
        ARS,
        '    cleaned = "".join(ch for ch in raw.upper() if ch in set(letters))\n'
        "    if len(cleaned) != arity or len(set(cleaned)) != arity:\n"
        '        return ""\n'
        "    return cleaned",
        '    cleaned = "".join(ch for ch in raw.upper() if ch in set(letters))\n'
        "    return cleaned[:arity]",
        T + "test_a_chamber_is_validated_against_the_figure_and_never_repaired",
    ),
    (
        ARS,
        'VERDICTS = ("pro", "contra", "nihil")',
        'VERDICTS = ("pro", "contra")',
        T + "test_nihil_is_one_of_the_things_a_row_may_conclude",
    ),
    (
        ARS_TPL,
        '<p class="ars-label">A reading, not a verdict.',
        '<p class="ars-label">What the wheels said.',
        T + "test_a_reading_of_the_art_is_labelled_as_one",
    ),
    (
        APPPY,
        '            "ars_available": ars.available(),',
        '            "ars_available": True,',
        T + "test_the_figure_is_asked_nothing_without_a_key",
    ),
    # ── scene four's address ──────────────────────────────────────────────
    (
        STAGE,
        "        ordinal = ordinal * len(options) + index\n    return ordinal + 1",
        "        ordinal = ordinal * len(options) + index\n    return ordinal",
        T + "test_the_last_poems_number_is_the_number_of_poems[en]",
    ),
    (
        STAGE,
        "    cuts = (4, 8, 11)",
        "    cuts = (4, 8, 12)",
        T + "test_the_address_is_the_state_broken_where_the_sonnet_is",
    ),
    (
        APPPY,
        '        "_stage_deal.html",',
        '        "_stage_poem.html",',
        T + "test_a_deal_brings_the_address_back_with_it",
    ),
    # ── scene one's tap ───────────────────────────────────────────────────
    #
    # The first is the defect that removed this scene's old click-to-turn: if
    # the band is a target as well as the word, a hand resting on a disc and
    # lifting off turns it. The rest are the ways the gesture goes quietly
    # dead — a press on the part already at the mark animating a turn of zero,
    # a step handed over before the drag has let go of the ring, and a spoke
    # that no longer knows which slot it stands in.
    (
        DENCK,
        "    const part = target && target.closest ? target.closest('.ring-part') : null;\n"
        "    if (!part) return;",
        "    const part = target && target.closest ? target.closest('[data-ring]') : null;\n"
        "    if (!part) return;",
        T + "test_only_a_word_is_a_tap_target",
    ),
    (
        DENCK,
        "    if (!slot) return; // slot 0 is already at the mark; this one turns nothing",
        "    // slot 0 falls through",
        T + "test_only_a_word_is_a_tap_target",
    ),
    (
        DENCK,
        "    text.dataset.slot = String(k);",
        "    text.dataset.index = String(k);",
        T + "test_only_a_word_is_a_tap_target",
    ),
    (
        DENCK,
        "    return snapRing(ring, residualDeg).then(() => {",
        "    void snapRing(ring, residualDeg).then(() => {",
        T + "test_a_release_may_report_when_it_has_settled",
    ),
    (
        HOLDJS,
        "      if (drag.committed === 0 && onTap) {",
        "      if (onTap) {",
        T + "test_a_release_may_report_when_it_has_settled",
    ),
    # The ellipsis. Both halves of the condition, because either one alone
    # would leave the figure lying — the first about how far a ring goes, the
    # second about a ring that goes no further.
    (
        DENCK,
        "  const elided = r.total > r.window;",
        "  const elided = true;",
        T + "test_the_denckring_says_a_ring_goes_on_only_where_it_does",
    ),
    (
        DENCK,
        "    const edge = elided && (k === far || k === far + (r.window % 2 ? 1 : 0));",
        "    const edge = elided && k === 0;",
        T + "test_the_denckring_says_a_ring_goes_on_only_where_it_does",
    ),
    (
        DENCK,
        "    el.classList.toggle('blank', !edge && piece === '');",
        "    el.classList.toggle('blank', piece === '');",
        T + "test_the_denckring_says_a_ring_goes_on_only_where_it_does",
    ),
    # The Wortbuch's control. If it becomes a submit it starts asking the
    # server for the one judgement the server does not have.
    (
        DENCK,
        '<button type="button" id="keep-word" class="quiet">',
        '<button type="submit" id="keep-word" class="quiet">',
        T + "test_the_denckring_wortbuch_keeps_words_without_asking_the_server",
    ),
    # And the sweep that would have caught the `isFastRing` regression. Mutated
    # at a call site rather than a definition, so the guard is tested the way
    # the defect actually arrived: a helper removed, a caller left behind.
    (
        DENCK,
        "  return isFastRing(ringIndex) ? 70 : 130;",
        "  return isFastRingSpeed(ringIndex) ? 70 : 130;",
        T + "test_no_scene_script_calls_a_function_that_does_not_exist",
    ),
]


def _pytest(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "--project", ".", "pytest", "--no-header", "-p", "no:cacheprovider", *args],
        cwd=APP,
        capture_output=True,
        text=True,
    )


def run(selector: str) -> bool:
    """True if the named test passes."""
    return _pytest("-q", selector).returncode == 0


def exists(selector: str) -> bool:
    """Whether pytest collects exactly this one test.

    **Not** with `-q`: pytest 9 collapses `--collect-only -q` to a bare count
    per file (`tests/test_stage.py: 1`) and prints no node ids at all, so a
    substring check against that output says "missing" for every test in the
    suite. That is what the first version of this harness did.
    """
    done = _pytest("--collect-only", selector)
    if done.returncode != 0:
        return False
    ids = [line.strip() for line in done.stdout.splitlines() if "::test_" in line]
    return len(ids) == 1 and ids[0].endswith(selector.split("::")[-1])


def harness_self_test() -> bool:
    """The check has to be able to say no."""
    real = T + "test_a_cell_is_two_halves_and_a_fold"
    fake = T + "test_a_cell_is_two_halves_and_a_fold_that_nobody_wrote"
    if not exists(real):
        print("HARNESS SELF-TEST FAILED: a test that exists was reported missing:", real)
        return False
    if exists(fake):
        print("HARNESS SELF-TEST FAILED: an invented test was reported present:", fake)
        return False
    print("harness self-test: the existence check says yes to a real test, no to an invented one")
    return True


def main() -> int:
    if not harness_self_test():
        return 2
    selectors = sorted({selector for *_, selector in MUTATIONS})
    print(f"harness check: {len(selectors)} distinct tests named by {len(MUTATIONS)} mutations")
    broken = [s for s in selectors if not exists(s)]
    if broken:
        print("HARNESS BROKEN — these tests do not exist:")
        for s in broken:
            print("   ", s)
        return 2
    unmutated = [s for s in selectors if not run(s)]
    if unmutated:
        print("HARNESS BROKEN — these tests fail before any mutation:")
        for s in unmutated:
            print("   ", s)
        return 2
    print("harness check: every named test exists and passes unmutated\n")

    caught = 0
    escaped: list[str] = []
    errors: list[str] = []
    for path, old, new, selector in MUTATIONS:
        source = path.read_text(encoding="utf-8")
        if source.count(old) != 1:
            errors.append(f"{path.name}: {' '.join(old.split())[:60]} appears {source.count(old)}x")
            continue
        path.write_text(source.replace(old, new, 1), encoding="utf-8")
        assert path.read_text(encoding="utf-8") != source, "mutation did not change the file"
        try:
            passed = run(selector)
        finally:
            path.write_text(source, encoding="utf-8")
            assert path.read_text(encoding="utf-8") == source, "restore failed"
        label = f"{path.name}: {' '.join(old.split())[:64]}"
        if passed:
            escaped.append(f"{label} -> {selector.split('::')[-1]}")
            print(f"  ESCAPED  {label}\n           -> {selector.split('::')[-1]}")
        else:
            caught += 1
            print(f"  caught   {label}")
    print(f"\n{caught} caught, {len(escaped)} escaped, {len(errors)} could not be applied")
    for error in errors:
        print("  ERROR", error)
    return 0 if not escaped and not errors else 1


if __name__ == "__main__":
    sys.exit(main())
