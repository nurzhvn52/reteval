"""Grouped bar chart of a report: one group per metric, one bar per system.

Error bars show the standard deviation over repeated runs. The figure is built with
the object-oriented matplotlib API, so no GUI backend is needed (CI, servers).
"""

from pathlib import Path

from reteval.report import Report

# Categorical colours in a fixed order; the order keeps neighbouring bars apart
# for colour-blind readers, so systems are never given colours out of order.
PALETTE = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948")
_INK = "#0b0b0b"
_INK_SECONDARY = "#52514e"
_GRID = "#e1e0d9"
_AXIS = "#c3c2b7"
_SURFACE = "#fcfcfb"


def plot_report(report: Report, path: str | Path, *, dpi: int = 200) -> None:
    """Save the chart to ``path``; the format follows the file extension."""
    from matplotlib.figure import Figure  # imported lazily: matplotlib is slow to import

    n_systems = len(report.systems)
    if n_systems > len(PALETTE):
        raise ValueError(f"the chart supports at most {len(PALETTE)} systems")

    # bars stay narrow and leave air between the groups of metrics
    bar_width = min(0.7 / n_systems, 0.25)
    fig = Figure(figsize=(max(6.0, 1.6 * len(report.metrics) + 1.5), 3.6), facecolor=_SURFACE)
    ax = fig.subplots()
    ax.set_facecolor(_SURFACE)

    for i, (system, colour) in enumerate(zip(report.systems, PALETTE, strict=False)):
        rows = [report.row(system, metric) for metric in report.metrics]
        offset = (i - (n_systems - 1) / 2) * bar_width
        ax.bar(
            [m + offset for m in range(len(report.metrics))],
            [row.mean for row in rows],
            # the white edge leaves a thin gap between neighbouring bars
            width=bar_width,
            color=colour,
            edgecolor=_SURFACE,
            linewidth=1.5,
            # a single run has no spread, so it gets no error bar at all
            yerr=[row.std for row in rows] if rows[0].runs > 1 else None,
            error_kw={"ecolor": _INK_SECONDARY, "elinewidth": 1, "capsize": 3},
            label=system if rows[0].runs == 1 else f"{system} ({rows[0].runs} runs)",
            zorder=2,
        )

    ax.set_xticks(range(len(report.metrics)), report.metrics, color=_INK)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Score", color=_INK_SECONDARY)
    ax.tick_params(colors=_INK_SECONDARY, length=0)
    ax.grid(axis="y", color=_GRID, linewidth=0.8, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(_AXIS)
    # legend above the plot area, so it never covers a tall bar
    ax.legend(
        frameon=False,
        ncols=min(n_systems, 4),
        loc="lower right",
        bbox_to_anchor=(1, 1),
        fontsize=9,
        labelcolor=_INK,
    )
    ax.set_title(
        f"Mean over {report.n_queries} queries; error bars: SD over runs",
        loc="left",
        fontsize=9,
        color=_INK_SECONDARY,
    )
    fig.tight_layout()
    fig.savefig(path, dpi=dpi)
