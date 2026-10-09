"""Result tables: a summary per system and a comparison with a baseline."""

import csv
import io
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace

from reteval.evaluation import System
from reteval.stats import bootstrap_ci, paired_randomization_test, summarize


@dataclass(frozen=True)
class Row:
    """One system on one metric. Comparison fields are ``None`` for the baseline."""

    system: str
    metric: str
    runs: int
    mean: float
    std: float
    delta: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    p_value: float | None = None


@dataclass(frozen=True)
class Report:
    systems: tuple[str, ...]
    metrics: tuple[str, ...]
    rows: tuple[Row, ...]
    n_queries: int
    min_rel: int
    baseline: str | None
    n_resamples: int
    seed: int

    def row(self, system: str, metric: str) -> Row:
        for row in self.rows:
            if row.system == system and row.metric == metric:
                return row
        raise KeyError((system, metric))


def build_report(
    systems: Sequence[System],
    metrics: Sequence[str],
    *,
    baseline: str | None = None,
    min_rel: int = 1,
    n_resamples: int = 10_000,
    seed: int = 0,
) -> Report:
    """Summarise every system and, if a baseline is given, compare the others with it."""
    names = [system.name for system in systems]
    if not systems:
        raise ValueError("no systems to report")
    if len(set(names)) != len(names):
        raise ValueError(f"system names must be unique, got {names}")
    if any(system.query_ids != systems[0].query_ids for system in systems):
        raise ValueError("all systems must be evaluated on the same queries")
    if baseline is not None and baseline not in names:
        raise ValueError(f"baseline {baseline!r} is not one of the systems: {', '.join(names)}")

    base = next((system for system in systems if system.name == baseline), None)
    rows = []
    for system in systems:
        for metric in metrics:
            summary = summarize(system.run_means(metric))
            row = Row(system.name, metric, summary.n, summary.mean, summary.std)
            if base is not None and system is not base:
                ours, theirs = system.per_query(metric), base.per_query(metric)
                low, high = bootstrap_ci(ours - theirs, n_resamples=n_resamples, seed=seed)
                row = replace(
                    row,
                    delta=float((ours - theirs).mean()),
                    ci_low=low,
                    ci_high=high,
                    p_value=paired_randomization_test(ours, theirs, n_resamples, seed),
                )
            rows.append(row)
    return Report(
        systems=tuple(names),
        metrics=tuple(metrics),
        rows=tuple(rows),
        n_queries=len(systems[0].query_ids),
        min_rel=min_rel,
        baseline=baseline,
        n_resamples=n_resamples,
        seed=seed,
    )


def _table(header: Sequence[str], body: Sequence[Sequence[str]], numeric_from: int) -> list[str]:
    align = ["---" if i < numeric_from else "---:" for i in range(len(header))]
    return [f"| {' | '.join(cells)} |" for cells in (header, align, *body)]


def to_markdown(report: Report) -> str:
    def cell(row: Row) -> str:
        return f"{row.mean:.4f}" if row.runs == 1 else f"{row.mean:.4f} ± {row.std:.4f}"

    lines = [
        "## Effectiveness",
        "",
        f"Mean over {report.n_queries} queries with at least one document of relevance "
        f">= {report.min_rel}. For systems with several runs, ± is the standard deviation "
        "of the run means.",
        "",
        *_table(
            ["System", "Runs", *report.metrics],
            [
                [name, str(report.row(name, report.metrics[0]).runs)]
                + [cell(report.row(name, metric)) for metric in report.metrics]
                for name in report.systems
            ],
            numeric_from=1,
        ),
    ]
    if report.baseline is not None:
        lines += [
            "",
            f"## Comparison with baseline `{report.baseline}`",
            "",
            "Difference is the mean per-query difference to the baseline, the 95% CI is a "
            "percentile bootstrap over queries, and p is from a two-sided paired "
            f"randomization test ({report.n_resamples} resamples, seed {report.seed}).",
            "",
            *_table(
                ["System", "Metric", "Difference", "95% CI", "p"],
                [
                    [
                        row.system,
                        row.metric,
                        f"{row.delta:+.4f}",
                        f"[{row.ci_low:+.4f}, {row.ci_high:+.4f}]",
                        f"{row.p_value:.4f}",
                    ]
                    for row in report.rows
                    if row.delta is not None
                ],
                numeric_from=2,
            ),
        ]
    return "\n".join(lines) + "\n"


def to_csv(report: Report) -> str:
    buffer = io.StringIO()
    fields = list(Row.__dataclass_fields__)
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in report.rows:
        writer.writerow(asdict(row))
    return buffer.getvalue()


def to_json(report: Report) -> str:
    return json.dumps(asdict(report), indent=2) + "\n"


def per_query_csv(systems: Sequence[System]) -> str:
    """Long-format per-query scores (system, run, query, metric, value) for error analysis."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["system", "run", "query_id", "metric", "value"])
    for system in systems:
        for run in system.runs:
            for metric, values in run.scores.items():
                for qid, value in zip(run.query_ids, values, strict=True):
                    writer.writerow([system.name, run.label, qid, metric, f"{value:.6f}"])
    return buffer.getvalue()


RENDERERS = {"markdown": to_markdown, "csv": to_csv, "json": to_json}
