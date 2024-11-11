import dask.array as da
import dask_histogram as dh
import boost_histogram as bh
import numpy as np
from dask.distributed import Client
from typing import Tuple, Union, Optional

class BoostHistogramProcessor:
    """
    A class to process histogram data using Boost-histogram and Dask.

    Attributes:
        hist (np.ndarray): The histogram frequencies.
        bin_edges (np.ndarray): The bin edges for the histogram.
        data_min (float): The minimum value of the data.
        data_max (float): The maximum value of the data.
        hist_cache (dict): Cache to store computed histograms.
        min_max_cache (dict): Cache to store computed min/max values.
    """

    __slots__ = ['hist', 'bin_edges', 'data_min', 'data_max', 'hist_cache', 'min_max_cache']
    
    def __init__(self):
        self.hist = None
        self.bin_edges = None
        self.data_min = None
        self.data_max = None
        self.hist_cache = {}
        self.min_max_cache = {}

    def compute_histogram(self, dask_data: da.Array, bins: int, data_min: Optional[Union[int, float]] = None, 
                         data_max: Optional[Union[int, float]] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes histogram data (da.Array) using Boost-histogram.
        
        Args:
            dask_data (da.Array): Input data for the histogram.
            bins (int): Number of bins for the histogram.
            data_min (Optional[Union[int, float]]): Minimum value for histogram range (optional, can be int or float).
            data_max (Optional[Union[int, float]]): Maximum value for histogram range (optional, can be int or float).
        
        Returns:
            tuple: A tuple containing the values (frequencies) of the histogram and bin edges.
        """
        if dask_data.size == 0:
            return np.zeros(bins), np.linspace(0, 1, bins + 1)

        if not isinstance(dask_data, da.Array):
            dask_data = da.from_array(dask_data, chunks='auto')
        
        if data_min is not None and data_max is not None:
            self.data_min = data_min
            self.data_max = data_max
        else:
            array_id = dask_data.name
            if array_id in self.min_max_cache:
                self.data_min, self.data_max = self.min_max_cache[array_id]
            else:
                self.data_min, self.data_max = self._get_min_max_values(dask_data)
                self.min_max_cache[array_id] = (self.data_min, self.data_max)

        key = (bins, self.data_min, self.data_max)
        
        if key in self.hist_cache:
            self.hist, self.bin_edges = self.hist_cache[key]
        else:
            dask_hist = dh.factory(dask_data, axes=(bh.axis.Regular(bins, self.data_min, self.data_max+1),))
            dask_hist = dask_hist.persist()
            
            self.hist = self._to_numpy_frequencies(dask_hist)
            _, self.bin_edges = da.histogram(dask_data, bins=bins, range=(self.data_min, self.data_max))
            
            self.hist_cache[key] = (self.hist, self.bin_edges)

        if not isinstance(self.hist, np.ndarray):
            self.hist = self._to_numpy(self.hist)

        return self.hist, self.bin_edges

    def _to_numpy_frequencies(self, dask_object: dh.AggHistogram) -> np.ndarray:
        """
        Converts the results (dh.AggHistogram) computed by Boost-histogram and Dask to a NumPy array of frequencies.

        Args:
            dask_object (dh.AggHistogram): The Dask AggHistogram object.

        Returns:
            np.ndarray: The converted NumPy array of frequencies.
        """
        result = dask_object.compute(scheduler='threads', num_workers=21) 
        frequencies = result.to_numpy()[0]
        return frequencies

    def _to_numpy_frequencies_distributed(self, dask_object: dh.AggHistogram) -> np.ndarray:
        """
        Converts the results (dh.AggHistogram) computed by Boost-histogram and Dask to a NumPy array of frequencies using Dask distributed.

        Args:
            dask_object (dh.AggHistogram): The Dask AggHistogram object.

        Returns:
            np.ndarray: The converted NumPy array of frequencies.
        """
        client = Client()
        dask_hist = client.compute(dask_object)
        frequencies = dask_hist.result().to_numpy()[0]
        return frequencies

    def _to_numpy(self, dask_object: da.Array) -> np.ndarray:
        """
        Converts a Dask array object to a NumPy array.

        Args:
            dask_object (da.Array): The Dask array object.

        Returns:
            np.ndarray: The converted NumPy array.
        """
        result = dask_object.compute(scheduler='threads', num_workers=21) 
        return result
    
    def _get_min_max_values(self, dask_data: da.Array) -> Tuple[float, float]:
        """
        Computes the minimum and maximum values of data using Dask.

        Args:
            dask_data (da.Array): Input data to compute min and max values.

        Returns:
            Tuple[float, float]: The minimum and maximum values of the data.
        """
        if dask_data.size == 0:
            return 0, 1

        if not isinstance(dask_data, da.Array):
            dask_data = da.from_array(dask_data, chunks='auto')

        data_min = dask_data.min().compute()
        data_max = dask_data.max().compute()
        
        return data_min, data_max
    
    def clear_cache(self) -> None:
        """
        Clears the cache for computed histograms and min/max values.
        """
        self.data_min = None
        self.data_max = None
        self.hist_cache.clear()
        self.min_max_cache.clear()