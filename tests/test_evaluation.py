import numpy as np
import pytest

from reteval.evaluation import RunScores, System, evaluate_run, judged_queries
from reteval.metrics import parse_metric
from reteval.trec import read_qrels, read_run

MRR = parse_metric("mrr")
RECALL3 = parse_metric("recall@3")


def test_judged_queries_skip_queries_without_relevant_documents(qrels_file):
    qrels = read_qrels(qrels_file)
    assert judged_queries(qrels) == ("q1", "q2")
    assert judged_queries(qrels, min_rel=2) == ("q1",)


def test_evaluate_run(qrels_file, run_a_file):
    scores = evaluate_run(read_run(run_a_file), read_qrels(qrels_file), [MRR, RECALL3])

    assert scores.query_ids == ("q1", "q2")
    np.testing.assert_allclose(scores.scores["MRR"], [1.0, 0.5])
    np.testing.assert_allclose(scores.scores["Recall@3"], [2 / 3, 1.0])
    assert scores.missing_queries == ()


def test_queries_missing_from_the_run_score_zero(qrels_file):
    scores = evaluate_run({"q1": ["d1"]}, read_qrels(qrels_file), [MRR])

    assert scores.missing_queries == ("q2",)
    np.testing.assert_allclose(scores.scores["MRR"], [1.0, 0.0])


def test_min_rel_changes_relevance_and_query_set(qrels_file):
    scores = evaluate_run({"q1": ["d3", "d1"]}, read_qrels(qrels_file), [MRR], min_rel=2)

    assert scores.query_ids == ("q1",)
    np.testing.assert_allclose(scores.scores["MRR"], [0.5])


def test_min_rel_must_be_positive(qrels_file):
    with pytest.raises(ValueError, match="at least 1"):
        evaluate_run({}, read_qrels(qrels_file), [MRR], min_rel=0)


def test_qrels_without_relevant_documents_are_rejected(qrels_file):
    with pytest.raises(ValueError, match="relevance >= 3"):
        evaluate_run({}, read_qrels(qrels_file), [MRR], min_rel=3)


def run_scores(*values: float) -> RunScores:
    query_ids = tuple(f"q{i}" for i in range(len(values)))
    return RunScores(query_ids, {"MRR": np.array(values)})


def test_system_aggregates_repeated_runs():
    system = System("dense", (run_scores(1.0, 0.5), run_scores(0.5, 0.5)))

    np.testing.assert_allclose(system.run_means("MRR"), [0.75, 0.5])
    np.testing.assert_allclose(system.per_query("MRR"), [0.75, 0.5])
    assert system.query_ids == ("q0", "q1")


def test_system_needs_at_least_one_run():
    with pytest.raises(ValueError, match="no runs"):
        System("empty", ())


def test_system_runs_must_share_queries():
    with pytest.raises(ValueError, match="different queries"):
        System("dense", (run_scores(1.0, 0.5), run_scores(1.0)))
