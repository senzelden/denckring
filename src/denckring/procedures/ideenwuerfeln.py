"""Ideenwürfeln — distant excerpts forced together under one headword."""

from __future__ import annotations

import random

from pydantic import Field

from denckring.core import corpus as corpora
from denckring.core.base import ApplyParams, ConstructiveProcedure, SeedParams, SourceParams, plain
from denckring.core.errors import InputTooShort, counted
from denckring.core.protocol import LanguagePack, Produced, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans

MIN_SLOTS = 2
#: How the parts of a throw are written when it is checked or produced.
SEPARATOR = "\n"


class IdeenwuerfelnParams(SourceParams):
    slots: int = Field(default=3, ge=MIN_SLOTS, description="Excerpts per throw.")
    headword: str | None = Field(
        default=None, description="Draw only from entries filed under this word."
    )
    distinct_domains: bool = Field(
        default=False,
        description="Every excerpt must come from a different field.",
    )


class IdeenwuerfelnApplyParams(IdeenwuerfelnParams, SeedParams, ApplyParams):
    pass


@register
class Ideenwuerfeln(ConstructiveProcedure[IdeenwuerfelnParams, IdeenwuerfelnApplyParams]):
    """Jean Paul's throw of the dice, reconstructed from the notebook.

    The rule is not his. He titled a notebook *Ideenwürfeln* in February 1795 and
    left a structure in it — headwords indexing his excerpt books, with pointers
    into them and an occasional mark against what deserved working up — but he
    never wrote the procedure down. Everything here is inferred from the object,
    which is why the catalogue row says `reconstruction`.

    **What this produces is a collision, not a text.** The step that matters —
    forcing remote materials together until a likeness appears, the *Witz* of the
    Vorschule der Ästhetik — is exactly what no program does. The checker
    verifies provenance and distinctness and stops there, and the catalogue row
    says so rather than implying the machine writes.

    The corpus arrives through `source`, as JSON or as one excerpt per line. None
    travels with the package: the excerpt books are public domain, but the
    transcriptions that make them usable are scholarly editions with their own
    rights, and a reader supplies their own.
    """

    id = "ideenwuerfeln"

    @classmethod
    def params_model(cls) -> type[IdeenwuerfelnParams]:
        return IdeenwuerfelnParams

    def _check(self, text: str, pack: LanguagePack, params: IdeenwuerfelnParams) -> Report:
        corpus = corpora.parse(params.source)
        available = corpus.entries(params.headword)
        by_text = {entry.text.strip(): entry for entry in corpus.entries()}
        thrown = [line.strip() for _, line in line_spans(text)]
        under_headword = {entry.text.strip() for entry in available}

        violations: list[Violation] = []
        drawn = []
        for offset, part in line_spans(text):
            body = part.strip()
            entry = by_text.get(body)
            if entry is None:
                violations.append(
                    Violation(
                        rule="not_in_the_corpus",
                        offset=offset,
                        found=body[:60],
                        expected="an excerpt the corpus holds",
                    )
                )
                continue
            drawn.append(entry)
            if params.headword and body not in under_headword:
                violations.append(
                    Violation(
                        rule="wrong_headword",
                        offset=offset,
                        found=body[:60],
                        expected=f"an excerpt filed under {params.headword!r}",
                    )
                )

        if len(thrown) != params.slots:
            violations.append(
                Violation(
                    rule="wrong_number_of_excerpts",
                    offset=None,
                    found=f"{len(thrown)} excerpts",
                    expected=f"{params.slots} excerpts",
                )
            )

        if params.distinct_domains:
            seen: set[str] = set()
            for entry in drawn:
                if entry.domain is None:
                    violations.append(
                        Violation(
                            rule="domain_unknown",
                            offset=None,
                            found=entry.id or entry.text[:40],
                            expected="an excerpt whose field is recorded",
                        )
                    )
                elif entry.domain in seen:
                    violations.append(
                        Violation(
                            rule="domain_repeated",
                            offset=None,
                            found=entry.domain,
                            expected="a field not already drawn from",
                        )
                    )
                else:
                    seen.add(entry.domain)

        checks = max(len(thrown), params.slots) + 1
        return self._report(
            good=max(checks - len(violations), 0),
            total=checks,
            violations=violations,
            metrics={
                "excerpts": float(len(thrown)),
                "pool": float(len(available)),
                "corpus": float(len(corpus.entries())),
            },
        )

    @classmethod
    def apply_params_model(cls) -> type[IdeenwuerfelnApplyParams]:
        return IdeenwuerfelnApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: IdeenwuerfelnApplyParams) -> Produced:
        """Throw. `text` is the corpus: a second `source` is refused rather
        than accepted alongside it, the same rule `parse_apply_params` enforces
        for every generator whose params model carries a `source` field.

        Falls back to the whole stock when a headword's pool is too small for the
        number of slots, and there is no way to signal that through a string
        return — so a caller who needs to know should check the pool size first.
        """
        corpus = corpora.parse(params.source)
        pool = corpus.entries(params.headword)
        if len(pool) < params.slots:
            pool = corpus.entries()
        if len(pool) < params.slots:
            # `InputTooShort`, not `MalformedCorpus`: a corpus of two slips is
            # perfectly well formed and simply holds fewer entries than a throw
            # of three needs, which is the shape `recombination` and
            # `spoonerism` raise `InputTooShort` for. `MalformedCorpus` keeps
            # what `corpus.parse` raises it for — empty, unparseable, or missing
            # the key that says where the entries are.
            raise InputTooShort(
                self.id,
                needed=f"at least {counted(params.slots, 'entry', 'entries')} to throw",
                found=counted(len(pool), "entry", "entries"),
            )
        chooser = random.Random(params.seed)
        if params.distinct_domains:
            by_domain: dict[str | None, list[corpora.Entry]] = {}
            for entry in pool:
                by_domain.setdefault(entry.domain, []).append(entry)
            domains = [d for d in by_domain if d is not None]
            if len(domains) >= params.slots:
                picked = [
                    chooser.choice(by_domain[domain])
                    for domain in chooser.sample(domains, params.slots)
                ]
                return plain([SEPARATOR.join(entry.text.strip() for entry in picked)])
        return plain(
            [SEPARATOR.join(entry.text.strip() for entry in chooser.sample(pool, params.slots))]
        )
