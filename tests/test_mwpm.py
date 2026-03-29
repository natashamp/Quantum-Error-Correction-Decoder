"""Tests for the MWPM decoder."""

import numpy as np
from qec.lattice import SurfaceCodeLattice
from qec.noise import apply_noise
from qec.syndrome import extract_syndrome, check_logical_error
from qec.mwpm_decoder import MWPMDecoder, min_weight_perfect_matching


def test_matching_basic():
    pairs = min_weight_perfect_matching(4, [
        [0, 1, 10, 10],
        [1, 0, 10, 10],
        [10, 10, 0, 1],
        [10, 10, 1, 0],
    ])
    assert sorted(tuple(sorted(p)) for p in pairs) == [(0, 1), (2, 3)]


def test_matching_empty():
    assert min_weight_perfect_matching(0, []) == []


def test_matching_two():
    pairs = min_weight_perfect_matching(2, [[0, 5], [5, 0]])
    assert pairs == [(0, 1)]


def test_single_x_error():
    L = SurfaceCodeLattice(5)
    dec = MWPMDecoder()
    errors = np.zeros(L.num_data_qubits(), dtype=np.uint8)
    errors[L.data_qubit_index[(4, 4)]] = 1
    syn = extract_syndrome(L, errors)
    correction = dec.decode(L, syn)
    result = check_logical_error(L, errors, correction)
    assert result["is_error"] == False


def test_single_z_error():
    L = SurfaceCodeLattice(5)
    dec = MWPMDecoder()
    errors = np.zeros(L.num_data_qubits(), dtype=np.uint8)
    errors[L.data_qubit_index[(4, 4)]] = 2
    syn = extract_syndrome(L, errors)
    correction = dec.decode(L, syn)
    result = check_logical_error(L, errors, correction)
    assert result["is_error"] == False


def test_threshold_behavior():
    """At low error rate, higher distance should give lower logical error rate."""
    dec = MWPMDecoder()
    rng = np.random.default_rng(42)

    rates = {}
    for d in [3, 5]:
        L = SurfaceCodeLattice(d)
        failures = 0
        n_trials = 500
        for _ in range(n_trials):
            errors = apply_noise(L, "depolarizing", 0.02, rng=rng)
            syn = extract_syndrome(L, errors)
            correction = dec.decode(L, syn)
            result = check_logical_error(L, errors, correction)
            if result["is_error"]:
                failures += 1
        rates[d] = failures / n_trials

    assert rates[5] < rates[3], f"d=5 ({rates[5]}) should be better than d=3 ({rates[3]})"
