import os
import sys
import asyncio
import subprocess
import signal
import threading

import inspect
import traceback
import subprocess

from trame.app import get_server
from trame.decorators import TrameApp, change
from trame.widgets import vtk, vuetify
from trame.ui.vuetify import SinglePageLayout
import vtk as standard_vtk

import numpy as np
import dask.dataframe as dd
import dask.array as da
import dask_histogram as dh
import boost_histogram as bh

from dask.distributed import Client
import tempfile
import time
from abc import abstractmethod

# ---------------------------------------------------------------------------------------------
# Histogram Application Class
# ---------------------------------------------------------------------------------------------
@TrameApp()
class BaseHistogramApp:
    def __init__(self, name, port, np_data=None):
        self.server = get_server(name, client_type="vue2")
        self.port = port
        self.np_data = np_data if np_data is not None else np.random.normal(size=1_000)
        self.dask_data = da.empty(shape=(0,))
        self.server.state.bins = 5
        self.server.state.file_input = None
        self.server.state.selected_column = None
        self.server.state.column_options = []

        self.hist_cache = {}
        self.data_min = None
        self.data_max = None
        self.data_changed = True
        self.setup_ui()

        self.histogram_vtk()
        self.client_view = vtk.VtkRemoteView(self.renderWindow, trame_server=self.server, ref="view")
        self.setup_layout()

    # ---------------------------------------------------------------------------------------------
    # Method using VTK to define histogram from data and render it
    # ---------------------------------------------------------------------------------------------
    def histogram_vtk(self):
        self.compute_histogram_data_with_dask(self.np_data, self.server.state.bins)

        self.table = standard_vtk.vtkTable()
        self.arrX = standard_vtk.vtkFloatArray()
        self.arrX.SetName("X Axis")
        self.arrY = standard_vtk.vtkFloatArray()
        self.arrY.SetName("Frequency")

        for i in range(len(self.hist)):
            self.arrX.InsertNextValue(self.bin_edges[i])
            self.arrY.InsertNextValue(self.hist[i])

        self.table.AddColumn(self.arrX)
        self.table.AddColumn(self.arrY)

        self.plot = standard_vtk.vtkPlotBar()
        self.plot.SetInputData(self.table)
        self.plot.SetInputArray(0, "X Axis")
        self.plot.SetInputArray(1, "Frequency")
        self.plot.SetColor(0, 0, 0, 255)

        outline = standard_vtk.vtkPen()
        outline.SetColor(255, 255, 255, 255)
        self.plot.SetPen(outline)

        self.chart = standard_vtk.vtkChartXY()
        self.chart.SetBarWidthFraction(1.0)
        self.chart.GetAxis(0).SetTitle("Frequency")
        self.chart.GetAxis(1).SetTitle("Feature")
        self.chart.GetAxis(1).SetMinimum(0)
        self.chart.GetAxis(1).SetMaximum(7000)
        self.chart.GetAxis(1).SetBehavior(standard_vtk.vtkAxis.FIXED)
        self.chart.AddPlot(self.plot)

        self.view = standard_vtk.vtkContextView()
        self.view.GetScene().AddItem(self.chart)

        self.renderWindow = self.view.GetRenderWindow()
        self.view.GetRenderWindow().SetSize(800, 600)

    # ---------------------------------------------------------------------------------------------
    # Method to update histogram and render it on the server-side
    # ---------------------------------------------------------------------------------------------
    def update_histogram(self, bins):
        bins = int(bins)
        if self.data_changed:
            self.dask_data = da.from_array(self.np_data, chunks='auto')
            self.data_changed = False

        self.compute_histogram_data_with_dask(self.dask_data, bins)

        self.arrX.Reset()
        self.arrY.Reset()

        for i in range(len(self.hist)):
            self.arrX.InsertNextValue(self.bin_edges[i])
            self.arrY.InsertNextValue(self.hist[i])

        self.update_the_client_view()

    def update_the_client_view(self):
        self.client_view.update()

    # ---------------------------------------------------------------------------------------------
    # Method using Dask to compute histogram data
    # ---------------------------------------------------------------------------------------------
    def compute_histogram_data_with_dask(self, dask_data, bins):
        key = (bins, self.data_min, self.data_max)

        if key in self.hist_cache:
            self.hist, self.bin_edges = self.hist_cache[key]
        else:
            dask_hist = dh.factory(dask_data, axes=(bh.axis.Regular(bins, self.data_min, self.data_max + 1),))
            dask_hist = dask_hist.persist()
            hist_result = self.convert_agghistogram_to_numpy_array_of_frequencies(dask_hist)
            self.hist = hist_result
            _, self.bin_edges = da.histogram(dask_data, bins=bins, range=(self.data_min, self.data_max))

            self.hist_cache[key] = (self.hist, self.bin_edges)

    def convert_agghistogram_to_numpy_array_of_frequencies(self, dask_object):
        result = dask_object.compute(scheduler='threads')
        frequencies = result.to_numpy()[0]
        return frequencies

    # ---------------------------------------------------------------------------------------------
    # State change handler for bins
    # ---------------------------------------------------------------------------------------------
    @change("bins")
    def on_bins_change(self, bins, **kwargs):
        self.update_histogram(bins)

    # ---------------------------------------------------------------------------------------------
    # UI Setup
    # ---------------------------------------------------------------------------------------------
    def setup_ui(self):
        with SinglePageLayout(self.server) as layout:
            layout.title.set_text(f"Histogram App on port {self.port}")
            with layout.toolbar:
                vuetify.VSpacer()
                vuetify.VSlider(
                    v_model=("bins", 10),
                    min=1,
                    max=50,
                    label="Number of Bins",
                )
            with layout.content:
                self.client_view = vtk.VtkRemoteView(ref="view")
                vuetify.VContainer(self.client_view, fluid=True)

        self.update_histogram(10)

    # ---------------------------------------------------------------------------------------------
    # UI Layout Definition
    # ---------------------------------------------------------------------------------------------
    def setup_layout(self):
        with SinglePageLayout(self.server) as layout:
            layout.title.set_text(self.server.name)
            with layout.toolbar:
                vuetify.VSpacer()
                vuetify.VSlider(v_model=("bins", 5), min=1, max=100, label="Number of Bins", hide_details=True, dense=True)
                vuetify.VFileInput(v_model=("file_input", None), label="Upload CSV File", accept=".csv")
                vuetify.VSelect(v_model=("selected_column", None), items=("column_options",), label="Select Column")

