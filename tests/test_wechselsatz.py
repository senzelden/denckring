from denckring import check

TEMPLATE = "Auf|Ab Nacht|Tag kommt|geht"


def test_a_line_drawn_from_the_template_is_satisfied() -> None:
    assert check("wechselsatz", "Ab Tag geht", source=TEMPLATE).satisfied


def test_a_word_the_template_does_not_offer_is_a_violation() -> None:
    report = check("wechselsatz", "Ab Mond geht", source=TEMPLATE)
    assert not report.satisfied
    assert report.violations[0].found == "Mond"


def test_an_extra_word_is_a_violation() -> None:
    report = check("wechselsatz", "Ab Tag geht nun", source=TEMPLATE)
    assert any(v.rule == "extra_word" for v in report.violations)
