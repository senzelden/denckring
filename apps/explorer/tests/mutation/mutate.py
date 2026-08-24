"""Mutation harness for scene eight — the letter board and its two cartridges.

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