# ---------------------------------------------------------------------------------------------
# Server Manager Class
# ---------------------------------------------------------------------------------------------
class ServerManager:
    def __init__(self):
        self.servers_manager = get_server("Server_Manager", client_type="vue2")
        self.control_state, self.control_ctrl = self.servers_manager.state, self.servers_manager.controller
        self.servers = {}
        self.next_port = 8090
        self.control_state.server_list = []

        self.control_state.level_to_color = {
            "Running": "green",
            "Stopped": "red"
        }
        self.register_triggers()
        self.render_ui_layout()

    def get_server_list(self):
        return [
            {'port': server['port'], 'status': server['status']} for server in self.control_state.server_list
        ]

    def start_new_server(self):
        command = ["python", "multi_trame_server_uncommented.py", "--launch_server", str(self.next_port)]
        process = subprocess.Popen(command)
        self.servers[self.next_port] = process
        self.control_state.server_list.append({
            'port': self.next_port,
            'status': 'Running'
        })
        self.next_port += 1
        self.control_state.dirty("server_list")
        self.render_ui_layout()

    def stop_server(self, port):
        port = int(port)
        server = self.servers.get(port)
        if server is None:
            print(f"ERROR: No server found at port {port}")
            return False
        try:
            server.terminate()
            server.wait()
            del self.servers[port]
            return True
        except Exception as e:
            print(f"An error occurred while stopping server at port {port}: {e}")
            return False

    def register_triggers(self):
        self.control_ctrl.trigger("handle_stop_server")(self.handle_stop_server)

    def handle_stop_server(self, port):
        self.stop_server(port)

    def render_ui_layout(self):
        with SinglePageLayout(self.servers_manager) as layout:
            layout.title.set_text("Server Manager")
            layout.content.clear()

            with layout.content:
                with vuetify.VRow():
                    with vuetify.VCol(cols="auto"):
                        vuetify.VBtn("Start New Server", click=self.start_new_server, classes="ma-2", color="primary", dark=True)
                with vuetify.VCard():
                    vuetify.VCardText("Active Servers:")
                    with vuetify.VList(shaped=True):
                        with vuetify.VListItem(v_for="(server, idx) in server_list", key="idx"):
                            with vuetify.VListItemIcon():
                                vuetify.VIcon("mdi-server", color=("level_to_color[server.status]",))
                            with vuetify.VListItemContent():
                                vuetify.VListItemTitle("{{ server.port }} - {{ server.status }}")
                            with vuetify.VBtn(icon=True, click="trigger('handle_stop_server', [server.port.toString()])"):
                                vuetify.VIcon("mdi-stop", color=("level_to_color[server.status]",))

    def start(self, port):
        print(f"Starting Server_Manager at http://localhost:{port}/index.html")
        self.servers_manager.start(port=port)


# ---------------------------------------------------------------------------------------------
# Main Execution Block
# ---------------------------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import asyncio

    if "--launch_server" in sys.argv:
        port = int(sys.argv[sys.argv.index("--launch_server") + 1])
        histogram_app = BaseHistogramApp("my_histogram_app", port)
        histogram_app.server.start(exec_mode="main", port=port)
    else:
        server_manager = ServerManager()
        server_manager.start(8080)
    