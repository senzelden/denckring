"""Occurrence-aligned dictionary relations; no unknown token is silently waived."""

from __future__ import annotations

from typing import Literal

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.errors import MissingCapability
from denckring.core.protocol import LanguagePack, Report, Violation


def relation_report(
    procedure: BaseProcedure[SourceParams],
    text: str,
    pack: LanguagePack,
    params: SourceParams,
    relation: Literal["synonyms", "antonyms"],
) -> Report:
    source, candidate = pack.word_spans(params.source), pack.word_spans(text)
    # `LexicalRelations` is optional and not part of the stable `LanguagePack`
    # contract (protocol.py), so a pack can legally declare the capability in
    # `capabilities` without implementing the method. A three-arg `getattr`
    # turns that mismatch into the same `MissingCapability` a caller would get
    # from a pack that never claimed the capability, instead of a bare
    # `AttributeError` escaping uncaught (core/errors.py: no error is silent).
    lookup = getattr(pack, relation, None)
    if lookup is None:
        raise MissingCapability(procedure.id, pack.lang, f"lexicon.{relation}")
    violations: list[Violation] = []
    good = unknown = 0
    for index, (offset, word) in enumerate(source):
        targets = lookup(word)
        if not targets:
            unknown += 1
            violations.append(
                Violation(
                    rule="unknown_relation",
                    offset=offset,
                    found=word,
                    expected=f"a supported {relation} relation",
                )
            )
        elif index >= len(candidate):
            # Covered once by the trailing `wrong_word_count` violation below;
            # a `wrong_relation` entry per out-of-range index would double-count
            # a single short-candidate defect as N+1 violations.
            pass
        elif candidate[index][1].casefold() not in targets:
            violations.append(
                Violation(
                    rule="wrong_relation",
                    offset=offset,
                    found=candidate[index][1],
                    expected=f"a dictionary {relation} replacement for {word}",
                )
            )
        else:
            good += 1
    if len(source) != len(candidate):
        violations.append(
            Violation(rule="wrong_word_count", found=str(len(candidate)), expected=str(len(source)))
        )
    if not source:
        violations.append(Violation(rule="empty_source", found="", expected="at least one token"))
    return procedure._report(
        good=good,
        total=max(len(source), len(candidate), 1),
        violations=violations,
        metrics={"source_words": float(len(source)), "unknown_words": float(unknown)},
    )
