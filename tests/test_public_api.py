"""What a caller can import from `denckring` itself, without reaching into `core`.

The README puts everything under `denckring.core` outside the stability promise, so
any name a caller needs has to be importable from the top level. denckring-bench
imported four error classes, the golden-case harness and a private clause pattern
from `core`, because nothing else offered them (audit B2-B4, B7, B9).
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest
from pydantic import BaseModel, Field

import denckring
from denckring.core import errors
from denckring.core.hints import show_kinds
from denckring.core.protocol import Lang
from denckring.core.registry import get
from denckring.eval.harness import golden_cases


def test_every_error_class_is_exported_from_the_top_level() -> None:
    """Derived from the module, so a new error class is covered the day it lands."""
    defined = {
        name
        for name, value in vars(errors).items()
        if inspect.isclass(value)
        and issubclass(value, errors.DenckringError)
        and value.__module__ == errors.__name__
    }
    missing = sorted(
        name
        for name in defined
        if getattr(denckring, name, None) is not getattr(errors, name)
        or name not in denckring.__all__
    )
    assert missing == []
    assert "DenckringError" in defined


def test_the_pack_surface_is_exported_from_the_top_level() -> None:
    """`get_pack` and the protocol it returns are a contract (README, audit B3)."""
    from denckring import lang
    from denckring.core import protocol

    assert denckring.get_pack is lang.get_pack
    assert denckring.LanguagePack is protocol.LanguagePack
    assert denckring.PosTag is protocol.PosTag
    assert {"get_pack", "LanguagePack", "PosTag"} <= set(denckring.__all__)
    assert isinstance(denckring.get_pack("en"), denckring.LanguagePack)


def test_golden_cases_filters_by_language_and_keeps_the_whole_corpus_on_request() -> None:
    every = denckring.golden_cases(runnable=False)
    german = denckring.golden_cases("de", runnable=False)
    assert german and {case.lang for case in german} == {"de"}
    assert len(german) < len(every)
    assert {(case.procedure, case.name, case.lang) for case in every} == {
        (case.procedure, case.name, case.lang) for case in golden_cases()
    }


def test_golden_cases_drops_what_this_install_cannot_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """A pack lacking a capability drops every case whose row or whose own `requires`
    asks for it: run, each would end in `MissingCapability` or answer about the data.

    The Gryphius alexandrine is the case whose row needs only the heuristic and whose
    own verdict needs the dictionary, so it is the one dropped for the case alone."""

    class Heuristic:
        capabilities: frozenset[str] = frozenset({"tokens", "syllables.heuristic"})

    monkeypatch.setattr(denckring, "get_pack", lambda lang: Heuristic())
    kept = denckring.golden_cases()
    assert kept
    assert all(
        set(case.requires) | set(get(case.procedure).meta.requires) <= Heuristic.capabilities
        for case in kept
    )
    alexandrines = {case.name for case in kept if case.procedure == "alexandrine"}
    assert alexandrines
    assert "gryphius-traenen-alexandriner" not in alexandrines


def test_render_hint_renders_a_callers_template_by_the_rows_rule() -> None:
    assert (
        denckring.render_hint("consonantal_lipogram", "Avoid {forbidden}.", forbidden="ST")
        == 'Avoid "s", "t".'
    )
    assert denckring.render_hint("syllable_count", "Lines of {pattern}.", pattern=[5, 7, 5]) == (
        "Lines of 5, 7, 5."
    )


def test_render_hint_validates_as_check_does() -> None:
    with pytest.raises(denckring.InvalidParams):
        denckring.render_hint("consonantal_lipogram", "Avoid {forbidden}.", forbidden="4")
    with pytest.raises(denckring.InvalidParams, match="not parameters"):
        denckring.render_hint("consonantal_lipogram", "Avoid {letters}.", forbidden="st")
    with pytest.raises(denckring.UnsetHintParameter):
        denckring.render_hint("bivocalic", "Only {vowels}.")
    with pytest.raises(denckring.UnknownLanguage):
        denckring.render_hint("lipogram", "No {forbidden}.", lang="xx")  # type: ignore[arg-type]


def test_a_letter_set_reads_as_letters_in_the_rows_own_hint() -> None:
    """`"et"` quoted whole reads as a word; the bench re-rendered it (R77, audit B6)."""
    hint = denckring.prompt_hint("consonantal_lipogram", forbidden="et")
    assert '"e", "t"' in hint
    assert '"et"' not in hint
    assert '"a", "e"' in denckring.prompt_hint("bivocalic", vowels="ae")


def test_every_declared_show_kind_is_one_the_renderer_knows() -> None:
    """`show_kinds` refuses an unknown kind; reading every row's model proves none has one."""
    declared = {
        (pid, name)
        for pid, procedure in denckring.all_procedures().items()
        for name in show_kinds(procedure.params_model())
    }
    assert ("consonantal_lipogram", "forbidden") in declared


def test_an_unknown_show_kind_is_refused() -> None:
    class Params(BaseModel):
        forbidden: str = Field(json_schema_extra={"x-denckring-show": "word"})

    with pytest.raises(ValueError, match="unknown x-denckring-show"):
        show_kinds(Params)


