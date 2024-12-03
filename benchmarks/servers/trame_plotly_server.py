import logging

from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.decorators import TrameApp, change
from trame.widgets import vuetify, plotly

import plotly.graph_objs as go
import numpy as np
import dask.array as da
import dask_histogram as dh
import boost_histogram as bh

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

@TrameApp()
class PlotlyApp:  
    def __init__(self, data_size=1_000):
        self.server = get_server(client_type="vue2")
        self.state, self.ctrl = self.server.state, self.server.controller
        
        self.data = da.from_array(np.random.normal(size=data_size), chunks='auto')
        
        self.data_min, self.data_max = self._compute_min_max(self.data)
        
        self.state.bins = 5 
        self.last_fig = None  

        self.setup_layout()
        self._initial_histogram()

    def _compute_min_max(self, dask_data):
        """Compute min and max efficiently"""
        return dask_data.min().compute(), dask_data.max().compute()
    
    def _compute_hist(self, dask_data, bins):
        """Optimize histogram computation"""
        try:
            dask_hist = dh.factory(dask_data, axes=(bh.axis.Regular(bins, self.data_min, self.data_max),))
            hist_result = dask_hist.persist().compute(scheduler='threads')
            frequencies = hist_result.to_numpy()[0]
            
            bin_edges = np.linspace(self.data_min, self.data_max, bins + 1)
            return frequencies, bin_edges
        
        except Exception as e:
            logging.error(f"Histogram computation error: {e}")
            return None, None
    
    def histogram_plotly(self):
        """Create Plotly histogram more efficiently"""
        hist, bin_edges = self._compute_hist(self.data, self.state.bins)
        
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

        return fig
    
    def _initial_histogram(self):
        """Initial histogram rendering"""
        self.ctrl.figure_update(self.histogram_plotly())
    
    @change("bins")
    def on_bins_change(self, **kwargs):
        """Efficiently handle bin changes"""
        logging.info(f"Bins changed to: {self.state.bins}")
        self.ctrl.figure_update(self.histogram_plotly())
    
    def setup_layout(self):
        with SinglePageLayout(self.server) as layout:
            layout.title.set_text("Optimized Interactive Histogram")
            
            with layout.toolbar:
                vuetify.VSpacer()
                vuetify.VSlider(
                    v_model=("bins", 5),  
                    min=1,  
                    max=100,  
                    step=1,
                    label="Number of Bins",
                    thumb_label=True,
                    hide_details=False,
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
        self.server.start(auth_key="key")

if __name__ == "__main__":
    plotly_app = PlotlyApp(data_size=1_000_000_000)  
    plotly_app.start_now()