"""Tests for syndrome extraction."""

import numpy as np
from qec.lattice import SurfaceCodeLattice
from qec.syndrome import extract_syndrome, check_logical_error


def test_no_errors_no_syndrome():
    L = SurfaceCodeLattice(3)
    errors = np.zeros(L.num_data_qubits(), dtype=np.uint8)
    syn = extract_syndrome(L, errors)
    assert syn["x_defects"] == []
    assert syn["z_defects"] == []


def test_single_x_triggers_two_z_defects():
    L = SurfaceCodeLattice(5)
    errors = np.zeros(L.num_data_qubits(), dtype=np.uint8)
    errors[L.data_qubit_index[(4, 4)]] = 1  # X
    syn = extract_syndrome(L, errors)
    assert len(syn["z_defects"]) == 2
    assert len(syn["x_defects"]) == 0


def test_single_z_triggers_two_x_defects():
    L = SurfaceCodeLattice(5)
    errors = np.zeros(L.num_data_qubits(), dtype=np.uint8)
    errors[L.data_qubit_index[(4, 4)]] = 2  # Z
    syn = extract_syndrome(L, errors)
    assert len(syn["x_defects"]) == 2
    assert len(syn["z_defects"]) == 0


def test_y_triggers_both():
    L = SurfaceCodeLattice(5)
    errors = np.zeros(L.num_data_qubits(), dtype=np.uint8)
    errors[L.data_qubit_index[(4, 4)]] = 3  # Y
    syn = extract_syndrome(L, errors)
    assert len(syn["x_defects"]) == 2
    assert len(syn["z_defects"]) == 2


def test_x_logical_detected():
    L = SurfaceCodeLattice(3)
    errors = np.zeros(L.num_data_qubits(), dtype=np.uint8)
    for c in range(3):
        errors[L.data_qubit_index[(0, 2 * c)]] = 1  # X on top row
    correction = np.zeros_like(errors)
    result = check_logical_error(L, errors, correction)
    assert result["x_logical"] == True


def test_z_logical_detected():
    L = SurfaceCodeLattice(3)
    errors = np.zeros(L.num_data_qubits(), dtype=np.uint8)
    for r in range(3):
        errors[L.data_qubit_index[(2 * r, 0)]] = 2  # Z on left col
    correction = np.zeros_like(errors)
    result = check_logical_error(L, errors, correction)
    assert result["z_logical"] == True


def test_no_logical_for_stabilizer():
    """A stabilizer pattern should not be detected as a logical error."""
    L = SurfaceCodeLattice(5)
    errors = np.zeros(L.num_data_qubits(), dtype=np.uint8)
    correction = np.zeros_like(errors)
    result = check_logical_error(L, errors, correction)
    assert result["is_error"] == False
