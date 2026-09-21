"""A declared language must be a language the row can actually speak.

ADR 0047 widened `languages` on thirty French-sourced rows, and the cheap way
to widen it is the wrong one: adding a language to `languages` and no strings
beside it costs nothing, changes what `describe` advertises, and is invisible
at the point where it does damage. `_text` falls back to English silently and
per field, so the French caller of a row that declares `fr` and carries no
French definition receives English prose in a field typed as French.
`Description.untranslated` was added on 2026-09-04 to stop that fallback being
invisible; this asserts that no *declared* language ever reaches it.

The rule, not today's rows: for every registered procedure and every language
its catalogue row declares, `describe(id, lang=...)` must report neither
`name` nor `definition` as untranslated.

`prompt_hints` is deliberately excluded. It is a hint for a model rather than
prose a reader is shown, nearly every row carries English alone, and requiring
one per declared language would be a different (and much larger) decision than
the one ADR 0047 makes.

The sibling guard in `tests/test_catalogue_quality.py`
(`test_every_declared_language_carries_a_name_and_a_definition`) asserts the
same rule against the YAML, over the whole catalogue including the rows with
no checker. This one asserts it through `describe`, which is the surface a
caller sees and the only place the fallback is observable: the two would
disagree if `_text` or `_fell_back` ever stopped agreeing with the data — a
row whose strings are all present but which `describe` still answers in
English would pass the YAML check and fail this one.
"""

from __future__ import annotations

from typing import get_args

from denckring.core import catalogue
from denckring.core.describe import describe
from denckring.core.protocol import Lang

#: The two fields a reader is actually shown. See the module docstring for why
#: `prompt_hints`, the third thing `untranslated` can name, is not here.
_READER_FACING = ("name", "definition")


def test_a_declared_language_is_never_answered_in_a_substitute(procedure_id: str) -> None:
    fell_back = []
    for lang in catalogue.get(procedure_id).languages:
        assert lang in get_args(Lang), f"{procedure_id} declares unknown language {lang!r}"
        description = describe(procedure_id, lang=lang)
        for field in _READER_FACING:
            if field in description.untranslated:
                fell_back.append(f"{lang}.{field}")
    assert not fell_back, (
        f"{procedure_id} declares a language it cannot say itself in: {fell_back} "
        f"fall back to another language. Either write the missing string or drop "
        f"the language from `languages` — a declaration with no strings behind it "
        f"is a claim about the packs, not about the procedure (ADR 0047)"
    )
