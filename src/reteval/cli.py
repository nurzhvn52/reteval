"""Command-line interface: ``reteval evaluate`` and ``reteval metrics``."""

import argparse
import glob
import sys
from collections.abc import Sequence
from pathlib import Path

from reteval import __version__
from reteval.evaluation import System, evaluate_run
from reteval.metrics import Metric, available_metrics, parse_metric
from reteval.report import RENDERERS, build_report, per_query_csv
from reteval.trec import read_qrels, read_run

DEFAULT_METRICS = ("ndcg@10", "recall@10", "mrr@10", "map")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reteval",
        description="Evaluate ranked retrieval runs against relevance judgements.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    evaluate = commands.add_parser(
        "evaluate",
        help="compute metrics for one or more systems",
        description="Compute metrics for one or more systems and compare them with a baseline.",
    )
    evaluate.add_argument(
        "--qrels", required=True, type=Path, help="relevance judgements in TREC qrels format"
    )
    evaluate.add_argument(
        "--run",
        dest="runs",
        action="append",
        required=True,
        metavar="NAME=PATTERN",
        help="system name and a run file or glob pattern, one file per repeated run "
        "(e.g. dense=runs/dense.seed*.run); repeat the option for every system",
    )
    evaluate.add_argument(
        "--metrics",
        nargs="+",
        default=list(DEFAULT_METRICS),
        metavar="METRIC",
        help="metrics such as ndcg@10, recall@100, mrr, map (default: %(default)s)",
    )
    evaluate.add_argument("--baseline", metavar="NAME", help="compare other systems with this one")
    evaluate.add_argument(
        "--min-rel", type=int, default=1, help="lowest grade that counts as relevant (default: 1)"
    )
    evaluate.add_argument(
        "--resamples",
        type=int,
        default=10_000,
        help="resamples for the randomization test and bootstrap (default: %(default)s)",
    )
    evaluate.add_argument(
        "--seed", type=int, default=0, help="random seed of the statistics (default: 0)"
    )
    evaluate.add_argument("--format", choices=sorted(RENDERERS), default="markdown")
    evaluate.add_argument(
        "-o", "--output", type=Path, help="write the report to a file instead of stdout"
    )
    evaluate.add_argument(
        "--per-query", type=Path, metavar="CSV", help="also write per-query scores to a CSV file"
    )
    evaluate.add_argument("--plot", type=Path, metavar="IMAGE", help="also save a bar chart")

    commands.add_parser("metrics", help="list supported metrics")
    return parser


def _parse_run_spec(spec: str) -> tuple[str, list[Path]]:
    """``name=pattern`` -> (name, matching files); without ``name=`` the file stem is used."""
    name, sep, pattern = spec.partition("=")
    if not sep:
        name, pattern = Path(spec).stem, spec
    if not name or not pattern:
        raise ValueError(f"invalid --run value {spec!r}, expected NAME=PATTERN")
    paths = sorted(Path(p) for p in glob.glob(pattern))
    if not paths:
        raise ValueError(f"no run files match {pattern!r}")
    return name, paths


def _unique(metrics: Sequence[Metric]) -> list[Metric]:
    seen: dict[str, Metric] = {}
    for metric in metrics:
        seen.setdefault(metric.name, metric)
    return list(seen.values())


def _evaluate(args: argparse.Namespace) -> int:
    metrics = _unique([parse_metric(spec) for spec in args.metrics])
    qrels = read_qrels(args.qrels)
    systems = []
    for spec in args.runs:
        name, paths = _parse_run_spec(spec)
        runs = []
        for path in paths:
            scores = evaluate_run(read_run(path), qrels, metrics, args.min_rel, label=path.name)
            if scores.missing_queries:
                print(
                    f"reteval: warning: {path}: {len(scores.missing_queries)} of "
                    f"{len(scores.query_ids)} queries are missing from the run and score 0",
                    file=sys.stderr,
                )
            runs.append(scores)
        systems.append(System(name, tuple(runs)))

    report = build_report(
        systems,
        [metric.name for metric in metrics],
        baseline=args.baseline,
        min_rel=args.min_rel,
        n_resamples=args.resamples,
        seed=args.seed,
    )
    text = RENDERERS[args.format](report)
    if args.output:
        _write(args.output, text)
    else:
        sys.stdout.write(text)
    if args.per_query:
        _write(args.per_query, per_query_csv(systems))
    if args.plot:
        from reteval.plot import plot_report

        args.plot.parent.mkdir(parents=True, exist_ok=True)
        plot_report(report, args.plot)
    return 0


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _list_metrics() -> int:
    for name, description in available_metrics():
        print(f"{name:<8}{description}")
    print("\nAdd @k for a cutoff, e.g. ndcg@10; without it the whole ranking is used.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "metrics":
            return _list_metrics()
        return _evaluate(args)
    except (OSError, ValueError) as exc:
        print(f"reteval: error: {exc}", file=sys.stderr)
        return 1
