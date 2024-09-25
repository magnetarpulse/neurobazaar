# Imports required for the server manager
# For multi-server management, also for system management 
import os
import sys

cwd = os.getcwd()
index = cwd.index('neurobazaar')
neurobazaar_dir = cwd[:index + len('neurobazaar')]
sys.path.insert(0, neurobazaar_dir)

# Imports required for the server manager
# For multi-server management
import asyncio
import subprocess
import signal

# Imports required for the vtk trame application
# Core libraries for rendering (vtk)
from trame.app import get_server
from trame.decorators import TrameApp, change
from trame.widgets import vtk, vuetify
from trame.ui.vuetify import SinglePageLayout
import vtk as standard_vtk

# Imports required for finding the counts in ranges of the histogram application
# Core libraries for rendering (matplotlib)
from trame.widgets import matplotlib

# Imports required for finding the counts in ranges of the histogram application
# Core libraries for data processing (matplotlib)
import matplotlib.pyplot as plt
import pandas as pd

# Imports required for the all histogram applications
# Core libraries for data processing (all)
import numpy as np
import dask.dataframe as dd
import dask.array as da
import dask_histogram as dh
import boost_histogram as bh
from dask.distributed import Client

# Imports required for the all histogram applications
# For manipulating CSV files
import csv
import tempfile
from neurobazaar.services.datastorage.localfs_datastore import LocalFSDatastore

# Imports required for the all histogram applications
# Base class for the histogram application
from abc import abstractmethod

# Imported for the histogram application
# from base_histogram_class import BaseHistogramApp
# from base_count_histogram_class import BaseRangeCountHistogram
from demo_base_histogram import DemoBaseHistogram

## ================================================================== ## 
## Visualization service. Server Manager sub service. The base class. ##         
## ================================================================== ##

class ServerManager:

    # ---------------------------------------------------------------------------------------------
    # Constructor for the ServerManager class.
    # --------------------------------------------------------------------------------------------- 

    def __init__(self):
        self.servers_manager = get_server("Server_Manager", client_type="vue2")
        self.control_state, self.control_ctrl = self.servers_manager.state, self.servers_manager.controller
        self.servers = {}
        self.next_port = 5456
        self.control_state.server_list = []

        self.control_state.level_to_color = {
        "Running": "green",
        "Stopped": "red"
        }

        self.register_triggers()

        self.render_ui_layout()

    # ---------------------------------------------------------------------------------------------
    # Method to start a different application server
    # ---------------------------------------------------------------------------------------------
    
    def start_new_server(self):
        print("Starting new server")

        command = [
            "python",
            "server_manager.py",  
            "--launch_server",
            str(self.next_port)
        ]

        process = subprocess.Popen(command)
        self.servers[self.next_port] = process

        print(f"Started new server on port {self.next_port} with PID {process.pid}")

        self.control_state.server_list.append({
            'port': self.next_port,
            'status': 'Running'
        })

        print(f"Server list after starting new server: {self.control_state.server_list}") 

        self.next_port += 1

        self.control_state.dirty("server_list")

        self.render_ui_layout()
    
    # ---------------------------------------------------------------------------------------------
    # Method to stop a different application server
    # ---------------------------------------------------------------------------------------------

    def stop_server(self, port):
        port = int(port)

        print(f"Attempting to stop server at port {port}")

        server = self.servers.get(port)

        print("Server: ", server)

        if server is None:
            print(f"ERROR: No server found at port {port}")
            return

        try:
            os.kill(server.pid, signal.SIGTERM) 
            print(f"Server at port {port} has been stopped")
        except Exception as e:
            print(f"An error occurred while stopping server at port {port}: {e}")

        del self.servers[port]

        for server in self.control_state.server_list:
            if server['port'] == port:
                server['status'] = 'Stopped'
                break

        self.control_state.dirty("server_list")

        self.render_ui_layout()

        print(f"Server at port {port} has been removed from the list of servers")
    
    # ---------------------------------------------------------------------------------------------
    # Method to register triggers with the controller
    # ---------------------------------------------------------------------------------------------

    def register_triggers(self):
        self.control_ctrl.trigger("handle_stop_server")(self.handle_stop_server)

    # ---------------------------------------------------------------------------------------------
    # Trigger to handle stopping a server
    # ---------------------------------------------------------------------------------------------

    def handle_stop_server(self, port):
        print("Stopping server with port:", port)
        self.stop_server(port) 

    # ---------------------------------------------------------------------------------------------
    # The interface for the server manager
    # ---------------------------------------------------------------------------------------------
    
    def render_ui_layout(self):

        with SinglePageLayout(self.servers_manager) as layout:
            layout.title.set_text("Server Manager")
            layout.content.clear()

            with layout.content:
                with vuetify.VRow():
                    with vuetify.VCol(cols="auto"):
                        vuetify.VBtn(
                            "Start New Server",
                            click=self.start_new_server,
                            classes="ma-2",
                            color="primary",
                            dark=True,
                        )

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

    # ---------------------------------------------------------------------------------------------
    # Method to start the server manager
    # ---------------------------------------------------------------------------------------------
    
    def start(self, port):
        print(f"Starting Server_Manager at http://localhost:{port}/index.html")
        self.servers_manager.start(port=port)

if __name__ == "__main__":
    import sys

    server_manager = ServerManager()
    
    if "--launch_server" in sys.argv:
        ports = [int(arg) for arg in sys.argv[sys.argv.index("--launch_server") + 1:]]

        loop = asyncio.get_event_loop()

        for port in ports:
            print("Starting server on port:", port)

            # histogram_app = BaseHistogramApp("my_histogram_app", port)
            # task = loop.create_task(histogram_app.start_new_server_async())

            # bin_count_histogram_app = BaseRangeCountHistogram("OoD Analyzer", port, "/home/demo/neurobazaar/MaxSlices_newMode_Manuf_Int.csv", "Area")
            # task = loop.create_task(bin_count_histogram_app.start_server_async())

            demo_histogram_app = DemoBaseHistogram("Demo Histogram", port)
            names, csv_file = demo_histogram_app.get_data_from_user()
            demo_histogram_app.update_dataset_names()
            task = loop.create_task(demo_histogram_app.start_new_server_async())

            loop.run_until_complete(task)
    else:
        server_manager.start(port=8080)