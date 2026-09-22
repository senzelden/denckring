"""Occurrence-aligned dictionary relations; no unknown token is silently waived."""

from __future__ import annotations

from typing import Literal, cast

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import LanguagePack, LexicalRelations, Report, Violation


def relation_report(
    procedure: BaseProcedure[SourceParams],
    text: str,
    pack: LanguagePack,
    params: SourceParams,
    relation: Literal["synonyms", "antonyms"],
) -> Report:
    source, candidate = pack.word_spans(params.source), pack.word_spans(text)
    lookup = getattr(cast(LexicalRelations, pack), relation)
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
        elif index >= len(candidate) or candidate[index][1].casefold() not in targets:
            violations.append(
                Violation(
                    rule="wrong_relation",
                    offset=offset,
                    found=candidate[index][1] if index < len(candidate) else "",
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
