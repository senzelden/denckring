from denckring import check

BORGMANN_REVERSED = "handwriting perplexing illegibly acquired doctors family where know not do I"


def test_shrinking_words_are_satisfied() -> None:
    assert check("reverse_snowball", BORGMANN_REVERSED).satisfied


def test_growing_words_are_not_satisfied() -> None:
    assert not check("reverse_snowball", "I do not").satisfied
