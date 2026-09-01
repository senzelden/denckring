from denckring import check


def test_twelve_syllable_lines_are_satisfied() -> None:
    line = "the cat sat on the mat and thought of the wild mice"  # twelve
    assert check("alexandrine", line).satisfied


def test_a_short_line_is_a_violation() -> None:
    assert not check("alexandrine", "the cat sat").satisfied


def test_a_french_line_reports_estimated_words() -> None:
    """Spec D4 and ADR 0034: the French line count is `exact=False`, always --
    ADR 0012's `exact` flag is what already says so, and every syllabic report
    carries `estimated_words`. Whole-branch-review Finding 3: this line is
    twelve syllables of entirely in-vocabulary French (no out-of-vocabulary
    word anywhere in it) and still must report `estimated_words > 0`, because
    `fond` before `de` and the final `coeur` both rest on a mute-e judgment
    the spelling alone does not settle. Before the fix `estimated_words` was
    `0.0` here -- exactly correct and exactly the "confidently wrong" shape
    D4 exists to rule out."""
    line = "Le jour n'est pas plus pur que le fond de mon coeur"
    report = check("alexandrine", line, lang="fr")
    assert report.metrics["estimated_words"] > 0
