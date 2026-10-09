import pytest

from reteval.trec import FormatError, read_qrels, read_run


def test_read_qrels(qrels_file):
    qrels = read_qrels(qrels_file)

    assert qrels["q1"] == {"d1": 2, "d3": 1, "d5": 1, "d9": 0}
    assert qrels["q2"] == {"d2": 1}
    assert set(qrels) == {"q1", "q2", "q3"}


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("q1 0 d1\n", ":1: expected 4 columns, got 3"),
        ("q1 0 d1 yes\n", ":1: relevance must be an integer"),
        ("q1 0 d1 1\nq1 0 d1 2\n", ":2: duplicate judgement"),
        ("# only a comment\n\n", "no judgements found"),
    ],
)
def test_read_qrels_rejects_malformed_input(write, text, message):
    with pytest.raises(FormatError, match=message):
        read_qrels(write("qrels.txt", text))


def test_read_run_orders_by_score_not_by_line_or_rank_column(write):
    text = "q1 Q0 low 1 0.5 t\nq1 Q0 high 9 2.5 t\nq1 Q0 mid 5 1.0 t\n"

    assert read_run(write("run.txt", text)) == {"q1": ["high", "mid", "low"]}


def test_read_run_breaks_ties_by_document_id(write):
    text = "q1 Q0 b 1 1.0 t\nq1 Q0 c 2 1.0 t\nq1 Q0 a 3 1.0 t\n"

    assert read_run(write("run.txt", text)) == {"q1": ["a", "b", "c"]}


def test_read_run_groups_by_query(run_a_file):
    run = read_run(run_a_file)

    assert run["q1"] == ["d1", "d2", "d3"]
    assert run["q2"] == ["d4", "d2"]


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("q1 Q0 d1 1 0.5\n", ":1: expected 6 columns, got 5"),
        ("q1 Q0 d1 1 high t\n", ":1: score must be a number"),
        ("q1 Q0 d1 1 nan t\n", ":1: score is NaN"),
        ("q1 Q0 d1 1 0.5 t\nq1 Q0 d1 2 0.4 t\n", ":2: document 'd1' is retrieved twice"),
        ("", "no retrieved documents found"),
    ],
)
def test_read_run_rejects_malformed_input(write, text, message):
    with pytest.raises(FormatError, match=message):
        read_run(write("run.txt", text))


def test_format_error_is_a_value_error(write):
    with pytest.raises(ValueError, match=r"run\.txt"):
        read_run(write("run.txt", ""))
