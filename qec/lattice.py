"""
Rotated surface code lattice representation.

Coordinate convention for distance d:
- Data qubits at (2r, 2c) for r, c = 0..d-1  (both coordinates even)
- Interior stabilizer faces at (2i+1, 2j+1) for i, j = 0..d-2
  Each touches 4 data qubits: (2i,2j), (2i,2j+2), (2i+2,2j), (2i+2,2j+2)
- Face type determined by checkerboard: face index (i,j) is
    Z-type if (i+j) % 2 == 0
    X-type if (i+j) % 2 == 1
- Boundary stabilizers (weight-2) extend the checkerboard to the edges:
    North (i=-1): Z-type faces at (-1, 2j+1) touching (0,2j) and (0,2j+2)
    South (i=d-1): Z-type faces at (2d-1, 2j+1) touching (2d-2,2j) and (2d-2,2j+2)
    West  (j=-1): X-type faces at (2i+1, -1) touching (2i,0) and (2i+2,0)
    East  (j=d-1): X-type faces at (2i+1, 2d-1) touching (2i,2d-2) and (2i+2,2d-2)

This gives d^2 data qubits and d^2 - 1 stabilizers ((d^2-1)/2 of each type).
"""


class SurfaceCodeLattice:

    def __init__(self, distance):
        if distance < 3 or distance % 2 == 0:
            raise ValueError("Distance must be an odd integer >= 3")

        self.distance = distance

        self.data_qubits = []
        self.x_stabilizers = []
        self.z_stabilizers = []

        self.x_stabilizer_qubits = {}  # stab_pos -> [data qubit positions]
        self.z_stabilizer_qubits = {}

        self.data_qubit_index = {}  # position -> integer index

        self._build()

    def _build(self):
        d = self.distance

        # Data qubits at (2r, 2c)
        for r in range(d):
            for c in range(d):
                self.data_qubits.append((2 * r, 2 * c))

        self.data_qubits.sort()
        self.data_qubit_index = {pos: i for i, pos in enumerate(self.data_qubits)}

        # Interior stabilizers at face (i, j) for i,j = 0..d-2
        for i in range(d - 1):
            for j in range(d - 1):
                coord = (2 * i + 1, 2 * j + 1)
                neighbors = [
                    (2 * i, 2 * j), (2 * i, 2 * j + 2),
                    (2 * i + 2, 2 * j), (2 * i + 2, 2 * j + 2),
                ]
                if (i + j) % 2 == 0:
                    self.z_stabilizers.append(coord)
                    self.z_stabilizer_qubits[coord] = neighbors
                else:
                    self.x_stabilizers.append(coord)
                    self.x_stabilizer_qubits[coord] = neighbors

        # Boundary stabilizers (weight-2)
        # North boundary: i = -1, only Z-type faces (where (-1+j) % 2 == 0, i.e. j even)
        # Wait: Z if (i+j)%2==0, so (-1+j)%2==0 means j is odd
        for j in range(d - 1):
            if (-1 + j) % 2 == 0:  # Z-type
                coord = (-1, 2 * j + 1)
                neighbors = [(0, 2 * j), (0, 2 * j + 2)]
                self.z_stabilizers.append(coord)
                self.z_stabilizer_qubits[coord] = neighbors

        # South boundary: i = d-1
        for j in range(d - 1):
            if (d - 1 + j) % 2 == 0:  # Z-type
                coord = (2 * d - 1, 2 * j + 1)
                neighbors = [(2 * d - 2, 2 * j), (2 * d - 2, 2 * j + 2)]
                self.z_stabilizers.append(coord)
                self.z_stabilizer_qubits[coord] = neighbors

        # West boundary: j = -1, only X-type faces (where (i-1) % 2 == 1, i.e. i even)
        for i in range(d - 1):
            if (i + (-1)) % 2 == 1:  # X-type
                coord = (2 * i + 1, -1)
                neighbors = [(2 * i, 0), (2 * i + 2, 0)]
                self.x_stabilizers.append(coord)
                self.x_stabilizer_qubits[coord] = neighbors

        # East boundary: j = d-1
        for i in range(d - 1):
            if (i + d - 1) % 2 == 1:  # X-type
                coord = (2 * i + 1, 2 * d - 1)
                neighbors = [(2 * i, 2 * d - 2), (2 * i + 2, 2 * d - 2)]
                self.x_stabilizers.append(coord)
                self.x_stabilizer_qubits[coord] = neighbors

        self.x_stabilizers.sort()
        self.z_stabilizers.sort()

    def get_neighbors(self, stabilizer_pos):
        """Return data qubit positions for a given stabilizer."""
        if stabilizer_pos in self.x_stabilizer_qubits:
            return self.x_stabilizer_qubits[stabilizer_pos]
        if stabilizer_pos in self.z_stabilizer_qubits:
            return self.z_stabilizer_qubits[stabilizer_pos]
        raise ValueError(f"Unknown stabilizer position: {stabilizer_pos}")

    def get_stabilizers_for_qubit(self, qubit_pos, stab_type="X"):
        """Return stabilizer positions that act on a given data qubit."""
        stab_map = (self.x_stabilizer_qubits if stab_type == "X"
                    else self.z_stabilizer_qubits)
        return [s for s, qubits in stab_map.items() if qubit_pos in qubits]

    def num_data_qubits(self):
        return len(self.data_qubits)

    def to_dict(self):
        """JSON-serializable representation for the frontend."""
        return {
            "distance": self.distance,
            "data_qubits": [list(q) for q in self.data_qubits],
            "x_stabilizers": [list(s) for s in self.x_stabilizers],
            "z_stabilizers": [list(s) for s in self.z_stabilizers],
            "x_stabilizer_qubits": {
                str(k): [list(v) for v in vs]
                for k, vs in self.x_stabilizer_qubits.items()
            },
            "z_stabilizer_qubits": {
                str(k): [list(v) for v in vs]
                for k, vs in self.z_stabilizer_qubits.items()
            },
            "data_qubit_index": {
                str(k): v for k, v in self.data_qubit_index.items()
            },
        }
