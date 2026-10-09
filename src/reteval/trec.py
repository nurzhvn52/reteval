"""Readers for TREC-style relevance judgements (qrels) and ranked runs.

qrels: one judgement per line, ``query_id iteration doc_id relevance``.
run:   one retrieved document per line, ``query_id Q0 doc_id rank score tag``.

These are the formats of trec_eval and of most IR toolkits (Anserini/Pyserini,
ir_datasets), so runs produced elsewhere can be evaluated without conversion.
"""

import math
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

#: query id -> document id -> relevance grade
Qrels = dict[str, dict[str, int]]
#: query id -> document ids ordered from best to worst
Run = dict[str, list[str]]


class FormatError(ValueError):
    """An input file does not follow the expected format."""

    def __init__(self, path: str | Path, line_no: int, message: str) -> None:
        location = f"{path}:{line_no}" if line_no else str(path)
        super().__init__(f"{location}: {message}")


def _records(path: str | Path, n_fields: int) -> Iterator[tuple[int, list[str]]]:
    """Yield ``(line number, fields)`` for every non-empty, non-comment line."""
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            fields = line.split()
            if not fields or fields[0].startswith("#"):
                continue
            if len(fields) != n_fields:
                raise FormatError(path, line_no, f"expected {n_fields} columns, got {len(fields)}")
            yield line_no, fields


def read_qrels(path: str | Path) -> Qrels:
    """Read relevance judgements. Grades are integers; grades <= 0 mean non-relevant."""
    qrels: defaultdict[str, dict[str, int]] = defaultdict(dict)
    for line_no, (qid, _iteration, doc_id, grade_text) in _records(path, 4):
        try:
            grade = int(grade_text)
        except ValueError:
            raise FormatError(
                path, line_no, f"relevance must be an integer, got {grade_text!r}"
            ) from None
        if doc_id in qrels[qid]:
            raise FormatError(
                path, line_no, f"duplicate judgement for query {qid!r}, document {doc_id!r}"
            )
        qrels[qid][doc_id] = grade
    if not qrels:
        raise FormatError(path, 0, "no judgements found")
    return dict(qrels)


def read_run(path: str | Path) -> Run:
    """Read a ranked run.

    Documents are ordered by descending score. The rank column is ignored, as in
    trec_eval, and ties are broken by document id, so the order never depends on
    the order of lines in the file.
    """
    scored: defaultdict[str, dict[str, float]] = defaultdict(dict)
    for line_no, (qid, _q0, doc_id, _rank, score_text, _tag) in _records(path, 6):
        try:
            score = float(score_text)
        except ValueError:
            raise FormatError(
                path, line_no, f"score must be a number, got {score_text!r}"
            ) from None
        if math.isnan(score):
            raise FormatError(path, line_no, "score is NaN")
        if doc_id in scored[qid]:
            raise FormatError(
                path, line_no, f"document {doc_id!r} is retrieved twice for query {qid!r}"
            )
        scored[qid][doc_id] = score
    if not scored:
        raise FormatError(path, 0, "no retrieved documents found")
    return {qid: _order_by_score(docs) for qid, docs in scored.items()}


def _order_by_score(scores: dict[str, float]) -> list[str]:
    return sorted(scores, key=lambda doc: (-scores[doc], doc))
