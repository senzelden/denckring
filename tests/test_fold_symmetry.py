"""Folding the text and folding the parameter must reach the same verdict.

The seam was that `fold_diacritics: true` folded the text and left the parameter
alone. The invariant that catches every instance of it at once: checking folded
input with folding *on* must agree with checking pre-folded input with folding
*off* and the parameter folded by hand. ADR 0035, D3.
"""

import pytest

from denckring import check
from denckring.core.protocol import Lang
from denckring.lang import get_pack

#: `(procedure, lang, text, letter_params, text_params)`. The two parameter
#: groups fold differently — a letter parameter folds per character and a text
#: parameter folds like any other text — which is precisely the distinction the
#: seam collapsed.
CASES: list[tuple[str, Lang, str, dict[str, str], dict[str, str]]] = [
    ("univocalic", "de", "Bäh", {"vowel": "ä"}, {}),
    ("bivocalic", "de", "Bähö", {"vowels": "äö"}, {}),
    ("monoconsonantal", "de", "Mäßig", {"consonant": "m"}, {}),
    ("acrostic", "de", "Sonne\nsehr\ntanzt", {"target": "sst"}, {}),
    (
        "slenderizing",
        "de",
        "Die trae war gro.",
        {"deleted": "s"},
        {"source": "Die Straße war groß."},
    ),
    ("univocalic", "fr", "Cœur", {"vowel": "o"}, {}),
]


def prefold(text: str, lang: Lang) -> str:
    pack = get_pack(lang)
    return "".join(pack.fold_diacritics(ch) if ch.isalpha() else ch for ch in text)


@pytest.mark.parametrize(("pid", "lang", "text", "letter_params", "text_params"), CASES)
def test_folding_the_text_agrees_with_folding_the_parameter(
    pid: str,
    lang: Lang,
    text: str,
    letter_params: dict[str, str],
    text_params: dict[str, str],
) -> None:
    folded_on = check(pid, text, lang=lang, **letter_params, **text_params)
    folded_off = check(
        pid,
        prefold(text, lang),
        lang=lang,
        fold_diacritics=False,
        **{key: prefold(value, lang) for key, value in letter_params.items()},
        **{key: prefold(value, lang) for key, value in text_params.items()},
    )
    assert folded_on.satisfied == folded_off.satisfied, (
        f"{pid} in {lang}: folding on gives {folded_on.satisfied}, "
        f"pre-folded with folding off gives {folded_off.satisfied}"
    )
