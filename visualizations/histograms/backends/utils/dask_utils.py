import dask.array as da
import dask.dataframe as dd
import pandas as pd
import numpy as np
from typing import Tuple, Union, Optional

class DaskUtils:
    """
    A utility class for working with Dask arrays and DataFrames.
    """
    
    def __init__(self):
        pass
    
    def create_empty_array(self, shape: Tuple[int, ...], dtype: str = 'float64') -> da.Array:
        """
        Creates an empty Dask array with the specified shape and data type.
        
        Args:
            shape (Tuple[int, ...]): Shape of the Dask array.
            dtype (str): Data type of the Dask array. Default is 'float64'.
        
        Returns:
            da.Array: An empty Dask array.
        """
        return da.empty(shape, dtype=dtype)

    def create_empty_dataframe(self, columns: list) -> dd.DataFrame:
        """
        Creates an empty Dask DataFrame with the specified columns.
        
        Args:
            columns (list): List of column names for the DataFrame.
        
        Returns:
            dd.DataFrame: An empty Dask DataFrame.
        """
        df = pd.DataFrame(columns=columns)
        return dd.from_pandas(df, npartitions=1)

    def read_csv(self, filepath: str, assume_missing: bool = False) -> dd.DataFrame:
        """
        Reads a CSV file into a Dask DataFrame.
        
        Args:
            filepath (str): Path to the CSV file.
            assuming_missing (bool, optional): Whether to assume missing values. Default is False.
        
        Returns:
            dd.DataFrame: A Dask DataFrame containing the CSV data.
        """
        return dd.read_csv(filepath, assume_missing=assume_missing)

    def to_dask_array(self, array: Union[np.ndarray, list], chunks: Optional[Union[str, int, tuple]] = 'auto') -> da.Array:
        """
        Converts a NumPy array or list to a Dask array.
        
        Args:
            array (Union[np.ndarray, list]): NumPy array or list to convert.
            chunks (Optional[Union[str, int, tuple]], optional): Chunk size for the Dask array. Default is 'auto'.
        
        Returns:
            da.Array: The converted Dask array.
        """
        return da.from_array(array, chunks=chunks)

    def to_dask_dataframe(self, dataframe: pd.DataFrame, npartitions: Optional[int] = 1) -> dd.DataFrame:
        """
        Converts a Pandas DataFrame to a Dask DataFrame.
        
        Args:
            dataframe (pd.DataFrame): Pandas DataFrame to convert.
            npartitions (Optional[int], optional): Number of partitions for the Dask DataFrame. Default is 1.
        
        Returns:
            dd.DataFrame: The converted Dask DataFrame.
        """
        return dd.from_pandas(dataframe, npartitions=npartitions)

    def to_dask_series(self, series: pd.Series, npartitions: Optional[int] = 1) -> dd.Series:
        """
        Converts a Pandas Series to a Dask Series.
        
        Args:
            series (pd.Series): Pandas Series to convert.
            npartitions (Optional[int], optional): Number of partitions for the Dask Series. Default is 1.
        
        Returns:
            dd.Series: The converted Dask Series.
        """
        return dd.from_pandas(series, npartitions=npartitions)

    def to_pandas_dataframe(self, dask_dataframe: dd.DataFrame) -> pd.DataFrame:
        """
        Converts a Dask DataFrame to a Pandas DataFrame.
        
        Args:
            dask_dataframe (dd.DataFrame): Dask DataFrame to convert.
        
        Returns:
            pd.DataFrame: The converted Pandas DataFrame.
        """
        return dask_dataframe.compute(scheduler='threads')
    
    def to_numpy_array(self, dask_array: da.Array) -> np.ndarray:
        """
        Converts a Dask array to a NumPy array.
        
        Args:
            dask_array (da.Array): Dask array to convert.
        
        Returns:
            np.ndarray: The converted NumPy array.
        """
        return dask_array.compute(scheduler='threads')
    
    def compute_values(self, dask_dataframe: dd.DataFrame) -> np.ndarray:
        """
        Computes the values of the Dask DataFrame using the 'threads' scheduler.
        
        Args:
            dask_dataframe (dd.DataFrame): The Dask DataFrame to compute.
        
        Returns:
            np.ndarray: The result of the computation.
        """
        return dask_dataframe.values.compute(scheduler='threads')