import pandas as pd
from io import BytesIO
import base64

from trame.app import get_server

import numpy as np

import plotly.graph_objects as go

import time

# -----------------------------------------------------------------------------
# Histogram Application
# -----------------------------------------------------------------------------

class HistogramApp:
    def __init__(self):
        self.server = get_server()
        self.state = self.server.state

        self.np_data = np.random.normal(size=360_000)
        
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

    def update_histogram(self):
        start_time_to_update_histogram = time.time()

        self.plotly_compute_min_max(self.np_data)

        fig = go.Figure(data=[go.Histogram(x=self.np_data, nbinsx=self.server.state.bins, histnorm='probability density')])
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
        self.update_histogram()
    
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