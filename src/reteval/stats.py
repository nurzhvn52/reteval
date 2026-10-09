"""Summary statistics over repeated runs and paired comparisons between systems.

Two sources of variation are reported separately:

* between repeated runs of one system (random seeds): the standard deviation of the
  run means, see :func:`summarize`;
* between queries: used by the paired randomization test and by the bootstrap
  confidence interval of the difference to a baseline.

Both procedures are Monte Carlo methods and take an explicit ``seed``, so a report
can be reproduced exactly.
"""

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

# Upper bound on the size of one block of resamples, to keep memory use small.
_BLOCK_ELEMENTS = 1_000_000


@dataclass(frozen=True)
class Summary:
    mean: float
    std: float
    n: int


def summarize(values: npt.ArrayLike) -> Summary:
    """Mean and sample standard deviation (ddof=1); the deviation of one value is 0."""
    arr = _as_sample(values)
    std = float(arr.std(ddof=1)) if arr.size > 1 else 0.0
    return Summary(float(arr.mean()), std, int(arr.size))


def _as_sample(values: npt.ArrayLike) -> npt.NDArray[np.float64]:
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 1 or arr.size == 0:
        raise ValueError("expected a non-empty 1-D sequence")
    return arr


def _blocks(n_resamples: int, sample_size: int) -> list[int]:
    if n_resamples < 1:
        raise ValueError("n_resamples must be positive")
    block = max(1, _BLOCK_ELEMENTS // sample_size)
    return [min(block, n_resamples - start) for start in range(0, n_resamples, block)]


def paired_randomization_test(
    a: npt.ArrayLike, b: npt.ArrayLike, n_resamples: int = 10_000, seed: int = 0
) -> float:
    """Two-sided paired randomization test of H0: mean(a - b) = 0.

    Under H0 the sign of each per-query difference is arbitrary, so the observed mean
    difference is compared with the means obtained after flipping signs at random.
    Returns the Monte Carlo p-value ``(extreme + 1) / (n_resamples + 1)``, which is
    never 0.
    """
    x, y = _as_sample(a), _as_sample(b)
    if x.shape != y.shape:
        raise ValueError("paired samples must have the same length")
    diff = x - y
    # Resamples equal to the observed value up to rounding error count as extreme.
    threshold = abs(diff.mean()) - 1e-12
    rng = np.random.default_rng(seed)
    extreme = 0
    for size in _blocks(n_resamples, diff.size):
        signs = rng.choice(np.array([-1.0, 1.0]), size=(size, diff.size))
        extreme += int(np.count_nonzero(np.abs(signs @ diff) / diff.size >= threshold))
    return (extreme + 1) / (n_resamples + 1)


def bootstrap_ci(
    values: npt.ArrayLike, confidence: float = 0.95, n_resamples: int = 10_000, seed: int = 0
) -> tuple[float, float]:
    """Percentile bootstrap confidence interval for the mean of ``values``."""
    arr = _as_sample(values)
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    rng = np.random.default_rng(seed)
    means = np.concatenate(
        [
            arr[rng.integers(0, arr.size, size=(size, arr.size))].mean(axis=1)
            for size in _blocks(n_resamples, arr.size)
        ]
    )
    alpha = (1 - confidence) / 2
    low, high = np.quantile(means, [alpha, 1 - alpha])
    return float(low), float(high)
