### Dask optimizations
1. **`dask_unoptimized.py`**: Import and use **`dask.array`**. Basically changing **`np.histogram`** -> **`da.histogram`**

2. **`dask_optimizations.py`**: Import and use **`dask.array`**. Computes **`self.hist`** using dask **`compute`** method.

3. **`dask_optimized.py`**: Import and use **`dask.array`**. Using a custom function **`input_histogram_values`** from a custom module **`update_histogram`** to more efficiently insert the values computed to the vtk table. **Note:** I am not seeing a massive increase, this is more optional.

4. **`dask_very_optimized.py`**: Import and use **`dask.array`**. Better chunking and using threads more efficiently.

5. **`dask_very_very_optimized.py`**: Import **`dask_histogram`** and use **`dh.factory`**. Uses **`dh.factory`**. to compute **`self.hist`** instead of **`da.histogram`**.

6. **`dask_optimized_optimized.py`**: Import **`dask_histogram`** and **`dask.array`** and use **`dh.factory`** and **`da.histogram`** to efficiently compute the histogram.

7. **`vtk_server_dask`**: The actual VTK server that implements the previous optimizations, uses dask, and also optimizes the VTK code.