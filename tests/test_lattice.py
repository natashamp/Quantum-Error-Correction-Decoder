"""Tests for the surface code lattice."""

import pytest
from qec.lattice import SurfaceCodeLattice


def test_distance_3():
    L = SurfaceCodeLattice(3)
    assert L.num_data_qubits() == 9
    assert len(L.x_stabilizers) == 4
    assert len(L.z_stabilizers) == 4


def test_distance_5():
    L = SurfaceCodeLattice(5)
    assert L.num_data_qubits() == 25
    assert len(L.x_stabilizers) + len(L.z_stabilizers) == 24


def test_distance_7():
    L = SurfaceCodeLattice(7)
    assert L.num_data_qubits() == 49
    assert len(L.x_stabilizers) == 24
    assert len(L.z_stabilizers) == 24


def test_stabilizer_count():
    for d in [3, 5, 7, 9]:
        L = SurfaceCodeLattice(d)
        total = len(L.x_stabilizers) + len(L.z_stabilizers)
        assert total == d * d - 1, f"d={d}: expected {d*d-1} stabilizers, got {total}"


def test_interior_qubit_in_two_stabs():
    """Interior qubits should be in exactly 2 X-stabs and 2 Z-stabs."""
    L = SurfaceCodeLattice(5)
    center = (4, 4)
    xs = L.get_stabilizers_for_qubit(center, "X")
    zs = L.get_stabilizers_for_qubit(center, "Z")
    assert len(xs) == 2
    assert len(zs) == 2


def test_to_dict():
    L = SurfaceCodeLattice(3)
    d = L.to_dict()
    assert d["distance"] == 3
    assert len(d["data_qubits"]) == 9


def test_invalid_distance():
    with pytest.raises(ValueError):
        SurfaceCodeLattice(2)
    with pytest.raises(ValueError):
        SurfaceCodeLattice(4)
