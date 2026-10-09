import csv
import json
import subprocess
import sys

import pytest

from reteval import __version__
from reteval.cli import main


def evaluate(qrels, *runs, extra=()):
    args = ["evaluate", "--qrels", str(qrels), "--resamples", "200"]
    for spec in runs:
        args += ["--run", spec]
    return main([*args, *extra])


def test_metrics_command_lists_metrics(capsys):
    assert main(["metrics"]) == 0
    out = capsys.readouterr().out
    assert "ndcg" in out
    assert "@k" in out


def test_evaluate_prints_markdown(capsys, qrels_file, run_a_file, run_b_file):
    code = evaluate(
        qrels_file,
        f"A={run_a_file}",
        f"B={run_b_file}",
        extra=["--metrics", "mrr", "recall@3", "--baseline", "B"],
    )

    out = capsys.readouterr().out
    assert code == 0
    assert "| A | 1 | 0.7500 | 0.8333 |" in out
    assert "| B | 1 | 0.3333 | 0.6667 |" in out
    assert "| A | MRR | +0.4167 |" in out


def test_glob_pattern_collects_repeated_runs(capsys, write, qrels_file):
    write("runs/dense.seed1.run", "q1 Q0 d1 1 1.0 x\nq2 Q0 d2 1 1.0 x\n")
    write("runs/dense.seed2.run", "q1 Q0 d3 1 1.0 x\nq2 Q0 d2 1 1.0 x\n")
    pattern = qrels_file.parent / "runs" / "dense.seed*.run"

    assert evaluate(qrels_file, f"dense={pattern}", extra=["--metrics", "mrr"]) == 0
    assert "| dense | 2 | 1.0000 ± 0.0000 |" in capsys.readouterr().out


def test_system_name_defaults_to_file_stem(capsys, qrels_file, run_a_file):
    assert evaluate(qrels_file, str(run_a_file)) == 0
    assert "| a | 1 |" in capsys.readouterr().out


def test_writes_report_per_query_scores_and_chart(tmp_path, qrels_file, run_a_file, run_b_file):
    # outputs go to folders that do not exist yet
    out, per_query, chart = (tmp_path / "out" / name for name in ("r.json", "pq.csv", "r.png"))
    code = evaluate(
        qrels_file,
        f"A={run_a_file}",
        f"B={run_b_file}",
        extra=[
            *("--format", "json", "-o", str(out)),
            *("--per-query", str(per_query), "--plot", str(chart)),
        ],
    )

    assert code == 0
    assert json.loads(out.read_text(encoding="utf-8"))["systems"] == ["A", "B"]
    rows = list(csv.DictReader(per_query.open(encoding="utf-8")))
    assert {row["query_id"] for row in rows} == {"q1", "q2"}
    assert chart.read_bytes().startswith(b"\x89PNG")


def test_csv_format(capsys, qrels_file, run_a_file):
    assert evaluate(qrels_file, f"A={run_a_file}", extra=["--format", "csv"]) == 0
    assert capsys.readouterr().out.startswith("system,metric,runs,mean,std")


def test_warns_about_missing_queries(capsys, write, qrels_file):
    partial = write("partial.run", "q1 Q0 d1 1 1.0 x\n")

    assert evaluate(qrels_file, f"P={partial}") == 0
    assert "1 of 2 queries are missing" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("runs", "extra", "message"),
    [
        (["A={run_a}"], ["--metrics", "bleu"], "unknown metric"),
        (["A={missing}"], [], "no run files match"),
        (["=x"], [], "invalid --run value"),
        (["A={run_a}"], ["--baseline", "B"], "baseline 'B'"),
        (["A={run_a}"], ["--min-rel", "0"], "min_rel"),
    ],
)
def test_errors_are_reported_without_traceback(
    capsys, tmp_path, qrels_file, run_a_file, runs, extra, message
):
    specs = [r.format(run_a=run_a_file, missing=tmp_path / "nope.run") for r in runs]

    assert evaluate(qrels_file, *specs, extra=extra) == 1
    err = capsys.readouterr().err
    assert err.startswith("reteval: error:")
    assert message in err


def test_missing_qrels_file(capsys, tmp_path, run_a_file):
    assert evaluate(tmp_path / "missing.txt", f"A={run_a_file}") == 1
    assert "reteval: error:" in capsys.readouterr().err


def test_usage_errors_exit_with_code_2():
    with pytest.raises(SystemExit) as exc:
        main(["evaluate", "--run", "a.run"])
    assert exc.value.code == 2


def test_module_entry_point():
    result = subprocess.run(
        [sys.executable, "-m", "reteval", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == f"reteval {__version__}"
