import itertools

import numpy as np
import pytest

from reteval.stats import bootstrap_ci, paired_randomization_test, summarize


def test_summarize_uses_sample_standard_deviation():
    summary = summarize([0.2, 0.4, 0.6])
    assert summary.mean == pytest.approx(0.4)
    assert summary.std == pytest.approx(0.2)
    assert summary.n == 3


def test_summarize_single_run_has_zero_deviation():
    assert summarize([0.5]).std == 0.0


@pytest.mark.parametrize("values", [[], [[0.1, 0.2]]])
def test_summarize_rejects_bad_shapes(values):
    with pytest.raises(ValueError, match="1-D"):
        summarize(values)


def exact_randomization_p(diff: np.ndarray) -> float:
    """Exact two-sided p-value by enumerating all 2^n sign assignments."""
    observed = abs(diff.mean())
    signs = np.array(list(itertools.product([-1.0, 1.0], repeat=diff.size)))
    return float(np.mean(np.abs(signs @ diff) / diff.size >= observed - 1e-12))


def test_randomization_test_agrees_with_exact_enumeration():
    rng = np.random.default_rng(42)
    a = rng.uniform(0, 1, size=10)
    b = a - rng.normal(0.08, 0.1, size=10)

    exact = exact_randomization_p(a - b)
    approx = paired_randomization_test(a, b, n_resamples=50_000, seed=1)

    # Monte Carlo standard error is at most sqrt(0.25 / 50000) ~ 0.0022
    assert approx == pytest.approx(exact, abs=0.01)


def test_identical_systems_are_not_different():
    a = np.linspace(0, 1, 25)
    assert paired_randomization_test(a, a, n_resamples=500) == 1.0


def test_consistent_improvement_is_significant():
    a = np.linspace(0.1, 0.9, 30)
    p = paired_randomization_test(a + 0.05, a, n_resamples=2_000)
    assert p == pytest.approx(1 / 2_001)


def test_randomization_test_is_reproducible_with_a_seed():
    rng = np.random.default_rng(0)
    a, b = rng.uniform(size=50), rng.uniform(size=50)
    assert paired_randomization_test(a, b, seed=7) == paired_randomization_test(a, b, seed=7)


def test_randomization_test_handles_many_resamples_in_blocks():
    # 3 queries x 1e6 resamples is larger than one block, so several blocks are drawn
    p = paired_randomization_test([0.1, 0.2, 0.3], [0.1, 0.2, 0.3], n_resamples=1_000_000)
    assert p == 1.0


def test_randomization_test_rejects_unpaired_samples():
    with pytest.raises(ValueError, match="same length"):
        paired_randomization_test([0.1, 0.2], [0.1])


def test_randomization_test_rejects_no_resamples():
    with pytest.raises(ValueError, match="n_resamples"):
        paired_randomization_test([0.1], [0.2], n_resamples=0)


def test_bootstrap_ci_of_constant_values_is_a_point():
    assert bootstrap_ci([0.3] * 20) == pytest.approx((0.3, 0.3))


def test_bootstrap_ci_contains_the_mean_and_widens_with_confidence():
    values = np.random.default_rng(3).normal(0.1, 0.2, size=60)
    low90, high90 = bootstrap_ci(values, confidence=0.90, n_resamples=4_000)
    low99, high99 = bootstrap_ci(values, confidence=0.99, n_resamples=4_000)

    assert low90 < values.mean() < high90
    assert low99 < low90
    assert high99 > high90


@pytest.mark.parametrize("confidence", [0, 1, 1.5])
def test_bootstrap_ci_rejects_bad_confidence(confidence):
    with pytest.raises(ValueError, match="confidence"):
        bootstrap_ci([0.1, 0.2], confidence=confidence)
