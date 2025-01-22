# Imports required for the server manager
# For multi-server management, also for system management 
import os
import sys

# Imports required for the server manager
# For multi-server management
import asyncio
import subprocess
import signal

# Get the Neurobazaar directory as the root directory
cwd = os.getcwd()
index = cwd.index('neurobazaar')
neurobazaar_dir = cwd[:index + len('neurobazaar')]
print("Neurobazaar directory: ", neurobazaar_dir)
sys.path.insert(0, neurobazaar_dir)

# Imports required for the vtk trame application
# Core libraries for rendering (vtk)
from trame.app import get_server
from trame.widgets import vuetify
from trame.ui.vuetify import SinglePageLayout

# Imported for the histogram application
from trame.server.example_generic_histogram import GenericHistogramApp
from trame.server.example_standalone_histogram import BasicHistogramApp
from trame.server.example_simple_server import main_async
from trame.server.updated_dask_working_code import BaseOoDHistogram

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

        self.simple_servers = {}
        self.control_state.simple_server_list = []

        self.ood_servers = {}
        self.control_state.ood_server_list = []

        self.control_state.level_to_color = {
        "Running": "green",
        "Stopped": "red"
        }

        self.register_triggers()

        self.render_ui_layout()

    # ---------------------------------------------------------------------------------------------
    # Method to start a standalone histogram server
    # ---------------------------------------------------------------------------------------------
    
    def start_new_basic_server(self):
        print("Starting a new standalone histogram server")

        command = [
            "python",
            "trame/server/example_server_manager.py",  
            "--launch_basic_server",
            str(self.next_port)
        ]

        process = subprocess.Popen(command)
        self.basic_servers[self.next_port] = process

        print(f"Started a new standalone histogram server on port {self.next_port} with PID {process.pid}")

        self.control_state.basic_server_list.append({
            'port': self.next_port,
            'status': 'Running'
        })

        print(f"Server list after starting a new standalone histogram server: {self.control_state.basic_server_list}") 

        self.next_port += 1

        self.control_state.dirty("basic_server_list")

        self.render_ui_layout()

    # ---------------------------------------------------------------------------------------------
    # Method to start a general histogram application server
    # ---------------------------------------------------------------------------------------------
    
    def start_new_general_server(self):
        print("Starting a new general histogram server")

        command = [
            "python",
            "trame/server/example_server_manager.py",  
            "--launch_general_server",
            str(self.next_port)
        ]

        process = subprocess.Popen(command)
        self.general_servers[self.next_port] = process

        print(f"Started a new general histogram server on port {self.next_port} with PID {process.pid}")

        self.control_state.general_server_list.append({
            'port': self.next_port,
            'status': 'Running'
        })

        print(f"Server list after starting a new general histogram server: {self.control_state.general_server_list}") 

        self.next_port += 1

        self.control_state.dirty("general_server_list")

        self.render_ui_layout()

    # ---------------------------------------------------------------------------------------------
    # Method to start a simple server
    # ---------------------------------------------------------------------------------------------
    
    def start_new_simple_server(self):
        print("Starting a new simple server")

        command = [
            "python",
            "trame/server/example_server_manager.py",  
            "--launch_simple_server",
            str(self.next_port)
        ]

        process = subprocess.Popen(command)
        self.simple_servers[self.next_port] = process

        print(f"Started a new simple server on port {self.next_port} with PID {process.pid}")

        self.control_state.simple_server_list.append({
            'port': self.next_port,
            'status': 'Running'
        })

        print(f"Server list after starting a new simple server: {self.control_state.simple_server_list}") 

        self.next_port += 1

        self.control_state.dirty("simple_server_list")

        self.render_ui_layout()

    # ---------------------------------------------------------------------------------------------
    # Method to start an OOD server
    # ---------------------------------------------------------------------------------------------
    
    def start_new_ood_server(self):
        print("Starting a new OOD server")

        command = [
            "python",
            "trame/server/example_server_manager.py",  
            "--launch_ood_server",
            str(self.next_port)
        ]

        process = subprocess.Popen(command)
        self.ood_servers = getattr(self, 'ood_servers', {})
        self.ood_servers[self.next_port] = process

        print(f"Started a new OOD server on port {self.next_port} with PID {process.pid}")

        self.control_state.ood_server_list = getattr(self.control_state, 'ood_server_list', [])
        self.control_state.ood_server_list.append({
            'port': self.next_port,
            'status': 'Running'
        })

        print(f"Server list after starting a new OOD server: {self.control_state.ood_server_list}") 

        self.next_port += 1

        self.control_state.dirty("ood_server_list")

        self.render_ui_layout()
    
    # ---------------------------------------------------------------------------------------------
    # Method to stop a Standalone Histogram server
    # ---------------------------------------------------------------------------------------------

    def stop_basic_server(self, port):
        port = int(port)

        print(f"Attempting to stop standalone histogram server at port {port}")

        server = self.basic_servers.get(port)

        print("Server: ", server)

        if server is None:
            print(f"ERROR: No standalone histogram server found at port {port}")
            return

        try:
            os.kill(server.pid, signal.SIGTERM) 
            print(f"Server at port {port} has been stopped")
        except Exception as e:
            print(f"An error occurred while stopping standalone histogram server at port {port}: {e}")

        del self.basic_servers[port]

        for server in self.control_state.basic_server_list:
            if server['port'] == port:
                server['status'] = 'Stopped'
                break

        self.control_state.dirty("basic_server_list")

        self.render_ui_layout()

        print(f"Standalone histogram server at port {port} has been removed from the list of servers")

    # ---------------------------------------------------------------------------------------------
    # Method to stop a general histogram application server
    # ---------------------------------------------------------------------------------------------

    def stop_general_server(self, port):
        port = int(port)

        print(f"Attempting to stop general histogram server at port {port}")

        server = self.general_servers.get(port)

        print("Server: ", server)

        if server is None:
            print(f"ERROR: No general histogram server found at port {port}")
            return

        try:
            os.kill(server.pid, signal.SIGTERM) 
            print(f"Server at port {port} has been stopped")
        except Exception as e:
            print(f"An error occurred while stopping general histogram server at port {port}: {e}")

        del self.general_servers[port]

        for server in self.control_state.general_server_list:
            if server['port'] == port:
                server['status'] = 'Stopped'
                break

        self.control_state.dirty("general_server_list")

        self.render_ui_layout()

        print(f"General histogram server at port {port} has been removed from the list of servers")

    # ---------------------------------------------------------------------------------------------
    # Method to stop a simple server
    # ---------------------------------------------------------------------------------------------
    
    def stop_simple_server(self, port):
        port = int(port)

        print(f"Attempting to stop simple server at port {port}")

        server = self.simple_servers.get(port)

        print("Server: ", server)

        if server is None:
            print(f"ERROR: No simple server found at port {port}")
            return

        try:
            os.kill(server.pid, signal.SIGTERM) 
            print(f"Server at port {port} has been stopped")
        except Exception as e:
            print(f"An error occurred while stopping simple server at port {port}: {e}")

        del self.simple_servers[port]

        for server in self.control_state.simple_server_list:
            if server['port'] == port:
                server['status'] = 'Stopped'
                break

        self.control_state.dirty("simple_server_list")

        self.render_ui_layout()

        print(f"Simple server at port {port} has been removed from the list of servers")
    
    # ---------------------------------------------------------------------------------------------
    # Method to stop an OOD server
    # ---------------------------------------------------------------------------------------------

    def stop_ood_server(self, port):
        port = int(port)

        print(f"Attempting to stop OOD server at port {port}")

        server = self.ood_servers.get(port)

        print("Server: ", server)

        if server is None:
            print(f"ERROR: No OOD server found at port {port}")
            return

        try:
            os.kill(server.pid, signal.SIGTERM) 
            print(f"Server at port {port} has been stopped")
        except Exception as e:
            print(f"An error occurred while stopping OOD server at port {port}: {e}")

        del self.ood_servers[port]

        for server in self.control_state.ood_server_list:
            if server['port'] == port:
                server['status'] = 'Stopped'
                break

        self.control_state.dirty("ood_server_list")

        self.render_ui_layout()

        print(f"OOD server at port {port} has been removed from the list of servers")
    
    # ---------------------------------------------------------------------------------------------
    # Method to register triggers with the controller
    # ---------------------------------------------------------------------------------------------

    def register_triggers(self):
        self.control_ctrl.trigger("trigger_stop_basic_server")(self.trigger_stop_basic_server)
        self.control_ctrl.trigger("trigger_stop_general_server")(self.trigger_stop_general_server)
        self.control_ctrl.trigger("trigger_stop_simple_server")(self.trigger_stop_simple_server)
        self.control_ctrl.trigger("trigger_stop_ood_server")(self.trigger_stop_ood_server)

    # ---------------------------------------------------------------------------------------------
    # Trigger to handle stopping a standalone histogram server
    # ---------------------------------------------------------------------------------------------

    def trigger_stop_basic_server(self, port):
        print("Stopping standalone histogram server at port:", port)
        self.stop_basic_server(port) 
    
    # ---------------------------------------------------------------------------------------------
    # Trigger to handle stopping a general histogram server
    # ---------------------------------------------------------------------------------------------

    def trigger_stop_general_server(self, port):
        print("Stopping general histogram server at port:", port)
        self.stop_general_server(port) 

    # ---------------------------------------------------------------------------------------------
    # Trigger to handle stopping a simple server
    # ---------------------------------------------------------------------------------------------

    def trigger_stop_simple_server(self, port):
        print("Stopping simple server at port:", port)
        self.stop_simple_server(port) 

    # ---------------------------------------------------------------------------------------------
    # Trigger to handle stopping an OOD server
    # ---------------------------------------------------------------------------------------------

    def trigger_stop_ood_server(self, port):
        print("Stopping OOD server at port:", port)
        self.stop_ood_server(port)

    # ---------------------------------------------------------------------------------------------
    # The interface for the server manager
    # ---------------------------------------------------------------------------------------------
    
    def render_ui_layout(self):
        with SinglePageLayout(self.servers_manager) as layout:
            layout.title.set_text("Server Manager")
            layout.content.clear()

            with layout.content:
                with vuetify.VContainer(fluid=True, classes="pa-4", style="background: linear-gradient(135deg, #f5f7fa 0%, #e4e9f2 100%);"):
                    with vuetify.VRow(dense=False):
                        with vuetify.VCol(cols="12", md="4", classes="pa-2"):
                            with vuetify.VCard(elevation=1):
                                with vuetify.VCardTitle(classes="primary white--text py-3"):
                                    with vuetify.VRow(align="center", classes="ma-0"):
                                        with vuetify.VCol(cols="auto", classes="pa-0 mr-3"):
                                            vuetify.VIcon("mdi-chart-histogram", color="white", size="24")
                                        with vuetify.VCol(classes="pa-0"):
                                            vuetify.VCardText("Standalone Histogram Servers", classes="white--text text-h6 mb-0")
                                
                                with vuetify.VCardText(classes="pa-4"):
                                    vuetify.VBtn(
                                        "START NEW SERVER",
                                        prepend_icon="mdi-plus",
                                        click=self.start_new_basic_server,
                                        color="primary",
                                        classes="mb-6 py-2",
                                        style_="height: 44px;",
                                        block=True,
                                    )
                                    
                                    with vuetify.VList(nav=True, classes="pa-0"):
                                        with vuetify.VListItem(
                                            v_for="(server, idx) in basic_server_list",
                                            key="idx",
                                            classes="rounded-lg mb-3 grey lighten-5"
                                        ):
                                            with vuetify.VListItemIcon():
                                                vuetify.VIcon(
                                                    "mdi-server",
                                                    color=("level_to_color[server.status]",),
                                                    classes="mr-3"
                                                )
                                            with vuetify.VListItemContent():
                                                vuetify.VListItemTitle(
                                                    "Port: {{ server.port }}",
                                                    classes="font-weight-medium"
                                                )
                                                vuetify.VListItemSubtitle(
                                                    "{{ server.status }}",
                                                    classes="text-capitalize"
                                                )
                                            with vuetify.VListItemAction():
                                                with vuetify.VBtn(
                                                    icon=True,
                                                    color="error",
                                                    click="trigger('trigger_stop_basic_server', [server.port.toString()])",
                                                    classes="mr-2"
                                                ):
                                                    vuetify.VIcon("mdi-stop-circle")

                        with vuetify.VCol(cols="12", md="4", classes="pa-2"):
                            with vuetify.VCard(elevation=1):
                                with vuetify.VCardTitle(classes="secondary white--text py-3"):
                                    with vuetify.VRow(align="center", classes="ma-0"):
                                        with vuetify.VCol(cols="auto", classes="pa-0 mr-3"):
                                            vuetify.VIcon("mdi-chart-box", color="white", size="24")
                                        with vuetify.VCol(classes="pa-0"):
                                            vuetify.VCardText("General Histogram Servers", classes="white--text text-h6 mb-0")
                                
                                with vuetify.VCardText(classes="pa-4"):
                                    vuetify.VBtn(
                                        "START NEW SERVER",
                                        prepend_icon="mdi-plus",
                                        click=self.start_new_general_server,
                                        color="secondary",
                                        classes="mb-6 py-2",
                                        style_="height: 44px;",
                                        block=True,
                                    )
                                    
                                    with vuetify.VList(nav=True, classes="pa-0"):
                                        with vuetify.VListItem(
                                            v_for="(server, idx) in general_server_list",
                                            key="idx",
                                            classes="rounded-lg mb-3 grey lighten-5"
                                        ):
                                            with vuetify.VListItemIcon():
                                                vuetify.VIcon(
                                                    "mdi-server",
                                                    color=("level_to_color[server.status]",),
                                                    classes="mr-3"
                                                )
                                            with vuetify.VListItemContent():
                                                vuetify.VListItemTitle(
                                                    "Port: {{ server.port }}",
                                                    classes="font-weight-medium"
                                                )
                                                vuetify.VListItemSubtitle(
                                                    "{{ server.status }}",
                                                    classes="text-capitalize"
                                                )
                                            with vuetify.VListItemAction():
                                                with vuetify.VBtn(
                                                    icon=True,
                                                    color="error",
                                                    click="trigger('trigger_stop_general_server', [server.port.toString()])",
                                                    classes="mr-2"
                                                ):
                                                    vuetify.VIcon("mdi-stop-circle")

                        with vuetify.VCol(cols="12", md="4", classes="pa-2"):
                            with vuetify.VCard(elevation=1):
                                with vuetify.VCardTitle(classes="success white--text py-3"):
                                    with vuetify.VRow(align="center", classes="ma-0"):
                                        with vuetify.VCol(cols="auto", classes="pa-0 mr-3"):
                                            vuetify.VIcon("mdi-server", color="white", size="24")
                                        with vuetify.VCol(classes="pa-0"):
                                            vuetify.VCardText("Simple Servers", classes="white--text text-h6 mb-0")
                                
                                with vuetify.VCardText(classes="pa-4"):
                                    vuetify.VBtn(
                                        "START NEW SERVER",
                                        prepend_icon="mdi-plus",
                                        click=self.start_new_simple_server,
                                        color="success",
                                        classes="mb-6 py-2",
                                        style_="height: 44px;",
                                        block=True,
                                    )
                                    
                                    with vuetify.VList(nav=True, classes="pa-0"):
                                        with vuetify.VListItem(
                                            v_for="(server, idx) in simple_server_list",
                                            key="idx",
                                            classes="rounded-lg mb-3 grey lighten-5"
                                        ):
                                            with vuetify.VListItemIcon():
                                                vuetify.VIcon(
                                                    "mdi-server",
                                                    color=("level_to_color[server.status]",),
                                                    classes="mr-3"
                                                )
                                            with vuetify.VListItemContent():
                                                vuetify.VListItemTitle(
                                                    "Port: {{ server.port }}",
                                                    classes="font-weight-medium"
                                                )
                                                vuetify.VListItemSubtitle(
                                                    "{{ server.status }}",
                                                    classes="text-capitalize"
                                                )
                                            with vuetify.VListItemAction():
                                                with vuetify.VBtn(
                                                    icon=True,
                                                    color="error",
                                                    click="trigger('trigger_stop_simple_server', [server.port.toString()])",
                                                    classes="mr-2"
                                                ):
                                                    vuetify.VIcon("mdi-stop-circle")

                        with vuetify.VCol(cols="12", md="4", classes="pa-2"):
                            with vuetify.VCard(elevation=1):
                                with vuetify.VCardTitle(classes="warning white--text py-3"):
                                    with vuetify.VRow(align="center", classes="ma-0"):
                                        with vuetify.VCol(cols="auto", classes="pa-0 mr-3"):
                                            vuetify.VIcon("mdi-server", color="white", size="24")
                                        with vuetify.VCol(classes="pa-0"):
                                            vuetify.VCardText("OOD Servers", classes="white--text text-h6 mb-0")

                            with vuetify.VCardText(classes="pa-4"):
                                vuetify.VBtn(
                                    "START NEW SERVER",
                                    prepend_icon="mdi-plus",
                                    click=self.start_new_ood_server,
                                    color="warning",
                                    classes="mb-6 py-2",
                                    style_="height: 44px;",
                                    block=True,
                                )   
                                
                                with vuetify.VList(nav=True, classes="pa-0"):
                                    with vuetify.VListItem(
                                        v_for="(server, idx) in ood_server_list",
                                        key="idx",
                                        classes="rounded-lg mb-3 grey lighten-5"
                                    ):
                                        with vuetify.VListItemIcon():
                                            vuetify.VIcon(
                                                "mdi-server",
                                                color=("level_to_color[server.status]",),
                                                classes="mr-3"
                                            )
                                        with vuetify.VListItemContent():
                                            vuetify.VListItemTitle(
                                                "Port: {{ server.port }}",
                                                classes="font-weight-medium"
                                            )
                                            vuetify.VListItemSubtitle(
                                                "{{ server.status }}",
                                                classes="text-capitalize"
                                            )
                                        with vuetify.VListItemAction():
                                            with vuetify.VBtn(
                                                icon=True,
                                                color="error",
                                                click="trigger('trigger_stop_ood_server', [server.port.toString()])",
                                                classes="mr-2"
                                            ):
                                                vuetify.VIcon("mdi-stop-circle")

    # ---------------------------------------------------------------------------------------------
    # Method to start the server manager
    # ---------------------------------------------------------------------------------------------
    
    def start(self, port):
        print(f"Starting the server manager at http://localhost:{port}/index.html")
        self.servers_manager.start(port=port, open_browser=False, timeout=0, auth_key="key")

    # ---------------------------------------------------------------------------------------------
    # Method to start launch the server manager
    # ---------------------------------------------------------------------------------------------

    def launch_server_manager(self):
        if "--launch_basic_server" in sys.argv:
            ports = [int(arg) for arg in sys.argv[sys.argv.index("--launch_basic_server") + 1:]]

            loop = asyncio.get_event_loop()

            for port in ports:
                print("Starting standalone histogram server on port:", port)

                statc_auth_key = "first_key"

                basic_histogram_app = BasicHistogramApp("Example standalone histogram!", port)
                task = loop.create_task(basic_histogram_app.start_new_server_async(statc_auth_key))

                loop.run_until_complete(task)

        elif "--launch_general_server" in sys.argv:
            ports = [int(arg) for arg in sys.argv[sys.argv.index("--launch_general_server") + 1:]]

            loop = asyncio.get_event_loop()

            for port in ports:
                print("Starting general histogram server on port:", port)

                statc_auth_key = "second_key"

                general_histogram_app = GenericHistogramApp("Example general histogram!", port)
                task = loop.create_task(general_histogram_app.start_new_server_async(statc_auth_key))

                loop.run_until_complete(task)
                
        elif "--launch_simple_server" in sys.argv:
            ports = [int(arg) for arg in sys.argv[sys.argv.index("--launch_simple_server") + 1:]]

            static_auth_key = "third_key"

            for port in ports:
                asyncio.run(main_async(port, static_auth_key))

        elif "--launch_ood_server" in sys.argv:
            ports = [int(arg) for arg in sys.argv[sys.argv.index("--launch_ood_server") + 1:]]

            static_auth_key = "key"

            for port in ports:
                ood_histogram = BaseOoDHistogram("OOD Visualizer", port, "MaxSlices_wOoDScore.csv", "LIDC_Dataset", "lidc_pixConvImg", "Log_Loss_ALL", "StudyInstanceUID", "SeriesInstanceUid", "imageSOP_UID", "noduleID")
                ood_histogram.start_server_immediately()

        else:
            self.start(port=8080)

if __name__ == "__main__":
    server_manager = ServerManager()

    # Note: This will cause an error if you try to start a new application server, since the port is already in use. 
    # Use the launcher instead.
    # Start the server manager
    # server_manager.start(port=8080) 

    # The launcher is used to start new application servers
    # Remember to uncomment the server_manager.start(port=8080) line above 
    server_manager.launch_server_manager()