"""Field-level accuracy against ground truth, and how well the review queue catches errors."""

from __future__ import annotations

from dataclasses import dataclass, field

from .schema import FIELDS, ExtractionResult, Invoice


def _same(field_name: str, got, expected) -> bool:
    if got is None or expected is None:
        return got is None and expected is None
    if isinstance(got, str) and isinstance(expected, str):
        return got.casefold().split() == expected.casefold().split()
    return got == expected


@dataclass
class DocScore:
    source: str
    wrong_fields: list[str]
    needs_review: bool

    @property
    def fully_correct(self) -> bool:
        return not self.wrong_fields


@dataclass
class Evaluation:
    docs: list[DocScore] = field(default_factory=list)
    field_correct: dict[str, int] = field(default_factory=lambda: dict.fromkeys(FIELDS, 0))

    @property
    def n(self) -> int:
        return len(self.docs)

    def field_accuracy(self) -> dict[str, float]:
        return {f: (self.field_correct[f] / self.n if self.n else 0.0) for f in FIELDS}

    @property
    def doc_accuracy(self) -> float:
        return sum(d.fully_correct for d in self.docs) / self.n if self.n else 0.0

    @property
    def auto_accepted(self) -> list[DocScore]:
        return [d for d in self.docs if not d.needs_review]

    @property
    def auto_accepted_error_rate(self) -> float:
        """Share of documents NOT sent to review that still contain an error (want ~0)."""
        acc = self.auto_accepted
        return sum(not d.fully_correct for d in acc) / len(acc) if acc else 0.0

    @property
    def errors_caught(self) -> float:
        """Share of documents with any wrong field that the review queue flagged."""
        wrong = [d for d in self.docs if not d.fully_correct]
        return sum(d.needs_review for d in wrong) / len(wrong) if wrong else 1.0


def evaluate(results: list[ExtractionResult], truths: dict[str, Invoice]) -> Evaluation:
    ev = Evaluation()
    for res in results:
        truth = truths[res.source]
        wrong = []
        for f in FIELDS:
            if _same(f, getattr(res.invoice, f), getattr(truth, f)):
                ev.field_correct[f] += 1
            else:
                wrong.append(f)
        ev.docs.append(DocScore(res.source, wrong, res.needs_review))
    return ev
