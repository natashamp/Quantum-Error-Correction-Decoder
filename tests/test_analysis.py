"""Tests for the analysis module."""

import numpy as np
from qec.lattice import SurfaceCodeLattice
from qec.mwpm_decoder import MWPMDecoder
from qec.analysis import monte_carlo


def test_monte_carlo_basic():
    L = SurfaceCodeLattice(3)
    dec = MWPMDecoder()
    result = monte_carlo(L, dec, "depolarizing", 0.05, 50,
                         rng=np.random.default_rng(42))
    assert "logical_error_rate" in result
    assert "std_error" in result
    assert "avg_runtime_ms" in result
    assert 0 <= result["logical_error_rate"] <= 1


def test_monte_carlo_zero_errors():
    L = SurfaceCodeLattice(3)
    dec = MWPMDecoder()
    result = monte_carlo(L, dec, "depolarizing", 0.0, 50,
                         rng=np.random.default_rng(42))
    assert result["logical_error_rate"] == 0.0
