"""The French lexicon's own invariants.

Skipped in full when `denckring[fr]` is not installed, exactly as the German and
English data tests skip without theirs.
"""

import pytest

fr_data = pytest.importorskip("denckring_fr_data", reason="needs denckring[fr]")


def test_the_distribution_is_importable_and_versioned() -> None:
    assert fr_data.__version__ == "0.1.0"
