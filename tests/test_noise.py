"""Tests for noise models."""

import numpy as np
from qec.lattice import SurfaceCodeLattice
from qec.noise import apply_noise


def test_no_errors_at_p_zero():
    L = SurfaceCodeLattice(3)
    errors = apply_noise(L, "depolarizing", 0.0, rng=np.random.default_rng(42))
    assert np.all(errors == 0)


def test_all_x_at_p_one():
    L = SurfaceCodeLattice(3)
    errors = apply_noise(L, "bit_flip", 1.0, rng=np.random.default_rng(42))
    assert np.all(errors == 1)


def test_all_z_at_p_one():
    L = SurfaceCodeLattice(3)
    errors = apply_noise(L, "phase_flip", 1.0, rng=np.random.default_rng(42))
    assert np.all(errors == 2)


def test_depolarizing_stats():
    L = SurfaceCodeLattice(5)
    rng = np.random.default_rng(42)
    counts = np.zeros(4)
    for _ in range(5000):
        e = apply_noise(L, "depolarizing", 0.09, rng=rng)
        for v in e:
            counts[v] += 1
    total = 5000 * 25
    # Each of X, Y, Z should be ~3%
    for i in [1, 2, 3]:
        rate = counts[i] / total
        assert 0.02 < rate < 0.04, f"Pauli {i} rate {rate:.4f} out of range"


def test_biased_noise():
    L = SurfaceCodeLattice(5)
    rng = np.random.default_rng(42)
    z_count = 0
    x_count = 0
    for _ in range(5000):
        e = apply_noise(L, "biased", 0.1, rng=rng, bias_eta=10.0)
        z_count += np.sum(e == 2)
        x_count += np.sum(e == 1)
    # Z should be much more common than X with eta=10
    assert z_count > x_count * 5
