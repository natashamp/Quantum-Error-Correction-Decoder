"""
Noise models for the surface code simulator.

Error encoding (2-bit Pauli representation):
    0 = I  (00)
    1 = X  (01)  - bit flip
    2 = Z  (10)  - phase flip
    3 = Y  (11)  - both (X and Z)

Composition of Paulis is XOR on this 2-bit representation.
"""

import numpy as np


def apply_noise(lattice, model, p, rng=None, **kwargs):
    """Apply a noise model to all data qubits.

    Args:
        lattice: SurfaceCodeLattice instance.
        model: One of "depolarizing", "bit_flip", "phase_flip", "biased".
        p: Error probability.
        rng: Optional numpy Generator for reproducibility.
        **kwargs: Additional parameters (e.g., bias_eta for biased noise).

    Returns:
        np.ndarray of shape (n_data_qubits,) with Pauli labels (0-3).
    """
    if rng is None:
        rng = np.random.default_rng()

    n = lattice.num_data_qubits()

    if model == "depolarizing":
        return _depolarizing(n, p, rng)
    elif model == "bit_flip":
        return _bit_flip(n, p, rng)
    elif model == "phase_flip":
        return _phase_flip(n, p, rng)
    elif model == "biased":
        eta = kwargs.get("bias_eta", 10.0)
        return _biased(n, p, eta, rng)
    else:
        raise ValueError(f"Unknown noise model: {model}")


def _depolarizing(n, p, rng):
    """Each qubit gets X, Y, or Z with probability p/3 each."""
    errors = np.zeros(n, dtype=np.uint8)
    rand = rng.random(n)
    errors[rand < p / 3] = 1        # X
    errors[(rand >= p / 3) & (rand < 2 * p / 3)] = 3  # Y
    errors[(rand >= 2 * p / 3) & (rand < p)] = 2      # Z
    return errors


def _bit_flip(n, p, rng):
    """Each qubit gets X with probability p."""
    errors = np.zeros(n, dtype=np.uint8)
    errors[rng.random(n) < p] = 1
    return errors


def _phase_flip(n, p, rng):
    """Each qubit gets Z with probability p."""
    errors = np.zeros(n, dtype=np.uint8)
    errors[rng.random(n) < p] = 2
    return errors


def _biased(n, p, eta, rng):
    """Biased noise: Z errors are eta times more likely than X or Y.

    p_Z = p * eta / (eta + 1)
    p_X = p_Y = p / (2 * (eta + 1))

    When eta=0.5, this reduces to depolarizing (each p/3).
    When eta -> inf, almost all errors are Z.
    """
    p_x = p / (2 * (eta + 1))
    p_y = p_x
    p_z = p * eta / (eta + 1)

    errors = np.zeros(n, dtype=np.uint8)
    rand = rng.random(n)
    errors[rand < p_x] = 1                              # X
    errors[(rand >= p_x) & (rand < p_x + p_y)] = 3      # Y
    errors[(rand >= p_x + p_y) & (rand < p_x + p_y + p_z)] = 2  # Z
    return errors
