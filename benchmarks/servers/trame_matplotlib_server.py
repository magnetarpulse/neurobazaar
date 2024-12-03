import asyncio
import numpy as np
import matplotlib.pyplot as plt
import time

from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vuetify, trame, matplotlib

# -----------------------------------------------------------------------------
# Data Generation (Normal Distribution) using numpy
# -----------------------------------------------------------------------------

np.random.seed(42)
data = np.random.normal(loc=0, scale=1, size=1000)

# -----------------------------------------------------------------------------
# Trame setup
# -----------------------------------------------------------------------------

server = get_server(client_type="vue2")
state, ctrl = server.state, server.controller

# -----------------------------------------------------------------------------
# Histogram Function
# -----------------------------------------------------------------------------

def figure_size():
    if state.figure_size is None:
        return {}

    dpi = state.figure_size.get("dpi")
    rect = state.figure_size.get("size")
    w_inch = rect.get("width") / dpi / 2
    h_inch = rect.get("height") / dpi / 2

    return {
        "figsize": (w_inch, h_inch),
        "dpi": dpi,
    }

def create_histogram():
    plt.close("all")
    
    # Get the number of bins from state
    num_bins = state.num_bins
    
    # Create the figure and axis
    fig, ax = plt.subplots(**figure_size())
    
    # Create histogram
    ax.hist(data, bins=num_bins, edgecolor='black', alpha=0.7)
    
    # Set labels and title
    ax.set_title(f'Histogram with {num_bins} Bins', fontsize=14)
    ax.set_xlabel('Value')
    ax.set_ylabel('Frequency')
    
    return fig

# -----------------------------------------------------------------------------
# Timing Function
# -----------------------------------------------------------------------------

def time_histogram_render():
    start_time = time.time()
    ctrl.update_figure(create_histogram())
    end_time = time.time()
    print(f"Histogram render time: {end_time - start_time:.2f} seconds")

# -----------------------------------------------------------------------------
# Callbacks
# -----------------------------------------------------------------------------

@state.change("num_bins", "figure_size")
def update_histogram(num_bins, **kwargs):
    print(f"Slider changed to: {num_bins}")
    time_histogram_render()

# -----------------------------------------------------------------------------
# Initial State
# -----------------------------------------------------------------------------

state.num_bins = 30 

# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------

state.trame__title = "Interactive Histogram"

with SinglePageLayout(server) as layout:
    layout.title.set_text("Interactive Histogram with Bin Slider")

    with layout.toolbar:
        vuetify.VSpacer()
        
        vuetify.VSlider(
            v_model=("num_bins", 30),  
            min=1,  
            max=100,  
            step=1,
            label="Number of Bins",
            thumb_label=True,
            hide_details=False,
        )

    with layout.content:
        with vuetify.VContainer(fluid=True, classes="fill-height pa-0 ma-0"):
            with trame.SizeObserver("figure_size"):
                html_figure = matplotlib.Figure(style="position: absolute")
                ctrl.update_figure = html_figure.update

async def start_later():
    await server.start(exec_mode="task", auth_key="key")

if __name__ == "__main__":
    asyncio.run(start_later())