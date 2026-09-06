"""The instruction files check themselves, because nothing else can.

`CLAUDE.md` and `.claude/rules/*.md` are untracked by decision (spec D5), so this
test skips everywhere except the machine that has them. That is a shape this
project normally distrusts — the MCP job in `ci.yml` exists because
`pytest.importorskip` made a whole extra's tests vanish into a green run — and it
is defensible here only because the subject is machine-local too. There, code
shipped to everyone while its tests ran nowhere; here the check has exactly the
same scope as the thing it checks.
"""

from __future__ import annotations

import glob
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / ".claude" / "rules"
INSTRUCTIONS = ROOT / "CLAUDE.md"

pytestmark = pytest.mark.skipif(
    not RULES.is_dir() or not INSTRUCTIONS.is_file(),
    reason=(
        "CLAUDE.md and .claude/rules/ are untracked (spec D5); present only on "
        "the maintainer's machine"
    ),
)


def _rule_files() -> list[Path]:
    return sorted(RULES.glob("*.md"))


def _paths_of(rule: Path) -> list[str]:
    """The `paths:` list from a rule's YAML frontmatter."""
    text = rule.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{rule.name} has no frontmatter block"
    front = text.split("---", 2)[1]
    loaded = yaml.safe_load(front) or {}
    declared = loaded.get("paths")
    assert isinstance(declared, list), f"{rule.name} declares no `paths:` list"
    return [str(p) for p in declared]


def test_there_are_rules_to_check() -> None:
    """Guards the guard: an empty directory would make every test below vacuous."""
    assert _rule_files(), "no rules found, yet the directory exists"


def test_every_rule_is_path_scoped() -> None:
    """A rule without `paths:` loads unconditionally and defeats the split (spec D4)."""
    for rule in _rule_files():
        assert _paths_of(rule), f"{rule.name} declares an empty `paths:` list"


def test_no_pattern_uses_brace_expansion() -> None:
    """Python's `glob` does not expand braces, so a braced pattern is one this
    test cannot verify — and an unverifiable pattern is the thing being guarded
    against. Write the alternatives as separate entries."""
    for rule in _rule_files():
        for pattern in _paths_of(rule):
            assert "{" not in pattern, f"{rule.name}: {pattern} uses brace expansion"


def test_every_pattern_still_matches_a_file() -> None:
    """The failure this test exists for.

    A renamed module or a moved package leaves a pattern matching nothing, the
    rule silently stops loading, and the symptom is an absence — the hardest
    thing to notice. This cannot catch a pattern that matches the *wrong* files;
    matching nothing is the failure that actually happens.
    """
    stale = []
    for rule in _rule_files():
        for pattern in _paths_of(rule):
            if not glob.glob(pattern, recursive=True, root_dir=ROOT):
                stale.append(f"{rule.name}: {pattern!r} matches nothing")
    assert not stale, "\n".join(stale)


def test_the_root_and_the_rules_agree_in_both_directions() -> None:
    """No rule nothing points at, no pointer leading nowhere.

    Matched on filename rather than on a heading, so reorganising the root's
    prose cannot break the check.
    """
    root = INSTRUCTIONS.read_text(encoding="utf-8")
    for rule in _rule_files():
        assert rule.name in root, f"{rule.name} exists but CLAUDE.md never mentions it"
    for named in set(re.findall(r"rules/([a-z_]+\.md)", root)):
        assert (RULES / named).is_file(), f"CLAUDE.md points at rules/{named}, which is absent"
