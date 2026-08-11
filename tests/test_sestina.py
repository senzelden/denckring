from denckring import check

SESTINA = """x one
x two
x three
x four
x five
x six
x six
x one
x five
x two
x four
x three
x three
x six
x four
x one
x two
x five
x five
x three
x two
x six
x one
x four
x four
x five
x one
x three
x six
x two
x two
x four
x six
x five
x three
x one"""


def test_a_true_sestina_is_satisfied() -> None:
    assert check("sestina", SESTINA).satisfied


def test_repeating_the_first_stanza_is_not_satisfied() -> None:
    stanza = "\n".join("x " + w for w in ["one", "two", "three", "four", "five", "six"])
    assert not check("sestina", "\n".join([stanza] * 6)).satisfied
