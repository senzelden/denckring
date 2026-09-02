"""Folding the text and folding the parameter must reach the same verdict.

The seam was that `fold_diacritics: true` folded the text and left the parameter
alone. The invariant that catches every instance of it at once: checking folded
input with folding *on* must agree with checking pre-folded input with folding
*off* and the parameter folded by hand. ADR 0035, D3.

**Seven of the eight cases discriminate, measured rather than assumed** by
replaying them against the branch point `9472ff0`: each of those seven gives
`on=False, off=True` there and agrees here. The eighth, `slenderizing`, agrees
at the branch point too — its defect was generator-side (D6) and this is a
check-side invariant, so the round-trip property is what covers it. It stays
because the row belongs in the list and because a future check-side regression
would show up here.

The discipline the first draft of this file failed: a case whose parameter is
plain ASCII passes unchanged under the unfolded code and proves nothing, and so
does a case that is `False` on both sides. `target="sst"`, `consonant="m"` and
`vowel="o"` against `Cœur` were all of that kind.
"""

import pytest

from denckring import check
from denckring.core.protocol import Lang
from denckring.lang import get_pack

#: `(procedure, lang, text, letter_params, text_params)`. The two parameter
#: groups fold differently — a letter parameter folds per character and a text
#: parameter folds like any other text — which is precisely the distinction the
#: seam collapsed. Every parameter here carries a diacritic or a `ß`, since one
#: that does not cannot tell the two codepaths apart.
CASES: list[tuple[str, Lang, str, dict[str, str], dict[str, str]]] = [
    ("univocalic", "de", "Bäh", {"vowel": "ä"}, {}),
    ("bivocalic", "de", "Bähö", {"vowels": "äö"}, {}),
    # French, because German has no accented consonant and D4 refuses `ß` as a
    # single-letter parameter while folding is on — so the German half of this
    # row cannot be stated as a symmetry at all.
    ("monoconsonantal", "fr", "Ça ci", {"consonant": "ç"}, {}),
    # All three of the acrostic family: `telestich` inherits from `Acrostic`,
    # `double_acrostic` keeps its own copy of the expression, and only a target
    # folding to two letters exercises the flattening.
    ("acrostic", "de", "Sonne\nsehr\ntanzt", {"target": "ßt"}, {}),
    ("telestich", "de", "das\nes\nvot", {"target": "ßt"}, {}),
    ("double_acrostic", "de", "sonnes\nsehrs\ntanzt", {"first": "ßt", "last": "ßt"}, {}),
    (
        "slenderizing",
        "de",
        "Die trae war gro.",
        {"deleted": "s"},
        {"source": "Die Straße war groß."},
    ),
    ("univocalic", "fr", "Été", {"vowel": "é"}, {}),
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
    assert folded_on.satisfied, (
        f"{pid} in {lang}: both sides agree on False, so the case asserts nothing — "
        f"a symmetry between two refusals holds under the defect as well"
    )
