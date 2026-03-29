"""
Minimum Weight Perfect Matching decoder for the surface code.

Implements Edmonds' blossom algorithm from scratch for minimum weight
perfect matching on the syndrome graph, then infers corrections from
the matching.

The syndrome graph:
- Nodes: defect positions (fired stabilizers) + virtual boundary node(s)
- Edges: fully connected, weight = Chebyshev distance between defects
  in stabilizer coordinates (= minimum data qubits on a connecting path)
- We need a perfect matching, so pad to even number of nodes if needed.

Key insight for the rotated surface code: stabilizers of the same type
form a diagonal grid. Adjacent same-type stabilizers share exactly one
data qubit, and moving between them is a diagonal step of (±2, ±2) in
coordinate space. The minimum number of qubits to flip between two
same-type stabilizers is max(|Δr|, |Δc|) / 2 (Chebyshev distance).
"""

import numpy as np

from qec.decoder_base import DecoderBase


def min_weight_perfect_matching(n, weights):
    """Exact minimum weight perfect matching using DP with bitmask.

    Time: O(n^2 * 2^n). Space: O(2^n). Practical for n <= ~24.
    For typical surface code decoding, n is usually < 20.

    Args:
        n: number of nodes (must be even)
        weights: n x n weight matrix

    Returns:
        list of (i, j) pairs forming the minimum weight perfect matching
    """
    assert n % 2 == 0
    if n == 0:
        return []
    if n == 2:
        return [(0, 1)]

    INF = float('inf')
    size = 1 << n

    # dp[mask] = min weight to match all nodes in mask
    dp = [INF] * size
    dp[0] = 0

    # parent[mask] = (i, j) pair that was matched to reach this state
    parent = [None] * size

    for mask in range(size):
        if dp[mask] == INF:
            continue

        # Find first unmatched node (lowest unset bit in complement)
        first = -1
        for i in range(n):
            if not (mask & (1 << i)):
                first = i
                break

        if first == -1:
            continue

        # Try pairing first with each other unmatched node
        for j in range(first + 1, n):
            if mask & (1 << j):
                continue

            new_mask = mask | (1 << first) | (1 << j)
            new_cost = dp[mask] + weights[first][j]

            if new_cost < dp[new_mask]:
                dp[new_mask] = new_cost
                parent[new_mask] = (first, j)

    # Reconstruct matching
    pairs = []
    mask = size - 1  # all bits set
    while mask:
        i, j = parent[mask]
        pairs.append((i, j))
        mask ^= (1 << i) | (1 << j)

    return pairs


