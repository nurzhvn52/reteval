import csv
import io
import json

import numpy as np
import pytest

from reteval.evaluation import RunScores, System
from reteval.report import build_report, per_query_csv, to_csv, to_json, to_markdown

QUERIES = ("q1", "q2", "q3")


def run(label: str, *values: float) -> RunScores:
    return RunScores(QUERIES, {"MRR": np.array(values)}, label=label)


@pytest.fixture
def systems() -> list[System]:
    # "a" has two runs with means 0.8333 and 1.0; "b" has one run with mean 0.4167.
    a = System("a", (run("a1", 1.0, 0.5, 1.0), run("a2", 1.0, 1.0, 1.0)))
    b = System("b", (run("b1", 0.5, 0.5, 0.25),))
    return [a, b]


def test_summary_without_baseline(systems):
    report = build_report(systems, ["MRR"])

    row = report.row("a", "MRR")
    assert row.runs == 2
    assert row.mean == pytest.approx(11 / 12)
    assert row.std == pytest.approx((1 / 6) / np.sqrt(2))
    assert row.delta is None
    assert report.n_queries == 3


def test_comparison_with_baseline(systems):
    report = build_report(systems, ["MRR"], baseline="b", n_resamples=500)

    a, b = report.row("a", "MRR"), report.row("b", "MRR")
    assert a.delta == pytest.approx(a.mean - b.mean)
    assert a.ci_low <= a.delta <= a.ci_high
    assert 0 < a.p_value <= 1
    assert b.delta is None


def test_report_is_reproducible(systems):
    first = build_report(systems, ["MRR"], baseline="b", n_resamples=300, seed=5)
    second = build_report(systems, ["MRR"], baseline="b", n_resamples=300, seed=5)
    assert first == second


def test_unknown_row_raises(systems):
    with pytest.raises(KeyError):
        build_report(systems, ["MRR"]).row("c", "MRR")


def test_unknown_baseline_raises(systems):
    with pytest.raises(ValueError, match="baseline 'bm25' is not one of the systems: a, b"):
        build_report(systems, ["MRR"], baseline="bm25")


def test_invalid_system_sets_raise(systems):
    with pytest.raises(ValueError, match="no systems"):
        build_report([], ["MRR"])
    with pytest.raises(ValueError, match="unique"):
        build_report([systems[0], systems[0]], ["MRR"])
    other = System("c", (RunScores(("x",), {"MRR": np.array([1.0])}),))
    with pytest.raises(ValueError, match="same queries"):
        build_report([systems[0], other], ["MRR"])


def test_markdown(systems):
    text = to_markdown(build_report(systems, ["MRR"], baseline="b", n_resamples=200))

    assert "| a | 2 | 0.9167 ± 0.1179 |" in text
    assert "| b | 1 | 0.4167 |" in text
    assert "## Comparison with baseline `b`" in text
    assert "| a | MRR | +0.5000 |" in text


def test_markdown_without_baseline_has_no_comparison(systems):
    assert "Comparison" not in to_markdown(build_report(systems, ["MRR"]))


def test_csv(systems):
    rows = list(csv.DictReader(io.StringIO(to_csv(build_report(systems, ["MRR"], baseline="b")))))

    assert [row["system"] for row in rows] == ["a", "b"]
    assert float(rows[0]["delta"]) == pytest.approx(0.5)
    assert rows[1]["delta"] == ""


def test_json(systems):
    data = json.loads(to_json(build_report(systems, ["MRR"], baseline="b", n_resamples=100)))

    assert data["baseline"] == "b"
    assert data["n_resamples"] == 100
    assert len(data["rows"]) == 2


def test_per_query_csv(systems):
    rows = list(csv.reader(io.StringIO(per_query_csv(systems))))

    assert rows[0] == ["system", "run", "query_id", "metric", "value"]
    assert len(rows) == 1 + 3 * 3
    assert ["a", "a1", "q2", "MRR", "0.500000"] in rows
