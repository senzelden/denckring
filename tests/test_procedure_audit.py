"""P2-07: the audit went stale once (three procedures with no file, an
undercounted README) with nothing to catch it. This closes that gap.

Issue #19 found the first fix incomplete: it only asserted the subset relation
(every registered procedure has a file), not the equality the module's stated
intent actually calls for. Two directions were still open — a stale audit file
left behind for a procedure that was removed, and `docs/audit/README.md`
itself drifting out of sync with what is actually on disk. The second one was
not hypothetical: `homosyntaxism` and `verbless_prose` (added 2026-09-20, ADR
0045) already had audit files that were named in the README's intro prose but
never classified into any of its `## Rows with a note` / `## Rows that refused
the probe` / `## Rows not exercised` / `## Clean` sections — invisible to a
reader working from the index, which is what those sections are for. Fixed
alongside this guard (see docs/audit/README.md's `## Clean` section)."""

import re
from pathlib import Path

from denckring.core.registry import all_procedures

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "docs" / "audit"

#: Markdown link target pattern used throughout docs/audit/README.md, e.g.
#: "[`anagram`](anagram.md)". Matches only inside the classification sections
#: (see `_classified_ids` below) so a bare mention in prose — exactly how
#: homosyntaxism and verbless_prose went unclassified — does not count.
_LINK = re.compile(r"\[`([\w]+)`\]\((\w+)\.md\)")


def _audited_ids() -> set[str]:
    return {path.stem for path in AUDIT_DIR.glob("*.md") if path.stem != "README"}


def _classified_ids() -> set[str]:
    """Every id linked from README.md's classification sections onward.

    The README opens with prose recapping what was added and when — prose
    that can (and did) name a file without actually filing it into one of
    the sections that make the index navigable. Slicing from the first
    section heading excludes that prose, so a mention there does not
    satisfy this check.
    """
    text = (AUDIT_DIR / "README.md").read_text(encoding="utf-8")
    start = text.index("## Rows with a note")
    return {name for name, _ in _LINK.findall(text[start:])}


def test_every_registered_procedure_has_an_audit_file() -> None:
    missing = sorted(all_procedures().keys() - _audited_ids())
    assert not missing, (
        f"{missing} are registered procedures with no docs/audit/<id>.md — "
        f"add one (see Task 12 of the 2026-09-19 hardening plan for the method) "
        f"or this file goes stale the same way it did before"
    )


def test_no_audit_file_for_a_procedure_that_is_no_longer_registered() -> None:
    """The reverse direction: a stale docs/audit/<id>.md left behind after its
    procedure was removed or renamed documents a row that no longer exists."""
    stale = sorted(_audited_ids() - all_procedures().keys())
    assert not stale, (
        f"{stale} have a docs/audit/<id>.md but are not a registered procedure — "
        f"remove the stale file, or fix the id if it was renamed"
    )


def test_the_audit_readme_classifies_every_audited_file() -> None:
    """docs/audit/README.md is the audit's index. A file present on disk that
    the README never files into `## Rows with a note` / `## Rows that refused
    the probe` / `## Rows not exercised` / `## Clean` is exactly as invisible
    to a reader as a missing file — this is the gap `homosyntaxism` and
    `verbless_prose` fell into (named in the intro, classified nowhere)."""
    audited = _audited_ids()
    classified = _classified_ids()
    unclassified = sorted(audited - classified)
    assert not unclassified, (
        f"{unclassified} have a docs/audit/<id>.md but are not linked from any "
        f"classification section of docs/audit/README.md — file each one under "
        f"the section its actual result belongs in"
    )
    phantom = sorted(classified - audited)
    assert not phantom, (
        f"{phantom} are linked from docs/audit/README.md's classification "
        f"sections but have no docs/audit/<id>.md file — fix or remove the link"
    )
