import numpy as np
import pytest

from reteval.evaluation import RunScores, System
from reteval.plot import PALETTE, plot_report
from reteval.report import build_report


def systems(n: int) -> list[System]:
    return [
        System(f"s{i}", (RunScores(("q1", "q2"), {"MRR": np.array([0.5, 1.0])}),)) for i in range(n)
    ]


def test_plot_writes_an_image(tmp_path):
    path = tmp_path / "chart.png"
    plot_report(build_report(systems(3), ["MRR"]), path)

    assert path.read_bytes().startswith(b"\x89PNG")


def test_plot_refuses_more_systems_than_colours(tmp_path):
    report = build_report(systems(len(PALETTE) + 1), ["MRR"])
    with pytest.raises(ValueError, match="at most 8 systems"):
        plot_report(report, tmp_path / "chart.png")
