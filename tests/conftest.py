from collections.abc import Callable
from pathlib import Path

import pytest

QRELS = """\
# query iteration document relevance
q1 0 d1 2
q1 0 d3 1
q1 0 d5 1
q1 0 d9 0
q2 0 d2 1
q3 0 d7 0
"""

# q1: d1 and d3 are relevant and ranked 1st and 3rd; q2: the relevant d2 is ranked 2nd.
# q3 has no relevant document and must be left out of the evaluation.
RUN_A = """\
q1 Q0 d1 1 9.0 a
q1 Q0 d2 2 8.0 a
q1 Q0 d3 3 7.0 a
q2 Q0 d4 1 5.0 a
q2 Q0 d2 2 4.0 a
q3 Q0 d7 1 1.0 a
"""

# A weaker system: relevant documents are ranked lower.
RUN_B = """\
q1 Q0 d2 1 9.0 b
q1 Q0 d4 2 8.0 b
q1 Q0 d1 3 7.0 b
q2 Q0 d4 1 5.0 b
q2 Q0 d6 2 4.0 b
q2 Q0 d2 3 3.0 b
"""


@pytest.fixture
def write(tmp_path: Path) -> Callable[[str, str], Path]:
    """Write ``text`` to ``tmp_path / name`` and return the path."""

    def _write(name: str, text: str) -> Path:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    return _write


@pytest.fixture
def qrels_file(write: Callable[[str, str], Path]) -> Path:
    return write("qrels.txt", QRELS)


@pytest.fixture
def run_a_file(write: Callable[[str, str], Path]) -> Path:
    return write("runs/a.run", RUN_A)


@pytest.fixture
def run_b_file(write: Callable[[str, str], Path]) -> Path:
    return write("runs/b.run", RUN_B)
