"""Ordered target-language gloss expansion against supplied data (ADR 0049)."""

from denckring.core.base import BaseProcedure
from denckring.core.bilingual import GlossParams, words
from denckring.core.errors import InvalidParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.lang import get_pack


@register
class DefinitionalTranslation(BaseProcedure[GlossParams]):
    id = "definitional_translation"

    @classmethod
    def params_model(cls) -> type[GlossParams]:
        return GlossParams

    def _check(self, text: str, pack: LanguagePack, params: GlossParams) -> Report:
        data = params.data
        if pack.lang != data.source_language:
            raise InvalidParams(self.id, "lang must match data.source_language")
        target_pack = get_pack(data.target_language)
        source, candidate = words(params.source, pack), words(text, target_pack)
        if max(len(source), len(candidate)) > 4096:
            raise InvalidParams(self.id, "at most 4096 tokens per text are supported")
        unknown = [word for word in source if word not in data.glosses]
        violations = [
            Violation(rule="unknown_gloss", found=word, expected="a supplied target-language gloss")
            for word in unknown
        ]
        if not source:
            violations.append(
                Violation(rule="empty_source", found="", expected="at least one word")
            )
        if not violations:
            # Keep every reachable boundary: choosing the shortest/first gloss
            # greedily rejects valid ambiguous-prefix segmentations.
            reachable = {0}
            for word in source:
                alternatives = [words(gloss, target_pack) for gloss in data.glosses[word]]
                reachable = {
                    start + len(gloss)
                    for start in reachable
                    for gloss in alternatives
                    if candidate[start : start + len(gloss)] == gloss
                }
                if not reachable:
                    break
            if len(candidate) not in reachable:
                violations.append(
                    Violation(
                        rule="not_the_gloss_sequence",
                        found=text,
                        expected="one ordered gloss per source occurrence, with no extra words",
                    )
                )
        return self._report(
            good=int(not violations),
            total=1,
            violations=violations,
            metrics={
                "source_words": float(len(source)),
                "unknown_words": float(len(unknown)),
                "caller_supplied_data": 1.0,
            },
        )
