"""
Union-Find decoder for the surface code.

Implements the Delfosse-Nickerson Union-Find decoder with cluster growth
and peeling. Near-linear time complexity.

Algorithm:
1. Initialize each defect as an odd-parity cluster.
2. Grow clusters by processing edges in weight order.
3. When two clusters merge, XOR their parities.
4. Stop when all clusters have even parity.
5. Peel the spanning forest to extract corrections.
"""

import numpy as np
from qec.decoder_base import DecoderBase


class UnionFindDecoder(DecoderBase):
    """Union-Find decoder for the surface code."""

    def name(self):
        return "Union-Find"

    def decode(self, lattice, syndrome):
        n = lattice.num_data_qubits()
        correction = np.zeros(n, dtype=np.uint8)

        if syndrome["z_defects"]:
            x_corr = self._decode_one_type(lattice, syndrome["z_defects"], "Z")
            correction |= x_corr

        if syndrome["x_defects"]:
            z_corr = self._decode_one_type(lattice, syndrome["x_defects"], "X")
            correction |= z_corr

        return correction

    def _decode_one_type(self, lattice, defects, stab_type):
        """Decode one error type using Union-Find with cluster growth + peeling."""
        d = lattice.distance
        error_bit = 0b01 if stab_type == "Z" else 0b10

        # Build the graph of same-type stabilizers connected by shared data qubits.
        # Nodes: all same-type stabs (interior + boundary) + virtual boundary nodes.
        # Edges: between adjacent same-type stabs (weight = 1 data qubit).
        #        from boundary stabs to virtual boundary (weight = 0).

        if stab_type == "Z":
            stab_list = list(lattice.z_stabilizers)
            stab_qubits = lattice.z_stabilizer_qubits
        else:
            stab_list = list(lattice.x_stabilizers)
            stab_qubits = lattice.x_stabilizer_qubits

        # Get boundary points (including missing faces)
        boundary_points = self._get_boundary_points(lattice, stab_type)

        # All nodes: stabs + boundary points (deduplicated) + 1 virtual boundary
        seen = set()
        all_nodes = []
        for pos in stab_list + boundary_points:
            if pos not in seen:
                seen.add(pos)
                all_nodes.append(pos)

        # Add a virtual boundary node that absorbs odd-parity chains
        virtual_boundary_idx = len(all_nodes)
        all_nodes.append("virtual_boundary")
        node_index = {pos: i for i, pos in enumerate(all_nodes)}
        n_nodes = len(all_nodes)

        # Identify which real nodes are boundary termination points
        boundary_set = set(boundary_points)

        # Build edges between adjacent same-type nodes (sharing a data qubit)
        edges = []  # (weight, node_i, node_j, data_qubit_pos)

        for i, pos_i in enumerate(all_nodes):
            if pos_i == "virtual_boundary":
                continue
            for dr, dc in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
                pos_j = (pos_i[0] + dr, pos_i[1] + dc)
                if pos_j in node_index:
                    j = node_index[pos_j]
                    if j > i:
                        qr = pos_i[0] + dr // 2
                        qc = pos_i[1] + dc // 2
                        if 0 <= qr <= 2 * (d - 1) and 0 <= qc <= 2 * (d - 1):
                            edges.append((1, i, j, (qr, qc)))

        # Connect all boundary termination points to the virtual boundary
        # with weight 0 (no data qubit to flip — boundary absorbs the chain)
        for i, pos_i in enumerate(all_nodes):
            if pos_i != "virtual_boundary" and pos_i in boundary_set:
                edges.append((0, i, virtual_boundary_idx, None))

        # Sort edges by weight (process weight-0 boundary edges first)
        edges.sort()

        # Union-Find data structures
        parent = list(range(n_nodes))
        rank = [0] * n_nodes
        parity = [False] * n_nodes  # True = odd (has unmatched defect)

        defect_set = set(defects)
        for pos in defect_set:
            if pos in node_index:
                parity[node_index[pos]] = True

        # Virtual boundary always has even parity
        parity[virtual_boundary_idx] = False

        # Forest edges for peeling
        forest = []  # list of (node_i, node_j, data_qubit_pos)

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]  # path compression
                x = parent[x]
            return x

        def union(x, y, qubit_pos):
            rx, ry = find(x), find(y)
            if rx == ry:
                return
            # Merge smaller into larger
            if rank[rx] < rank[ry]:
                rx, ry = ry, rx
            parent[ry] = rx
            parity[rx] = parity[rx] ^ parity[ry]
            if rank[rx] == rank[ry]:
                rank[rx] += 1
            forest.append((x, y, qubit_pos))

        # Phase 1: Cluster growth
        # Process edges repeatedly until all clusters have even parity.
        # Each pass allows clusters to grow by one hop. Multiple passes
        # are needed when odd clusters are separated by even clusters.
        changed = True
        while changed:
            changed = False
            # Check if any odd clusters remain
            has_odd = any(parity[find(i)] for i in range(n_nodes))
            if not has_odd:
                break

            for weight, i, j, qubit_pos in edges:
                ri, rj = find(i), find(j)
                if ri == rj:
                    continue
                if parity[ri] or parity[rj]:
                    union(i, j, qubit_pos)
                    changed = True

        # Phase 2: Peeling decoder
        # Build adjacency from forest edges
        adj = [[] for _ in range(n_nodes)]
        for x, y, qpos in forest:
            adj[x].append((y, qpos))
            adj[y].append((x, qpos))

        # Compute syndrome bits for peeling
        syn = [False] * n_nodes
        for pos in defect_set:
            if pos in node_index:
                syn[node_index[pos]] = True

        # Find leaves and peel
        degree = [len(adj[i]) for i in range(n_nodes)]
        correction = np.zeros(lattice.num_data_qubits(), dtype=np.uint8)
        idx = lattice.data_qubit_index

        # Queue of leaf nodes (never peel the virtual boundary — it absorbs)
        from collections import deque
        leaves = deque()
        for i in range(n_nodes):
            if degree[i] == 1 and i != virtual_boundary_idx:
                leaves.append(i)

        removed = [False] * n_nodes

        while leaves:
            leaf = leaves.popleft()
            if removed[leaf]:
                continue
            if degree[leaf] != 1:
                continue

            # Find the edge to the parent
            for neighbor, qpos in adj[leaf]:
                if not removed[neighbor]:
                    # If leaf has odd syndrome, flip the edge
                    if syn[leaf]:
                        if qpos in idx:
                            correction[idx[qpos]] ^= error_bit
                        # Transfer syndrome to parent
                        syn[neighbor] ^= syn[leaf]
                        syn[leaf] = False

                    # Remove leaf
                    removed[leaf] = True
                    degree[neighbor] -= 1
                    if degree[neighbor] == 1 and neighbor != virtual_boundary_idx:
                        leaves.append(neighbor)
                    break

        return correction

    def _get_boundary_points(self, lattice, stab_type):
        """Get boundary termination points (same as MWPM decoder)."""
        d = lattice.distance
        points = []

        if stab_type == "X":
            for i in range(d - 1):
                if (i + (-1)) % 2 == 1:
                    points.append((2 * i + 1, -1))
            for i in range(d - 1):
                if (i + d - 1) % 2 == 1:
                    points.append((2 * i + 1, 2 * d - 1))
            for j in range(d - 1):
                if (-1 + j) % 2 == 1:
                    points.append((-1, 2 * j + 1))
            for j in range(d - 1):
                if (d - 1 + j) % 2 == 1:
                    points.append((2 * d - 1, 2 * j + 1))
        else:
            for j in range(d - 1):
                if (-1 + j) % 2 == 0:
                    points.append((-1, 2 * j + 1))
            for j in range(d - 1):
                if (d - 1 + j) % 2 == 0:
                    points.append((2 * d - 1, 2 * j + 1))
            for i in range(d - 1):
                if (i + (-1)) % 2 == 0:
                    points.append((2 * i + 1, -1))
            for i in range(d - 1):
                if (i + d - 1) % 2 == 0:
                    points.append((2 * i + 1, 2 * d - 1))

        return points
