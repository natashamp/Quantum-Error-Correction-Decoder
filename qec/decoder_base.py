"""Abstract base class for QEC decoders."""

from abc import ABC, abstractmethod
import numpy as np


class DecoderBase(ABC):

    @abstractmethod
    def decode(self, lattice, syndrome):
        """Decode a syndrome and return a correction.

        Args:
            lattice: SurfaceCodeLattice instance.
            syndrome: dict with "x_defects" and "z_defects" lists.

        Returns:
            np.ndarray of Pauli corrections, same shape as error array.
        """
        pass

    @abstractmethod
    def name(self):
        """Return the decoder's display name."""
        pass
