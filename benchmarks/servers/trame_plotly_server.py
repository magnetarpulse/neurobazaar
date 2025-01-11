import os
import sys
import logging
import time

def get_neurobazaar_dir() -> str:
    """Returns the neurobazaar directory."""
    cwd = os.getcwd()
    index = cwd.index('neurobazaar')
    return cwd[:index + len('neurobazaar')]

neurobazaar = get_neurobazaar_dir()
sys.path.insert(0, neurobazaar)

from trame.app import get_server              # type: ignore
from trame.ui.vuetify import SinglePageLayout # type: ignore
from trame.decorators import TrameApp, change # type: ignore
from trame.widgets import vuetify, plotly     # type: ignore

import plotly.graph_objs as go                # type: ignore
import numpy as np                            # type: ignore
import dask.array as da                       # type: ignore
import dask_histogram as dh                   # type: ignore
import boost_histogram as bh                  # type: ignore

from benchmarks.utils.find_statistics import FindStatistics
from benchmarks.utils.logger import ReLogger

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

@TrameApp()
class PlotlyApp:  
    def __init__(self, data_size=1_000, ui_type = "slider ", port: int = 8080):
        self.server = get_server(client_type="vue2")
        self.state, self.ctrl = self.server.state, self.server.controller
        self.port = port
        
        self.data = da.from_array(np.random.normal(size=data_size), chunks='auto')
        self.data_min, self.data_max = self._compute_min_max(self.data)
        self.state.bins = 5 

        self.benchmark_counter = 0
        self.computing_total = []
        self.serializing_total = []

        self.find_statistics_computing = FindStatistics("computing")
        self.find_statistics_serializing = FindStatistics("serializing")

        if ui_type == "slider":
            print("Slider interactor was chosen")
            self._setup_slider_layout()
        elif ui_type == "input":
            print("Input interactor was chosen")
            self._setup_input_layout()
        else:
            raise ValueError("Invalid ui_type")
        
        print("Data size: " + str(data_size))
        
        self._initial_histogram()

    def _plotly_histogram(self):
        """Create Plotly histogram more efficiently"""
        self.benchmark_counter += 1

        compute_start = time.time()
        hist, bin_edges = self._compute_hist(self.data, self.state.bins)
        compute_end = time.time()

        print(f"Benchmark {self.benchmark_counter} -> Computing Time: {compute_end - compute_start}")
        self.computing_total.append(compute_end - compute_start)
        
        serialize_start = time.time()
        if hist is None or bin_edges is None:
            return None

        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        fig = go.Figure(data=[go.Bar(
            x=bin_centers,
            y=hist,
            width=(bin_edges[1] - bin_edges[0]),
            marker_color='blue',
            opacity=0.7,
        )])

        fig.update_layout(
            title=f'Histogram with {self.state.bins} Bins',
            xaxis_title='Value',
            yaxis_title='Frequency',
            bargap=0.1,
        )
        serialize_end = time.time()

        print(f"Benchmark {self.benchmark_counter} -> Serializing Time: {serialize_end - serialize_start}")
        self.serializing_total.append(serialize_end - serialize_start)

        return fig

    def _compute_min_max(self, dask_data):
        """Compute min and max efficiently"""
        return dask_data.min().compute(), dask_data.max().compute()
    
    def _compute_hist(self, dask_data, bins):
        """Optimize histogram computation"""
        try:
            bins = int(bins)
            dask_hist = dh.factory(dask_data, axes=(bh.axis.Regular(bins, self.data_min, self.data_max),))
            hist_result = dask_hist.persist().compute(scheduler='threads')
            frequencies = hist_result.to_numpy()[0]
            
            bin_edges = np.linspace(self.data_min, self.data_max, bins + 1)
            return frequencies, bin_edges
        
        except Exception as e:
            logging.error(f"Histogram computation error: {e}")
            return None, None
    
    def _initial_histogram(self):
        """Initial histogram rendering"""
        self.ctrl.figure_update(self._plotly_histogram())
    
    @change("bins")
    def _on_bins_change(self, **kwargs):
        """Efficiently handle bin changes"""
        logging.info(f"Bins changed to: {self.state.bins}")
        self.ctrl.figure_update(self._plotly_histogram())
    
    def _setup_slider_layout(self):
        """Setup layout with slider"""
        with SinglePageLayout(self.server) as layout:
            layout.title.set_text("Optimized Interactive Histogram")
            
            with layout.toolbar:
                vuetify.VSpacer()
                vuetify.VSlider(
                    v_model=("bins", 5), 
                    min=1,
                    max=100,
                    label="Number of Bins",  
                    hide_details=False,
                    dense=True,
                    thumb_label=True,  
                    thumb_size=20, 
                    style="padding-top: 20px;", 
                )
                
            with layout.content:
                with vuetify.VContainer(fluid=True, classes="fill-height"):
                    figure = plotly.Figure(
                        style="width: 100%; height: 100%;",
                        display_logo=False,
                        display_mode_bar="true",
                    )
                    self.server.controller.figure_update = figure.update
    
    def _setup_input_layout(self):
        """Setup input layout"""
        with SinglePageLayout(self.server) as layout:
            layout.title.set_text("Optimized Interactive Histogram")
            
            with layout.toolbar:
                vuetify.VSpacer()
                vuetify.VTextField(
                    v_model=("bins", 5),  
                    label="Number of Bins",
                    type="number",
                    style="padding-top: 20px;",
                )
                
            with layout.content:
                with vuetify.VContainer(fluid=True, classes="fill-height"):
                    figure = plotly.Figure(
                        style="width: 100%; height: 100%;",
                        display_logo=False,
                        display_mode_bar="true",
                    )
                    self.server.controller.figure_update = figure.update

    def start_now(self):
        """Start server now"""
        self.server.start(auth_key="key", port = self.port)

    async def start_later(self):
        """Start server later"""
        return await self.server.start(exec_mode="task", port=self.port, auth_key="key")
    
    def stop(self):
        """Stop server"""
        self.server.stop()

        # Find statistics for computing 
        self.find_statistics_computing.find_average(self.computing_total)
        self.find_statistics_computing.find_median(self.computing_total)
        self.find_statistics_computing.find_standard_deviation(self.computing_total)
        self.find_statistics_computing.find_quartiles(self.computing_total)
        self.find_statistics_computing.find_length(self.computing_total)

        # Find statistics for serializing
        self.find_statistics_serializing.find_average(self.serializing_total)
        self.find_statistics_serializing.find_median(self.serializing_total)
        self.find_statistics_serializing.find_standard_deviation(self.serializing_total)
        self.find_statistics_serializing.find_quartiles(self.serializing_total)
        self.find_statistics_serializing.find_length(self.serializing_total)

if __name__ == "__main__":
    logging_statistics = ReLogger(log_file="plotly_server.log", create_dir="results/render")
    logging_statistics.run()
    plotly_app = PlotlyApp(data_size=1_000_000_000, ui_type="input")  
    plotly_app.start_now()
    plotly_app.stop()
    logging_statistics.stop()