class MWPMDecoder(DecoderBase):
    """Minimum Weight Perfect Matching decoder for the surface code."""

    def name(self):
        return "MWPM"

    def decode(self, lattice, syndrome):
        """Decode X and Z errors separately.

        - Z-defects (from X errors) -> match Z-defects -> correct X errors
        - X-defects (from Z errors) -> match X-defects -> correct Z errors
        """
        n = lattice.num_data_qubits()
        correction = np.zeros(n, dtype=np.uint8)

        if syndrome["z_defects"]:
            x_corr = self._decode_one_type(
                lattice, syndrome["z_defects"], "Z"
            )
            correction |= x_corr

        if syndrome["x_defects"]:
            z_corr = self._decode_one_type(
                lattice, syndrome["x_defects"], "X"
            )
            correction |= z_corr

        return correction

    def _decode_one_type(self, lattice, defects, stab_type):
        """Decode one error type using MWPM."""
        d = lattice.distance

        # Compute boundary distances for each defect
        boundary_dists = []
        for defect in defects:
            bd = self._boundary_distance(lattice, defect, stab_type)
            boundary_dists.append(bd)

        nodes = list(defects)
        n_defects = len(nodes)

        # Add virtual boundary nodes to allow boundary matching.
        # Boundary-boundary edges have weight 0 (matching two boundaries is free).
        if n_defects % 2 == 1:
            nodes.append("boundary_0")
            n_boundary = 1
        else:
            nodes.append("boundary_0")
            nodes.append("boundary_1")
            n_boundary = 2

        total = len(nodes)
        if total % 2 == 1:
            nodes.append(f"boundary_{n_boundary}")
            total += 1

        # Build weight matrix
        weights = [[0] * total for _ in range(total)]

        for i in range(n_defects):
            for j in range(i + 1, n_defects):
                w = self._defect_distance(defects[i], defects[j])
                weights[i][j] = w
                weights[j][i] = w

        for i in range(n_defects):
            for b in range(n_defects, total):
                w = boundary_dists[i]
                weights[i][b] = w
                weights[b][i] = w

        # Solve matching
        pairs = min_weight_perfect_matching(total, weights)

        # Infer correction from matching
        n_qubits = lattice.num_data_qubits()
        correction = np.zeros(n_qubits, dtype=np.uint8)

        # Error bit: X (bit 0) if stab_type is "Z", Z (bit 1) if stab_type is "X"
        error_bit = 0b01 if stab_type == "Z" else 0b10

        for i, j in pairs:
            if i >= n_defects and j >= n_defects:
                continue

            if i >= n_defects:
                i, j = j, i

            max_coord = 2 * (lattice.distance - 1)
            if j >= n_defects:
                path = self._path_to_boundary(lattice, defects[i], stab_type)
            else:
                path = self._trace_diagonal_path(
                    defects[i][0], defects[i][1],
                    defects[j][0], defects[j][1],
                    max_coord,
                )

            for qubit_pos in path:
                idx = lattice.data_qubit_index[qubit_pos]
                correction[idx] ^= error_bit

        return correction

    def _defect_distance(self, pos1, pos2):
        """Chebyshev distance / 2 between two stabilizer positions.

        On the rotated surface code, same-type stabilizers are connected
        diagonally. The minimum number of data qubit flips to connect
        two same-type stabilizers is max(|Δr|, |Δc|) / 2.
        """
        return max(abs(pos1[0] - pos2[0]), abs(pos1[1] - pos2[1])) // 2

    def _get_boundary_points(self, lattice, stab_type):
        """Get all boundary termination points for error chains of the given type.

        The boundary includes both the actual boundary stabilizers AND the
        "missing" same-type faces on the other two boundaries. Both serve
        as termination points for error chains.

        For X-defect correction (stab_type="X"):
          - Left/right X-boundary stabs (present)
          - Missing X-type faces on top/bottom boundaries

        For Z-defect correction (stab_type="Z"):
          - Top/bottom Z-boundary stabs (present)
          - Missing Z-type faces on left/right boundaries
        """
        d = lattice.distance
        points = []

        if stab_type == "X":
            # Left X-boundary stabs
            for i in range(d - 1):
                if (i + (-1)) % 2 == 1:  # X-type
                    points.append((2 * i + 1, -1))
            # Right X-boundary stabs
            for i in range(d - 1):
                if (i + d - 1) % 2 == 1:  # X-type
                    points.append((2 * i + 1, 2 * d - 1))
            # Missing X-type faces on top boundary
            for j in range(d - 1):
                if (-1 + j) % 2 == 1:  # X-type, not built
                    points.append((-1, 2 * j + 1))
            # Missing X-type faces on bottom boundary
            for j in range(d - 1):
                if (d - 1 + j) % 2 == 1:  # X-type, not built
                    points.append((2 * d - 1, 2 * j + 1))
        else:  # Z
            # Top Z-boundary stabs
            for j in range(d - 1):
                if (-1 + j) % 2 == 0:  # Z-type
                    points.append((-1, 2 * j + 1))
            # Bottom Z-boundary stabs
            for j in range(d - 1):
                if (d - 1 + j) % 2 == 0:  # Z-type
                    points.append((2 * d - 1, 2 * j + 1))
            # Missing Z-type faces on left boundary
            for i in range(d - 1):
                if (i + (-1)) % 2 == 0:  # Z-type, not built
                    points.append((2 * i + 1, -1))
            # Missing Z-type faces on right boundary
            for i in range(d - 1):
                if (i + d - 1) % 2 == 0:  # Z-type, not built
                    points.append((2 * i + 1, 2 * d - 1))

        return points

    def _boundary_distance(self, lattice, defect_pos, stab_type):
        """Distance from a defect to the nearest boundary termination point."""
        points = self._get_boundary_points(lattice, stab_type)
        r, c = defect_pos
        return min(
            max(abs(r - p[0]), abs(c - p[1])) // 2
            for p in points
        )

    def _find_nearest_boundary_point(self, lattice, defect_pos, stab_type):
        """Find the coordinate of the nearest boundary termination point."""
        points = self._get_boundary_points(lattice, stab_type)
        r, c = defect_pos
        return min(points,
                   key=lambda p: max(abs(r - p[0]), abs(c - p[1])))

    def _trace_diagonal_path(self, r1, c1, r2, c2, max_coord):
        """Trace a diagonal path between two same-type stabilizer positions.

        On the rotated surface code, same-type stabilizers form a diagonal grid.
        Each step is (±2, ±2) in coordinate space, flipping the data qubit at
        the midpoint (r±1, c±1).

        We decompose the displacement into two orthogonal diagonal directions:
          u = (Δr + Δc) / 2  (northeast/southwest component)
          v = (Δr - Δc) / 2  (northwest/southeast component)

        Steps are interleaved (u then v) to avoid going out of bounds.
        When a u-step would leave the grid, a v-step is done instead.

        Returns list of data qubit positions to flip.
        """
        path = []
        r, c = r1, c1

        dr_total = r2 - r1
        dc_total = c2 - c1

        u = (dr_total + dc_total) // 2
        v = (dr_total - dc_total) // 2

        u_remaining = abs(u) // 2
        v_remaining = abs(v) // 2
        u_sign = 1 if u >= 0 else -1
        v_sign = 1 if v >= 0 else -1

        while u_remaining > 0 or v_remaining > 0:
            # Try u-step first
            if u_remaining > 0:
                qr, qc = r + u_sign, c + u_sign
                if 0 <= qr <= max_coord and 0 <= qc <= max_coord:
                    path.append((qr, qc))
                    r += 2 * u_sign
                    c += 2 * u_sign
                    u_remaining -= 1
                    continue

            # Try v-step
            if v_remaining > 0:
                qr, qc = r + v_sign, c - v_sign
                if 0 <= qr <= max_coord and 0 <= qc <= max_coord:
                    path.append((qr, qc))
                    r += 2 * v_sign
                    c -= 2 * v_sign
                    v_remaining -= 1
                    continue

            # Safety: shouldn't reach here for valid inputs
            break

        return path

    def _path_to_boundary(self, lattice, defect_pos, stab_type):
        """Trace a diagonal path from a defect to the nearest boundary point."""
        target = self._find_nearest_boundary_point(lattice, defect_pos, stab_type)
        max_coord = 2 * (lattice.distance - 1)
        return self._trace_diagonal_path(
            defect_pos[0], defect_pos[1], target[0], target[1], max_coord
        )
