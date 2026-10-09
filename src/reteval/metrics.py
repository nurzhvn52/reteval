"""Ranking metrics for a single query.

Every metric takes the ranking (document ids, best first), the judgements for the
query (document id -> grade) and an optional cutoff ``k``; ``k=None`` means the whole
ranking. A document is relevant when its grade is at least ``min_rel``. Only nDCG uses
the grades themselves, with linear gain (gain = grade) and a log2(rank + 1) discount.

A query without relevant documents has no meaningful score: the functions return 0.0
for it, and :func:`reteval.evaluation.evaluate_run` leaves such queries out.
"""

import math
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass

Ranking = Sequence[str]
Judgements = Mapping[str, int]
MetricFn = Callable[[Ranking, Judgements, int | None, int], float]


def _relevant(judgements: Judgements, min_rel: int) -> set[str]:
    return {doc for doc, grade in judgements.items() if grade >= min_rel}


def precision(
    ranking: Ranking, judgements: Judgements, k: int | None = None, min_rel: int = 1
) -> float:
    """Share of the top-k documents that are relevant (P@k).

    The denominator is k even if fewer than k documents were retrieved, so a short
    ranking is not rewarded.
    """
    depth = len(ranking) if k is None else k
    if depth == 0:
        return 0.0
    relevant = _relevant(judgements, min_rel)
    return sum(doc in relevant for doc in ranking[:depth]) / depth


def recall(
    ranking: Ranking, judgements: Judgements, k: int | None = None, min_rel: int = 1
) -> float:
    """Share of all relevant documents that appear in the top k (Recall@k)."""
    relevant = _relevant(judgements, min_rel)
    if not relevant:
        return 0.0
    return sum(doc in relevant for doc in ranking[:k]) / len(relevant)


def reciprocal_rank(
    ranking: Ranking, judgements: Judgements, k: int | None = None, min_rel: int = 1
) -> float:
    """1 / rank of the first relevant document in the top k, or 0 if there is none."""
    relevant = _relevant(judgements, min_rel)
    for rank, doc in enumerate(ranking[:k], start=1):
        if doc in relevant:
            return 1.0 / rank
    return 0.0


def average_precision(
    ranking: Ranking, judgements: Judgements, k: int | None = None, min_rel: int = 1
) -> float:
    """Mean of P@i over the ranks i of relevant documents in the top k.

    Relevant documents that were not retrieved contribute 0, i.e. the sum is divided
    by the total number of relevant documents.
    """
    relevant = _relevant(judgements, min_rel)
    if not relevant:
        return 0.0
    hits = 0
    total = 0.0
    for rank, doc in enumerate(ranking[:k], start=1):
        if doc in relevant:
            hits += 1
            total += hits / rank
    return total / len(relevant)


def _dcg(gains: Iterable[int]) -> float:
    return sum(gain / math.log2(rank + 1) for rank, gain in enumerate(gains, start=1))


def ndcg(ranking: Ranking, judgements: Judgements, k: int | None = None, min_rel: int = 1) -> float:
    """Normalised discounted cumulative gain with graded relevance (nDCG@k)."""

    def gain(grade: int) -> int:
        return grade if grade >= min_rel else 0

    ideal_dcg = _dcg(sorted((gain(g) for g in judgements.values()), reverse=True)[:k])
    if ideal_dcg == 0:
        return 0.0
    return _dcg(gain(judgements.get(doc, 0)) for doc in ranking[:k]) / ideal_dcg


def hit_rate(
    ranking: Ranking, judgements: Judgements, k: int | None = None, min_rel: int = 1
) -> float:
    """1 if at least one relevant document is in the top k, otherwise 0 (Hit@k)."""
    relevant = _relevant(judgements, min_rel)
    return float(any(doc in relevant for doc in ranking[:k]))


@dataclass(frozen=True)
class Metric:
    """A metric with a fixed cutoff, e.g. ``nDCG@10``."""

    label: str
    fn: MetricFn
    k: int | None = None

    @property
    def name(self) -> str:
        return self.label if self.k is None else f"{self.label}@{self.k}"

    def __call__(self, ranking: Ranking, judgements: Judgements, min_rel: int = 1) -> float:
        return self.fn(ranking, judgements, self.k, min_rel)


_REGISTRY: dict[str, tuple[str, MetricFn, str]] = {
    "p": ("P", precision, "precision: share of relevant documents in the top k"),
    "recall": ("Recall", recall, "share of all relevant documents found in the top k"),
    "mrr": ("MRR", reciprocal_rank, "reciprocal rank of the first relevant document"),
    "map": ("MAP", average_precision, "average precision over the ranks of relevant documents"),
    "ndcg": ("nDCG", ndcg, "normalised discounted cumulative gain, uses graded relevance"),
    "hit": ("Hit", hit_rate, "1 if at least one relevant document is in the top k"),
}
_ALIASES = {"precision": "p", "r": "recall", "rr": "mrr", "ap": "map", "success": "hit"}
_CUTOFF = re.compile(r"[1-9][0-9]*")


def parse_metric(spec: str) -> Metric:
    """Parse ``name`` or ``name@k`` (case-insensitive), e.g. ``ndcg@10`` or ``MAP``."""
    base, sep, cutoff = spec.strip().lower().partition("@")
    base = _ALIASES.get(base, base)
    if base not in _REGISTRY:
        known = ", ".join(_REGISTRY)
        raise ValueError(f"unknown metric {spec!r}; supported metrics: {known}")
    k = None
    if sep:
        if not _CUTOFF.fullmatch(cutoff):
            raise ValueError(f"cutoff in {spec!r} must be a positive integer")
        k = int(cutoff)
    label, fn, _ = _REGISTRY[base]
    return Metric(label, fn, k)


def available_metrics() -> list[tuple[str, str]]:
    """``(name, description)`` for every supported metric."""
    return [(name, description) for name, (_, _, description) in _REGISTRY.items()]