@pytest.mark.parametrize("lang", ["en", "de", "fr"])
def test_pack_provenance_is_what_a_report_records(lang: Lang) -> None:
    """The bench `getattr`ed `data_distributions` itself (audit B9)."""
    report = denckring.check("lipogram", "a text", lang=lang, forbidden="z")
    assert report.provenance is not None
    assert denckring.pack_provenance(lang) == report.provenance.pack
    assert {"pack_provenance", "PackProvenance"} <= set(denckring.__all__)


def test_pack_provenance_names_the_data_an_installed_pack_reads() -> None:
    pack = denckring.get_pack("en")
    recorded = denckring.pack_provenance("en")
    assert set(recorded.data) == set(getattr(pack, "data_distributions", ()))
    assert recorded.pack == type(pack).__name__


DOCS_API = Path(__file__).resolve().parents[1] / "docs" / "api"
README = Path(__file__).resolve().parents[1] / "README.md"

#: Documented where defined because `denckring` does not export them, so no top-level
#: path exists to document them from.
UNEXPORTED_DOCUMENTED = {"denckring.core.protocol.Constructive"}


def _exported() -> list[str]:
    return [name for name in denckring.__all__ if not name.startswith("_")]


def _directives() -> set[str]:
    return {
        line.removeprefix(":::").strip()
        for page in DOCS_API.glob("*.md")
        for line in page.read_text(encoding="utf-8").splitlines()
        if line.startswith(":::")
    }


def test_the_api_docs_document_every_export_from_the_top_level() -> None:
    """The API pages documented `denckring.core.*` paths, which the README puts
    outside the stability promise, and left out `apply` and `produce` (audit E1)."""
    documented = _directives()
    missing = sorted(name for name in _exported() if f"denckring.{name}" not in documented)
    assert missing == []
    elsewhere = sorted(
        path
        for path in documented - UNEXPORTED_DOCUMENTED
        if path.removeprefix("denckring.") not in denckring.__all__
    )
    assert elsewhere == [], "document an exported name from `denckring`, not where it is defined"


def _classifying_text(readme: str) -> str:
    """The parts of "What is stable" that classify an export: the bullet naming the
    exports under the promise, the pack-surface bullet, and the list of what is
    published but not yet promised. The rest of the section names fields and keys
    (`provenance`, `estimated`), which say nothing about an export of that name."""
    section = readme.split("## What is stable", 1)[1].split("\n## ", 1)[0]
    bullets = section.split("\n- ")
    promised = [
        bullet
        for bullet in bullets
        if bullet.startswith(("**The names `denckring` exports**", "**The language-pack surface**"))
    ]
    assert len(promised) == 2, "the promise's two export bullets were renamed"
    not_yet = section.split("**Published, not yet promised.**", 1)[1]
    return "\n".join([*promised, not_yet])


def test_the_stability_section_classifies_every_export() -> None:
    """Every name `denckring` exports is either promised or listed as not yet promised,
    so a new export cannot arrive without the README saying which (audit E1). Error
    classes are covered as a family: `DenckringError` and every subclass. A name counts
    only as a whole backticked token in the classifying text, so a field such as
    `provenance` elsewhere in the section does not classify an export of that name."""
    tokens = set(re.findall(r"`([^`]+)`", _classifying_text(README.read_text(encoding="utf-8"))))
    unnamed = sorted(
        name
        for name in _exported()
        if name not in tokens
        and f"denckring.{name}" not in tokens
        and not (
            inspect.isclass(value := getattr(denckring, name))
            and issubclass(value, errors.DenckringError)
        )
    )
    assert unnamed == []


@pytest.mark.parametrize(
    ("lang", "expected"),
    [("en", '"s", "t"'), ("de", "„s“, „t“"), ("fr", "« s », « t »")],
)
def test_a_letter_set_is_quoted_as_its_language_quotes(lang: Lang, expected: str) -> None:
    """A French hint read `aucune de ces lettres : "b", "c"` while quoting every other
    placeholder with guillemets (U5 review M2)."""
    assert denckring.render_hint(
        "consonantal_lipogram", "{forbidden}", lang=lang, forbidden="st"
    ) == (expected)


def test_a_hint_names_a_letter_as_the_checker_compares_it() -> None:
    """Under `fold_diacritics`, `forbidden="é"` forbids every `e`. A hint stating `é`
    beside its own sentence that `é` counts as `e` contradicted the checker (U5 review
    M3); the letter is shown folded, and shown as given where nothing folds."""
    hint = denckring.prompt_hint("lipogram", lang="fr", forbidden="é")
    assert "« e »" in hint
    assert not denckring.check("lipogram", "le chat", lang="fr", forbidden="é").satisfied
    assert '"e", "t"' in denckring.prompt_hint("consonantal_lipogram", forbidden="ÉtE")
    unfolded = denckring.prompt_hint("lipogram", lang="de", forbidden="ä", fold_diacritics=False)
    assert "„ä“" in unfolded
