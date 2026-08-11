from denckring import check


def test_every_word_sharing_an_initial_is_satisfied() -> None:
    assert check("tautogram", "Peter Piper picked a peck", initial="p").satisfied is False
    assert check("tautogram", "Peter Piper picked pickled peppers", initial="p").satisfied


def test_initial_is_inferred_from_the_first_word() -> None:
    assert check("tautogram", "silent seas sing softly").satisfied


def test_violations_point_at_the_offending_word() -> None:
    report = check("tautogram", "pale pink moon", initial="p")
    assert report.violations[0].found == "moon"
    assert report.violations[0].offset == 10


def test_accented_initials_fold() -> None:
    assert check("tautogram", "élan easy east", initial="e").satisfied


def test_empty_text_is_vacuously_satisfied() -> None:
    assert check("tautogram", "").satisfied
