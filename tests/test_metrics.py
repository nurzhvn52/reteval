import math

import pytest

from reteval.metrics import (
    available_metrics,
    average_precision,
    hit_rate,
    ndcg,
    parse_metric,
    precision,
    recall,
    reciprocal_rank,
)

# Relevant: d1, d3, d5. Retrieved: d1 (relevant), d2, d3 (relevant), d4.
RANKING = ["d1", "d2", "d3", "d4"]
JUDGEMENTS = {"d1": 1, "d3": 1, "d5": 1, "d2": 0}


def test_precision():
    assert precision(RANKING, JUDGEMENTS, k=1) == 1.0
    assert precision(RANKING, JUDGEMENTS, k=3) == pytest.approx(2 / 3)
    assert precision(RANKING, JUDGEMENTS) == pytest.approx(2 / 4)


def test_precision_divides_by_k_even_for_short_rankings():
    assert precision(["d1"], JUDGEMENTS, k=10) == pytest.approx(0.1)


def test_recall():
    assert recall(RANKING, JUDGEMENTS, k=1) == pytest.approx(1 / 3)
    assert recall(RANKING, JUDGEMENTS, k=3) == pytest.approx(2 / 3)
    assert recall([*RANKING, "d5"], JUDGEMENTS) == 1.0


def test_reciprocal_rank():
    assert reciprocal_rank(RANKING, JUDGEMENTS) == 1.0
    assert reciprocal_rank(["d2", "d4", "d3"], JUDGEMENTS) == pytest.approx(1 / 3)
    assert reciprocal_rank(["d2", "d4", "d3"], JUDGEMENTS, k=2) == 0.0


def test_average_precision_counts_unretrieved_relevant_documents():
    # hits at ranks 1 and 3: (1/1 + 2/3) / 3 relevant documents
    assert average_precision(RANKING, JUDGEMENTS) == pytest.approx((1 + 2 / 3) / 3)
    assert average_precision(RANKING, JUDGEMENTS, k=2) == pytest.approx(1 / 3)


def test_ndcg_binary():
    dcg = 1 / math.log2(2) + 1 / math.log2(4)
    ideal = 1 / math.log2(2) + 1 / math.log2(3) + 1 / math.log2(4)
    assert ndcg(RANKING, JUDGEMENTS, k=3) == pytest.approx(dcg / ideal)


def test_ndcg_uses_graded_relevance():
    judgements = {"a": 2, "b": 1}
    assert ndcg(["a", "b"], judgements) == pytest.approx(1.0)
    # gains 1 and 2 instead of the ideal 2 and 1
    expected = (1 + 2 / math.log2(3)) / (2 + 1 / math.log2(3))
    assert ndcg(["b", "a"], judgements) == pytest.approx(expected)


def test_hit_rate():
    assert hit_rate(RANKING, JUDGEMENTS, k=1) == 1.0
    assert hit_rate(["d2", "d4"], JUDGEMENTS) == 0.0


def test_min_rel_raises_the_relevance_threshold():
    judgements = {"a": 1, "b": 2}
    assert precision(["a", "b"], judgements, min_rel=2) == 0.5
    assert reciprocal_rank(["a", "b"], judgements, min_rel=2) == 0.5
    assert ndcg(["b", "a"], judgements, min_rel=2) == 1.0


@pytest.mark.parametrize(
    "metric", [precision, recall, reciprocal_rank, average_precision, ndcg, hit_rate]
)
def test_degenerate_inputs_score_zero(metric):
    assert metric([], JUDGEMENTS) == 0.0
    assert metric(RANKING, {"d1": 0}) == 0.0
    assert metric(RANKING, {}) == 0.0


@pytest.mark.parametrize(
    ("spec", "name", "k"),
    [
        ("ndcg@10", "nDCG@10", 10),
        ("NDCG@10", "nDCG@10", 10),
        ("p@5", "P@5", 5),
        ("precision@5", "P@5", 5),
        ("r@100", "Recall@100", 100),
        ("mrr", "MRR", None),
        ("ap", "MAP", None),
        (" map@1000 ", "MAP@1000", 1000),
        ("success@3", "Hit@3", 3),
    ],
)
def test_parse_metric(spec, name, k):
    metric = parse_metric(spec)
    assert metric.name == name
    assert metric.k == k


def test_parsed_metric_applies_its_cutoff():
    assert parse_metric("p@3")(RANKING, JUDGEMENTS) == pytest.approx(2 / 3)


@pytest.mark.parametrize("spec", ["ndcg@0", "ndcg@", "ndcg@-1", "ndcg@1.5", "ndcg@x", "ndcg@²"])
def test_parse_metric_rejects_bad_cutoffs(spec):
    with pytest.raises(ValueError, match="positive integer"):
        parse_metric(spec)


def test_parse_metric_rejects_unknown_metric():
    with pytest.raises(ValueError, match="unknown metric 'bleu'"):
        parse_metric("bleu")


def test_available_metrics_can_all_be_parsed():
    for name, description in available_metrics():
        assert description
        parse_metric(name)
