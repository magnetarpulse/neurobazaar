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
from base_basic_histogram_class import BasicHistogramApp
from base_analyzer_histogram_class import BaseAnalyzerCountHistogram
from base_general_histogram_class import GenericHistogramApp

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
        self.next_port = 5459

        self.basic_servers = {}
        self.control_state.basic_server_list = []

        self.general_servers = {}
        self.control_state.general_server_list = []

        self.analyzer_servers = {}
        self.control_state.analyzer_server_list = []

        self.control_state.level_to_color = {
        "Running": "green",
        "Stopped": "red"
        }

        self.register_triggers()

        self.render_ui_layout()

    # ---------------------------------------------------------------------------------------------
    # Method to start a Standalone Histogram server
    # ---------------------------------------------------------------------------------------------
    
    def start_new_basic_server(self):
        print("Starting new Standalone Histogram server")

        command = [
            "python",
            "server_manager.py",  
            "--launch_basic_server",
            str(self.next_port)
        ]

        process = subprocess.Popen(command)
        self.basic_servers[self.next_port] = process

        print(f"Started new Standalone Histogram server on port {self.next_port} with PID {process.pid}")

        self.control_state.basic_server_list.append({
            'port': self.next_port,
            'status': 'Running'
        })

        print(f"Server list after starting new Standalone Histogram server: {self.control_state.basic_server_list}") 

        self.next_port += 1

        self.control_state.dirty("basic_server_list")

        self.render_ui_layout()

    # ---------------------------------------------------------------------------------------------
    # Method to start a Neurobazaar Histogram application server
    # ---------------------------------------------------------------------------------------------
    
    def start_new_general_server(self):
        print("Starting new Neurobazaar Histogram server")

        command = [
            "python",
            "server_manager.py",  
            "--launch_general_server",
            str(self.next_port)
        ]

        process = subprocess.Popen(command)
        self.general_servers[self.next_port] = process

        print(f"Started new Neurobazaar Histogram server on port {self.next_port} with PID {process.pid}")

        self.control_state.general_server_list.append({
            'port': self.next_port,
            'status': 'Running'
        })

        print(f"Server list after starting Neurobazaar Histogram new server: {self.control_state.general_server_list}") 

        self.next_port += 1

        self.control_state.dirty("general_server_list")

        self.render_ui_layout()

    # ---------------------------------------------------------------------------------------------
    # Method to start a OoD Analyzer server
    # ---------------------------------------------------------------------------------------------
    
    def start_new_analyzer_server(self):
        print("Starting new OoD Analyzer server")

        command = [
            "python",
            "server_manager.py",  
            "--launch_analyzer_server",
            str(self.next_port)
        ]

        process = subprocess.Popen(command)
        self.analyzer_servers[self.next_port] = process

        print(f"Started new OoD Analyzer server on port {self.next_port} with PID {process.pid}")

        self.control_state.analyzer_server_list.append({
            'port': self.next_port,
            'status': 'Running'
        })

        print(f"Server list after starting new OoD Analyzer server: {self.control_state.analyzer_server_list}") 

        self.next_port += 1

        self.control_state.dirty("analyzer_server_list")

        self.render_ui_layout()
    
    # ---------------------------------------------------------------------------------------------
    # Method to stop a Standalone Histogram server
    # ---------------------------------------------------------------------------------------------

    def stop_basic_server(self, port):
        port = int(port)

        print(f"Attempting to stop Standalone Histogram server at port {port}")

        server = self.basic_servers.get(port)

        print("Server: ", server)

        if server is None:
            print(f"ERROR: No Standalone Histogram server found at port {port}")
            return

        try:
            os.kill(server.pid, signal.SIGTERM) 
            print(f"Server at port {port} has been stopped")
        except Exception as e:
            print(f"An error occurred while stopping Standalone Histogram server at port {port}: {e}")

        del self.basic_servers[port]

        for server in self.control_state.basic_server_list:
            if server['port'] == port:
                server['status'] = 'Stopped'
                break

        self.control_state.dirty("basic_server_list")

        self.render_ui_layout()

        print(f"Standalone Histogram server at port {port} has been removed from the list of servers")

    # ---------------------------------------------------------------------------------------------
    # Method to stop a Neurobazaar Histogram application server
    # ---------------------------------------------------------------------------------------------

    def stop_general_server(self, port):
        port = int(port)

        print(f"Attempting to stop Neurobazaar Histogram server at port {port}")

        server = self.general_servers.get(port)

        print("Server: ", server)

        if server is None:
            print(f"ERROR: No Neurobazaar Histogram server found at port {port}")
            return

        try:
            os.kill(server.pid, signal.SIGTERM) 
            print(f"Server at port {port} has been stopped")
        except Exception as e:
            print(f"An error occurred while stopping Neurobazaar Histogram server at port {port}: {e}")

        del self.general_servers[port]

        for server in self.control_state.general_server_list:
            if server['port'] == port:
                server['status'] = 'Stopped'
                break

        self.control_state.dirty("general_server_list")

        self.render_ui_layout()

        print(f"Neurobazaar Histogram server at port {port} has been removed from the list of servers")

    # ---------------------------------------------------------------------------------------------
    # Method to stop a OoD Analyzer server
    # ---------------------------------------------------------------------------------------------
    
    def stop_analyzer_server(self, port):
        port = int(port)

        print(f"Attempting to stop OoD Analyzer server at port {port}")

        server = self.analyzer_servers.get(port)

        print("Server: ", server)

        if server is None:
            print(f"ERROR: No OoD Analyzer server found at port {port}")
            return

        try:
            os.kill(server.pid, signal.SIGTERM) 
            print(f"Server at port {port} has been stopped")
        except Exception as e:
            print(f"An error occurred while stopping OoD Analyzer server at port {port}: {e}")

        del self.analyzer_servers[port]

        for server in self.control_state.analyzer_server_list:
            if server['port'] == port:
                server['status'] = 'Stopped'
                break

        self.control_state.dirty("analyzer_server_list")

        self.render_ui_layout()

        print(f"OoD Analyzer server at port {port} has been removed from the list of servers")
    
    # ---------------------------------------------------------------------------------------------
    # Method to register triggers with the controller
    # ---------------------------------------------------------------------------------------------

    def register_triggers(self):
        self.control_ctrl.trigger("trigger_stop_basic_server")(self.trigger_stop_basic_server)
        self.control_ctrl.trigger("trigger_stop_general_server")(self.trigger_stop_general_server)
        self.control_ctrl.trigger("trigger_stop_analyzer_server")(self.trigger_stop_analyzer_server)

    # ---------------------------------------------------------------------------------------------
    # Trigger to handle stopping a Standalone Histogram server
    # ---------------------------------------------------------------------------------------------

    def trigger_stop_basic_server(self, port):
        print("Stopping Standalone Histogram server with port:", port)
        self.stop_basic_server(port) 
    
    # ---------------------------------------------------------------------------------------------
    # Trigger to handle stopping a Neurobazaar histogram server
    # ---------------------------------------------------------------------------------------------

    def trigger_stop_general_server(self, port):
        print("Stopping Neurobazaar Histogram server with port:", port)
        self.stop_general_server(port) 

    # ---------------------------------------------------------------------------------------------
    # Trigger to handle stopping a OoD Analyzer server
    # ---------------------------------------------------------------------------------------------

    def trigger_stop_analyzer_server(self, port):
        print("Stopping OoD Analyzer server with port:", port)
        self.stop_analyzer_server(port) 

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
                            "Start New Standalone Histogram Server",
                            click=self.start_new_basic_server,
                            classes="ma-2",
                            color="primary",
                            dark=True,
                        )

                with vuetify.VCard():
                    vuetify.VCardText("Active Standalone Histogram Server(s):")
                    with vuetify.VList(shaped=True):
                        with vuetify.VListItem(v_for="(server, idx) in basic_server_list", key="idx"):
                            with vuetify.VListItemIcon():
                                vuetify.VIcon("mdi-server", color=("level_to_color[server.status]",))
                            with vuetify.VListItemContent():
                                vuetify.VListItemTitle("{{ server.port }} - {{ server.status }}")
                            with vuetify.VBtn(icon=True, click="trigger('trigger_stop_basic_server', [server.port.toString()])"):
                                vuetify.VIcon("mdi-stop", color=("level_to_color[server.status]",))

                with vuetify.VRow():
                    with vuetify.VCol(cols="auto"):
                        vuetify.VBtn(
                            "Start New Neurobazaar Histogram Server",
                            click=self.start_new_general_server,
                            classes="ma-2",
                            color="primary",
                            dark=True,
                        )

                with vuetify.VCard():
                    vuetify.VCardText("Active Neurobazaar Histogram Server(s):")
                    with vuetify.VList(shaped=True):
                        with vuetify.VListItem(v_for="(server, idx) in general_server_list", key="idx"):
                            with vuetify.VListItemIcon():
                                vuetify.VIcon("mdi-server", color=("level_to_color[server.status]",))
                            with vuetify.VListItemContent():
                                vuetify.VListItemTitle("{{ server.port }} - {{ server.status }}")
                            with vuetify.VBtn(icon=True, click="trigger('trigger_stop_general_server', [server.port.toString()])"):
                                vuetify.VIcon("mdi-stop", color=("level_to_color[server.status]",))

                with vuetify.VRow():
                    with vuetify.VCol(cols="auto"):
                        vuetify.VBtn(
                            "Start New Neurobazaar OoD Analyzer Server",
                            click=self.start_new_analyzer_server,
                            classes="ma-2",
                            color="primary",
                            dark=True,
                        )
                
                with vuetify.VCard():
                    vuetify.VCardText("Active Neurobazaar OoD Analyzer Server(s):")
                    with vuetify.VList(shaped=True):
                        with vuetify.VListItem(v_for="(server, idx) in analyzer_server_list", key="idx"):
                            with vuetify.VListItemIcon():
                                vuetify.VIcon("mdi-server", color=("level_to_color[server.status]",))
                            with vuetify.VListItemContent():
                                vuetify.VListItemTitle("{{ server.port }} - {{ server.status }}")
                            with vuetify.VBtn(icon=True, click="trigger('trigger_stop_analyzer_server', [server.port.toString()])"):
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
    
    if "--launch_basic_server" in sys.argv:
        ports = [int(arg) for arg in sys.argv[sys.argv.index("--launch_basic_server") + 1:]]

        loop = asyncio.get_event_loop()

        for port in ports:
            print("Starting Standalone Histogram server on port:", port)

            basic_histogram_app = BasicHistogramApp("Standalone Histogram", port)
            task = loop.create_task(basic_histogram_app.start_new_server_async())

            loop.run_until_complete(task)

    elif "--launch_general_server" in sys.argv:
        ports = [int(arg) for arg in sys.argv[sys.argv.index("--launch_general_server") + 1:]]

        loop = asyncio.get_event_loop()

        for port in ports:
            print("Starting Neurobazaar Histogram server on port:", port)

            general_histogram_app = GenericHistogramApp("Neurobazaar Histogram", port)
            names, csv_file = general_histogram_app.get_data_from_user()
            general_histogram_app.update_dataset_names()
            task = loop.create_task(general_histogram_app.start_new_server_async())

            loop.run_until_complete(task)
            
    elif "--launch_analyzer_server" in sys.argv:
        ports = [int(arg) for arg in sys.argv[sys.argv.index("--launch_analyzer_server") + 1:]]

        loop = asyncio.get_event_loop()

        for port in ports:
            print("Starting OoD Analyzer server on port:", port)

            analyzer_histogram_app = BaseAnalyzerCountHistogram("OoD Analyzer", port, "/home/demo/neurobazaar/MaxSlices_newMode_Manuf_Int_Real.csv", "Area")
            task = loop.create_task(analyzer_histogram_app.start_server_async())

            loop.run_until_complete(task)
    else:
        server_manager.start(port=8080)