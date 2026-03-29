"""
Syndrome extraction and logical error checking for the rotated surface code.

Syndrome rules:
- X-stabilizer fires if an odd number of its data qubits have an X or Y error
  (i.e., the X-component, bit 0, is set)
- Z-stabilizer fires if an odd number of its data qubits have a Z or Y error
  (i.e., the Z-component, bit 1, is set)
"""

import numpy as np


def extract_syndrome(lattice, errors):
    """Compute syndrome from an error configuration.

    Args:
        lattice: SurfaceCodeLattice instance.
        errors: np.ndarray of Pauli labels (0=I, 1=X, 2=Z, 3=Y).

    Returns:
        dict with:
            "x_defects": list of X-stabilizer positions that fired
            "z_defects": list of Z-stabilizer positions that fired
    """
    idx = lattice.data_qubit_index

    x_defects = []
    for stab_pos, qubits in lattice.x_stabilizer_qubits.items():
        # X-stabilizer measures product of Z on its qubits.
        # Fires if odd number of qubits have Z-component set (Z or Y error).
        parity = 0
        for q in qubits:
            if errors[idx[q]] & 0b10:  # Z-component (bit 1)
                parity ^= 1
        if parity:
            x_defects.append(stab_pos)

    z_defects = []
    for stab_pos, qubits in lattice.z_stabilizer_qubits.items():
        # Z-stabilizer measures product of X on its qubits.
        # Fires if odd number of qubits have X-component set (X or Y error).
        parity = 0
        for q in qubits:
            if errors[idx[q]] & 0b01:  # X-component (bit 0)
                parity ^= 1
        if parity:
            z_defects.append(stab_pos)

    return {"x_defects": x_defects, "z_defects": z_defects}


def check_logical_error(lattice, errors, correction):
    """Check if the residual (errors XOR correction) is a logical error.

    After decoding, the residual = errors ^ correction should be either:
    - Identity (all zeros) or a stabilizer: decoding succeeded
    - A non-trivial logical operator: decoding failed

    For the rotated surface code:
    - X logical operator: chain of X errors spanning left to right
    - Z logical operator: chain of Z errors spanning top to bottom

    We check by computing the parity of:
    - X-components along any single row (detects X logical)
    - Z-components along any single column (detects Z logical)

    Returns:
        dict with:
            "x_logical": bool - True if X logical error occurred
            "z_logical": bool - True if Z logical error occurred
            "is_error": bool - True if any logical error occurred
    """
    d = lattice.distance
    idx = lattice.data_qubit_index
    residual = errors ^ correction

    # Check X logical: does the residual anticommute with the Z logical?
    # Z logical = Z on all qubits in a column. Anticommutes iff odd number
    # of qubits in that column have X-component set (bit 0).
    # Check along the middle column.
    col = 2 * (d // 2)
    x_parity = 0
    for r in range(d):
        q = (2 * r, col)
        if residual[idx[q]] & 0b01:  # X-component
            x_parity ^= 1

    # Check Z logical: does the residual anticommute with the X logical?
    # X logical = X on all qubits in a row. Anticommutes iff odd number
    # of qubits in that row have Z-component set (bit 1).
    # Check along the middle row.
    row = 2 * (d // 2)
    z_parity = 0
    for c in range(d):
        q = (row, 2 * c)
        if residual[idx[q]] & 0b10:  # Z-component
            z_parity ^= 1

    return {
        "x_logical": bool(x_parity),
        "z_logical": bool(z_parity),
        "is_error": bool(x_parity or z_parity),
    }
