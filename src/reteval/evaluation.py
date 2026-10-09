"""Per-query evaluation of runs and grouping of repeated runs into systems."""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from reteval.metrics import Metric
from reteval.trec import Qrels, Run

Scores = npt.NDArray[np.float64]


@dataclass(frozen=True)
class RunScores:
    """Per-query scores of one run: ``scores[metric][i]`` belongs to ``query_ids[i]``."""

    query_ids: tuple[str, ...]
    scores: dict[str, Scores]
    #: evaluated queries that are absent from the run; they score 0
    missing_queries: tuple[str, ...] = ()
    label: str = ""


def judged_queries(qrels: Qrels, min_rel: int = 1) -> tuple[str, ...]:
    """Sorted ids of the queries that have at least one relevant document."""
    return tuple(sorted(q for q, docs in qrels.items() if any(g >= min_rel for g in docs.values())))


def evaluate_run(
    run: Run, qrels: Qrels, metrics: Sequence[Metric], min_rel: int = 1, label: str = ""
) -> RunScores:
    """Score a run on every query that has at least one relevant document.

    A query that is missing from the run scores 0 on every metric instead of being
    skipped, so a system cannot raise its average by not answering hard queries.
    """
    if min_rel < 1:
        raise ValueError("min_rel must be at least 1")
    query_ids = judged_queries(qrels, min_rel)
    if not query_ids:
        raise ValueError(f"no query has a document with relevance >= {min_rel}")
    scores = {
        metric.name: np.array(
            [metric(run.get(q, ()), qrels[q], min_rel) for q in query_ids], dtype=np.float64
        )
        for metric in metrics
    }
    missing = tuple(q for q in query_ids if q not in run)
    return RunScores(query_ids, scores, missing, label)


@dataclass(frozen=True)
class System:
    """A retrieval system evaluated over one or more repeated runs (e.g. random seeds)."""

    name: str
    runs: tuple[RunScores, ...]

    def __post_init__(self) -> None:
        if not self.runs:
            raise ValueError(f"system {self.name!r} has no runs")
        if any(run.query_ids != self.runs[0].query_ids for run in self.runs):
            raise ValueError(f"runs of system {self.name!r} were evaluated on different queries")

    @property
    def query_ids(self) -> tuple[str, ...]:
        return self.runs[0].query_ids

    def run_means(self, metric: str) -> Scores:
        """Mean over queries, one value per run."""
        return np.array([run.scores[metric].mean() for run in self.runs], dtype=np.float64)

    def per_query(self, metric: str) -> Scores:
        """Score of every query averaged over the runs."""
        return np.mean([run.scores[metric] for run in self.runs], axis=0)
