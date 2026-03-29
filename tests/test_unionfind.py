"""Tests for the Union-Find decoder."""

import numpy as np
from qec.lattice import SurfaceCodeLattice
from qec.syndrome import extract_syndrome, check_logical_error
from qec.unionfind_decoder import UnionFindDecoder


def test_single_x_error():
    L = SurfaceCodeLattice(5)
    dec = UnionFindDecoder()
    errors = np.zeros(L.num_data_qubits(), dtype=np.uint8)
    errors[L.data_qubit_index[(4, 4)]] = 1
    syn = extract_syndrome(L, errors)
    correction = dec.decode(L, syn)
    result = check_logical_error(L, errors, correction)
    assert result["is_error"] == False


def test_single_z_error():
    L = SurfaceCodeLattice(5)
    dec = UnionFindDecoder()
    errors = np.zeros(L.num_data_qubits(), dtype=np.uint8)
    errors[L.data_qubit_index[(4, 4)]] = 2
    syn = extract_syndrome(L, errors)
    correction = dec.decode(L, syn)
    result = check_logical_error(L, errors, correction)
    assert result["is_error"] == False


def test_no_errors():
    L = SurfaceCodeLattice(3)
    dec = UnionFindDecoder()
    errors = np.zeros(L.num_data_qubits(), dtype=np.uint8)
    syn = extract_syndrome(L, errors)
    correction = dec.decode(L, syn)
    assert np.all(correction == 0)
