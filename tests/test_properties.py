"""Property-based tests: invariants that must hold for any ranking and judgements."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from reteval.metrics import (
    average_precision,
    hit_rate,
    ndcg,
    precision,
    recall,
    reciprocal_rank,
)
from reteval.stats import paired_randomization_test

METRICS = [precision, recall, reciprocal_rank, average_precision, ndcg, hit_rate]
DOCS = [f"d{i}" for i in range(30)]

judgements = st.dictionaries(st.sampled_from(DOCS), st.integers(0, 3), min_size=1).filter(
    lambda j: any(grade >= 1 for grade in j.values())
)
rankings = st.lists(st.sampled_from(DOCS), unique=True, max_size=30)
cutoffs = st.one_of(st.none(), st.integers(1, 40))


@given(rankings, judgements, cutoffs)
def test_metrics_lie_between_zero_and_one(ranking, judged, k):
    for metric in METRICS:
        assert 0.0 <= metric(ranking, judged, k) <= 1.0 + 1e-12


@given(judgements)
def test_ideal_ranking_scores_one(judged):
    ideal = sorted(judged, key=lambda doc: -judged[doc])
    for metric in (recall, reciprocal_rank, average_precision, ndcg, hit_rate):
        assert metric(ideal, judged) == pytest.approx(1.0)


@given(rankings, judgements, st.integers(1, 40))
def test_precision_and_recall_count_the_same_hits(ranking, judged, k):
    n_relevant = sum(grade >= 1 for grade in judged.values())
    hits_p = precision(ranking, judged, k) * k
    hits_r = recall(ranking, judged, k) * n_relevant
    assert hits_p == pytest.approx(hits_r)


@given(rankings, judgements, st.integers(1, 39))
def test_recall_does_not_decrease_with_depth(ranking, judged, k):
    assert recall(ranking, judged, k) <= recall(ranking, judged, k + 1)


samples = st.lists(st.floats(0, 1), min_size=1, max_size=40)


@given(samples, st.integers(0, 2**32 - 1))
def test_randomization_test_is_symmetric_and_bounded(values, seed):
    other = [1 - v for v in values]
    p = paired_randomization_test(values, other, n_resamples=200, seed=seed)
    assert 0 < p <= 1
    assert p == paired_randomization_test(other, values, n_resamples=200, seed=seed)
