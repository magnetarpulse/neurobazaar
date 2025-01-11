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

from trame.app import get_server                 # type: ignore
from trame.ui.vuetify import SinglePageLayout    # type: ignore
from trame.decorators import TrameApp, change    # type: ignore
from trame.widgets import vuetify,  matplotlib   # type: ignore

import matplotlib.pyplot as plt                  # type: ignore
import numpy as np                               # type: ignore   
import dask.array as da                          # type: ignore
import dask_histogram as dh                      # type: ignore
import boost_histogram as bh                     # type: ignore

from benchmarks.utils.find_statistics import FindStatistics
from benchmarks.utils.logger import ReLogger
from benchmarks.utils.csv_reporter import CsvReporter

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

@TrameApp()
class MatplotlibApp:
    def __init__(self, data_size=1_000, ui_type="slider", port: int = 8080):
        self.server = get_server(client_type="vue2")
        self.state, self.ctrl = self.server.state, self.server.controller
        self.port = port

        if isinstance(data_size, int):
            print("Data size is an integer")
            self.data = da.from_array(np.random.normal(size=data_size), chunks='auto')
        elif isinstance(data_size, np.ndarray):
            print("Data size is a numpy array")
            self.data = da.from_array(data_size, chunks='auto')
        elif isinstance(data_size, list):
            print("Data size is a list of integers")
            self.data = da.from_array(np.array(data_size), chunks='auto')
        else:
            raise ValueError("data_size must be an integer, numpy array, or list of integers")

        self.data_min, self.data_max = self._compute_min_max(self.data)
        self.state.bins = 5
        self.state.figure_size = {
            "dpi": 100,
            "size": {"width": 1650, "height": 750},
        }

        self.benchmark_counter = 0
        self.computing_total = []
        self.serializing_total = []
        self.serialize_buffer = 0

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

    def _matplotlib_histogram(self):
        """Create Matplotlib histogram more efficiently"""
        self.benchmark_counter += 1

        compute_start = time.time()
        self.hist, self.bin_edges = self._compute_hist(self.data, self.state.bins)
        compute_end = time.time()

        print(f"Benchmark {self.benchmark_counter} -> Computing Time: {compute_end - compute_start}")
        self.computing_total.append(compute_end - compute_start)
        
        serialize_start = time.time()
        if self.hist is None or self.bin_edges is None:
            return None

        size_params = self.figure_size()
        fig, ax = plt.subplots(**size_params)

        fig.tight_layout()
        ax.bar(self.bin_edges[:-1], self.hist, width=np.diff(self.bin_edges), edgecolor='black')
        ax.set_title(f'Histogram with {self.state.bins} Bins')
        ax.set_xlabel('Value')
        ax.set_ylabel('Frequency')
        serialize_end = time.time()

        self.serialize_buffer = serialize_end - serialize_start
        
        plt.close(fig)  
        
        return fig
    
    def _update_histogram(self):
        """Update histogram"""
        fig = self._matplotlib_histogram()

        serialize_start = time.time()
        self.ctrl.update_figure(fig)
        serialize_end = time.time()
        
        print(f"Benchmark {self.benchmark_counter} -> Serializing Time: {serialize_end - serialize_start}")
        self.serialize_buffer += serialize_end - serialize_start
        self.serializing_total.append(self.serialize_buffer)

        self.serialize_buffer = 0
    
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
        """Initialize histogram"""
        self._matplotlib_histogram()

    @change("bins")
    def _on_bins_change(self, **kwargs):
        """Efficiently handle bin changes"""
        logging.info(f"Bins changed to: {self.state.bins}")
        self._update_histogram()

    def _setup_slider_layout(self):
        """Setup slider layout"""
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
                    html_figure = matplotlib.Figure()
                    self.ctrl.update_figure = html_figure.update
        
    def _setup_input_layout(self):
        """Setup input layout"""
        with SinglePageLayout(self.server) as layout:
            layout.title.set_text("Optimized Interactive Histogram")
            
            with layout.toolbar:
                vuetify.VSpacer()
                vuetify.VTextField(
                    v_model=("bins", 5),
                    label="Number of Bins",
                    dense=True,
                    style="padding-top: 20px;",
                )
                
            with layout.content:
                with vuetify.VContainer(fluid=True, classes="fill-height"):
                    html_figure = matplotlib.Figure()
                    self.ctrl.update_figure = html_figure.update

    def figure_size(self):
        """Get figure size"""
        if self.state.figure_size is None:
            return {}
        
        dpi = self.state.figure_size.get("dpi")
        rect = self.state.figure_size.get("size")
        w_inch = rect.get("width") / dpi
        h_inch = rect.get("height") / dpi
        
        return {
            "figsize": (w_inch, h_inch),
            "dpi": dpi,
        }

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
    csv_reporter = CsvReporter("/home/huy/neurobazaar/datastore/.datasets/a69cd7e7-d688-421a-911b-4c840683bcab_UCI_ParkinsonsTeleMonitoring.csv")
    logging_statistics = ReLogger(log_file="matplotlib_server_rd.log", create_dir="results")
    logging_statistics.run()
    # matplotlib_app = MatplotlibApp(data_size=200_000_000, ui_type="input")
    matplotlib_app = MatplotlibApp(data_size=csv_reporter.search("NHR"), ui_type="input")
    matplotlib_app.start_now()
    matplotlib_app.stop()
    logging_statistics.stop()