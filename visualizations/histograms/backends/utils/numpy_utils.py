import numpy as np
from typing import Tuple

class NumpyUtils:
    """
    A utility class for working with NumPy arrays.
    """
    
    def __init__(self):
        pass
    
    def create_empty_histogram(self, bins: int, range: Tuple[float, float]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Creates an empty histogram with the specified number of bins and range.
        
        Args:
            bins (int): Number of bins for the histogram.
            range (Tuple[float, float]): Range of the histogram (min, max).
        
        Returns:
            Tuple[np.ndarray, np.ndarray]: The histogram frequencies (initialized to zero) and the bin edges.
        """
        hist = np.zeros(bins)
        bin_edges = np.linspace(range[0], range[1], bins + 1)
        return hist, bin_edges

    def create_empty_array(self, shape: Tuple[int, ...], dtype: str = 'float64') -> np.ndarray:
        """
        Creates an empty NumPy array with the specified shape and data type.
        
        Args:
            shape (Tuple[int, ...]): Shape of the NumPy array.
            dtype (str): Data type of the NumPy array. Default is 'float64'.
        
        Returns:
            np.ndarray: An empty NumPy array.
        """
        return np.empty(shape, dtype=dtype)