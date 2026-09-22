"""Whole-stream similarity of caller-supplied symbols, not verified speech (ADR 0049)."""

from denckring.core.base import BaseProcedure
from denckring.core.bilingual import PronunciationParams, words
from denckring.core.errors import InvalidParams
from denckring.core.phonetics import distance_prepared
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.lang import get_pack


@register
class HomophonicTranslation(BaseProcedure[PronunciationParams]):
    id = "homophonic_translation"

    @classmethod
    def params_model(cls) -> type[PronunciationParams]:
        return PronunciationParams

    def _check(self, text: str, pack: LanguagePack, params: PronunciationParams) -> Report:
        data = params.data
        if pack.lang != data.source_language:
            raise InvalidParams(self.id, "lang must match data.source_language")
        source = words(params.source, pack)
        target = words(text, get_pack(data.target_language))
        violations: list[Violation] = []
        streams: list[list[str]] = []
        for side, tokens, table in (
            ("source", source, data.source_pronunciations),
            ("target", target, data.target_pronunciations),
        ):
            stream: list[str] = []
            for word in tokens:
                if word not in table:
                    violations.append(
                        Violation(
                            rule="unknown_pronunciation",
                            found=word,
                            expected=f"a supplied {side} pronunciation",
                        )
                    )
                else:
                    stream.extend(table[word])
                if len(stream) > 4096:
                    raise InvalidParams(self.id, "at most 4096 symbols per stream are supported")
            if not tokens:
                violations.append(
                    Violation(rule="empty_stream", found=side, expected="at least one word")
                )
            streams.append(stream)
        metrics = {
            "source_symbols": float(len(streams[0])),
            "target_symbols": float(len(streams[1])),
            "unknown_words": float(sum(v.rule == "unknown_pronunciation" for v in violations)),
            "caller_supplied_data": 1.0,
        }
        if not violations:
            distance = distance_prepared(streams[0], streams[1])
            metrics["distance"] = distance
            if distance > params.max_distance:
                violations.append(
                    Violation(
                        rule="sound_distance",
                        found=str(distance),
                        expected=f"distance <= {params.max_distance}",
                    )
                )
        return self._report(
            good=int(not violations), total=1, violations=violations, metrics=metrics
        )
