import pandas as pd
from io import BytesIO
import base64

from trame.app import get_server

import numpy as np

import dask.array as da
import dask_histogram as dh
import boost_histogram as bh

import plotly.graph_objects as go

import time

# -----------------------------------------------------------------------------
# Histogram Application
# -----------------------------------------------------------------------------

class HistogramApp:
    def __init__(self):
        self.server = get_server()
        self.state = self.server.state

        self.np_data = np.random.normal(size=1_000_000_000)

        self.dask_data = da.empty(shape=(0,))
        
        self.state.bins = 5 
        self.state.file_input = None
        self.state.selected_column = None 

        self.state.figure_data = None
        self.previous_figure_data = None

        self.data_min = None
        self.data_max = None
        self.check_method_invoked_min_max = 0

        self.state.change("bins")(self.on_bins_change)
        self.state.change("file_input")(self.on_file_input_change)
        self.state.change("selected_column")(self.on_selected_column_change)

    # -----------------------------------------------------------------------------
    # Method to update the histogram
    # -----------------------------------------------------------------------------

    def update_histogram(self, bins):
        start_time_to_update_histogram = time.time()

        self.plotly_compute_min_max(self.np_data)

        self.compute_histogram_data_with_dask(self.np_data, bins)
        x = (self.bin_edges[:-1] + self.bin_edges[1:]) / 2
        bin_width = self.bin_edges[1] - self.bin_edges[0]

        fig = go.Figure(data=[go.Bar(x=x, y=self.hist, width=bin_width)])
        fig.update_layout(title_text='Histogram', xaxis_title_text='Value (feature)', yaxis_title_text='Frequency')

        start_time_to_prepare_figure_for_client = time.time()
        new_figure_data = fig.to_json()
        end_time_to_prepare_figure_for_client = time.time()

        if new_figure_data != self.previous_figure_data:
            self.previous_figure_data = new_figure_data

        self.state.figure_data = new_figure_data

        end_time_to_update_histogram = time.time()
        print(f"Preparing the figure for the client took {end_time_to_prepare_figure_for_client - start_time_to_prepare_figure_for_client} seconds")
        print(f"Updating the histogram, after all computations and preparations, took {end_time_to_update_histogram - start_time_to_update_histogram} seconds")
    
    # ---------------------------------------------------------------------------------------------
    # Method using Dask to compute histogram data
    # ---------------------------------------------------------------------------------------------
    
    def compute_histogram_data_with_dask(self, dask_data, bins):
        computation_type = "Dask (threaded scheduler)"
        
        if not isinstance(dask_data, da.Array):
            self.np_data = da.from_array(dask_data, chunks=10000000)
            print("Converting NumPy array to Dask array")
        else:
            print("Dask array already exists")
            self.np_data = dask_data
        
        if self.data_min is None or self.data_max is None:
            self.data_min, self.data_max = self.plotly_compute_min_max(self.np_data)
        
        start_time_to_calculate_histogram = time.time()
        
        dask_hist = dh.factory(self.np_data, axes=(bh.axis.Regular(bins, self.data_min, self.data_max),))
        dask_hist = dask_hist.persist() 
        hist_result = self.convert_agghistogram_to_numpy_array_of_frequencies(dask_hist)
        self.hist = hist_result.view()
        _, self.bin_edges = da.histogram(self.np_data, bins=bins, range=(self.data_min, self.data_max))
        
        end_time_to_calculate_histogram = time.time()

        if not isinstance(self.hist, np.ndarray):
            self.hist = self.convert_dask_to_numpy(self.hist)

        print(f"Calculating the histogram using {computation_type} took {end_time_to_calculate_histogram - start_time_to_calculate_histogram} seconds")

    # ---------------------------------------------------------------------------------------------
    # Method using Dask compute method to convert AggHistogram to a NumPy array of frequencies
    # ---------------------------------------------------------------------------------------------

    def convert_agghistogram_to_numpy_array_of_frequencies(self, dask_object):
        result = dask_object.compute(scheduler='threads', num_workers=21) 
        frequencies = result.to_numpy()[0]
        return frequencies

    # ---------------------------------------------------------------------------------------------
    # Method using Dask compute method to convert Dask object to NumPy array
    # ---------------------------------------------------------------------------------------------

    def convert_dask_to_numpy(self, dask_object):
        result = dask_object.compute(scheduler='threads', num_workers=21) 
        return result

    # -----------------------------------------------------------------------------
    # Method to compute the minimum and maximum of the dataset
    # -----------------------------------------------------------------------------

    def plotly_compute_min_max(self, data):
        if self.data_min is None and self.data_max is None:
            self.data_min = data.min()
            self.data_max = data.max()
            self.check_method_invoked_min_max += 1
            print(f"Computing min and max. This method has been invoked {self.check_method_invoked_min_max} times.")
            return self.data_min, self.data_max
        else:
            return None, None

    # -----------------------------------------------------------------------------
    # State change handlers
    # -----------------------------------------------------------------------------
    
    def on_bins_change(self, bins, **kwargs):
        self.update_histogram(bins)
    
    def on_file_input_change(self, file_input, **kwargs):
        if file_input:
            try:             
                content = BytesIO(base64.b64decode(file_input['content']))
                df = pd.read_csv(content)
                
                self.state.column_options = df.columns.tolist()
                self.state.selected_column = self.state.column_options[0] 
                self.np_data = df[self.state.selected_column].values
                
                self.update_histogram()
            except KeyError as e:
                print(f"KeyError: {e} - Check the structure of file_input and the CSV file.")
            except Exception as e:
                print(f"An error occurred (file_input): {e}")

    def on_selected_column_change(self, selected_column, **kwargs):
        if self.state.file_input and selected_column:
            try:
                content = base64.b64decode(self.state.file_input['content'])
                df = pd.read_csv(BytesIO(content))

                self.np_data = df[selected_column].values

                self.update_histogram()
            except KeyError as e:
                print(f"KeyError: {e} - Check the structure of the CSV file.")
            except Exception as e:
                print(f"An error occurred (selected_column): {e}")

    # -----------------------------------------------------------------------------
    # Start server method
    # -----------------------------------------------------------------------------

    def start(self):
        self.server.start()

# -----------------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    app = HistogramApp()
    app.start()