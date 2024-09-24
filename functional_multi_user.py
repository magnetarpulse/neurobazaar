import asyncio
import os
import signal
import subprocess
import argparse
from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vtk, vuetify
import vtk as standard_vtk
import numpy as np
import dask.dataframe as dd
import dask.array as da
import tempfile

import logging

# -----------------------------------------------------------------------------
# Histogram server creation
# -----------------------------------------------------------------------------

def create_server(name, port):
    server = get_server(name, client_type="vue2")
    state, ctrl = server.state, server.controller

    # Generate random data for the histogram (can be replaced with real data)
    np_data = np.random.normal(size=1000)
    bins = np.linspace(-3, 3, 20)

    data_size = np_data.size * np_data.itemsize

    # Choose between NumPy or Dask based on data size
    if data_size < 5_000_000:
        hist, bin_edges = np.histogram(np_data, bins)
    else:
        dask_data = da.from_array(np_data, chunks='auto')
        data_min, data_max = dask_data.min().compute(), dask_data.max().compute()
        hist, bin_edges = da.histogram(dask_data, bins=bins, range=(data_min, data_max))

    # VTK Table for histogram data
    table = standard_vtk.vtkTable()
    arrX = standard_vtk.vtkFloatArray()
    arrX.SetName("X Axis")
    arrY = standard_vtk.vtkFloatArray()
    arrY.SetName("Frequency")

    for i in range(len(hist)):
        arrX.InsertNextValue(bin_edges[i])
        arrY.InsertNextValue(hist[i])

    table.AddColumn(arrX)
    table.AddColumn(arrY)

    plot = standard_vtk.vtkPlotBar()
    plot.SetInputData(table)
    plot.SetInputArray(0, "X Axis")
    plot.SetInputArray(1, "Frequency")
    plot.SetColor(0, 0, 0, 255)

    chart = standard_vtk.vtkChartXY()
    chart.SetBarWidthFraction(1.0)
    chart.GetAxis(0).SetTitle("Frequency")
    chart.GetAxis(1).SetTitle("Feature")
    chart.AddPlot(plot)

    view = standard_vtk.vtkContextView()
    view.GetScene().AddItem(chart)
    view.GetRenderWindow().SetSize(800, 600)

    # Layout and GUI
    with SinglePageLayout(server) as layout:
        layout.title.set_text(name)  # Setting the title for each server UI
        
        with layout.content:
            with vuetify.VContainer(fluid=True, classes="pa-0 fill-height"):
                vuetify.VSlider(v_model="bins", min=1, max=100, step=1, label="Number of Bins")
                vuetify.VFileInput(v_model="file_input", label="Upload CSV", accept=".csv")
                vuetify.VSelect(v_model=("selected_column", None), items=("column_options",), label="Select Column")
                html_view = vtk.VtkRemoteView(view.GetRenderWindow())
                ctrl.view_update = html_view.update
                ctrl.view_reset_camera = html_view.reset_camera

    @state.change("bins")
    def update_histogram(bins, **kwargs):
        bins = int(bins)
        data_size = np_data.size * np_data.itemsize

        if data_size < 5_000_000:
            hist, bin_edges = np.histogram(np_data, bins)
        else:
            dask_data = da.from_array(np_data, chunks='auto')
            data_min, data_max = dask_data.min().compute(), dask_data.max().compute()
            hist, bin_edges = da.histogram(dask_data, bins=bins, range=(data_min, data_max))

        arrX.Reset()
        arrY.Reset()

        for i in range(len(hist)):
            arrX.InsertNextValue(bin_edges[i])
            arrY.InsertNextValue(hist[i])

        table.Modified()
        ctrl.view_update()

    @state.change("file_input")
    def on_file_input_change(file_input, **kwargs):
        if file_input:
            tmp_path = None
            try:
                content = file_input['content']
                with tempfile.NamedTemporaryFile(delete=False, mode='wb') as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name

                df_dask = dd.read_csv(tmp_path)
                state.column_options = df_dask.columns.tolist()
                state.selected_column = state.column_options[0]
                nonlocal np_data
                np_data = df_dask[state.selected_column].values.compute()
                update_histogram(state.bins)
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)

    @state.change("selected_column")
    def on_selected_column_change(selected_column, **kwargs):
        if state.file_input and selected_column:
            tmp_path = None
            try:
                content = state.file_input['content']
                with tempfile.NamedTemporaryFile(delete=False, mode='wb') as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name

                df_dask = dd.read_csv(tmp_path)
                nonlocal np_data
                np_data = df_dask[selected_column].values.compute()
                update_histogram(state.bins)
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)

    state.trame__title = f"{name} Histogram Viewer"
    state.bins = 5
    state.file_input = None
    state.column_options = []

    print(f"Starting {name} at http://localhost:{port}")
    return server.start(exec_mode="task", port=port), server

# -----------------------------------------------------------------------------
# Main Control Server
# -----------------------------------------------------------------------------

control_server = get_server("control_server", client_type="vue2")
control_state, control_ctrl = control_server.state, control_server.controller

# To keep track of server processes
server_processes = {}
next_port = 8088

# Initialize state for server list
control_state.server_list = []

def start_new_server():
    global next_port

    print("Starting new server")

    # Command to start the new server (it uses the current script to run it)
    command = [
        "python",
        __file__,  # Assuming this script is the main one, change if necessary
        "--launch_server",
        str(next_port)
    ]

    # Start the process and store it in the dictionary
    process = subprocess.Popen(command)
    # logging.debug(f"Started new server on port {next_port} with PID {process.pid}")
    # print("Started new server on port", next_port, "with PID", process.pid)
    server_processes[next_port] = process
    # logging.debug(f"Added process for port {next_port} to server_processes: {server_processes}")
    # print("Added process for port", next_port, "to server_processes:", server_processes)

    # Update the UI: append to server list and update state
    control_state.server_list.append({"port": next_port, "status": "Running"})

    next_port += 1

    control_state.dirty("server_list")

    # Update server list string
    render_ui()  # Update the UI

def stop_server(port):
    port = int(port)
    # logging.debug(f"Attempting to stop server on port {port}")
    print("Attempting to stop server on port", port)

    print("Server processes:", server_processes)  # Debugging statement
    
    process = server_processes.get(port)

    print("Process:", process)  # Debugging statement

    if process is None:
        # logging.warning(f"No process found for port {port}")
        print("ERROR: No process found for port", port)
        return

    if process:
        # logging.debug(f"Found process for port {port}: {process.pid}")
        print("Found process for port", port, ":", process.pid)
        
        # Send a termination signal to the process
        try:
            os.kill(process.pid, signal.SIGTERM)
            # logging.debug(f"Sent SIGTERM to process {process.pid}")
            print("Sent SIGTERM to process", process.pid)
        except Exception as e:
            logging.error(f"Failed to send SIGTERM to process {process.pid}: {e}")

        # Update server status in the UI
        for server in control_state.server_list:
            if server["port"] == port:
                server["status"] = "Stopped"
                # logging.debug(f"Updated server status to 'Stopped' for port {port}")
                print("Updated server status to 'Stopped' for port", port)

        # Remove the process from the dictionary
        del server_processes[port]
        # logging.debug(f"Removed process for port {port} from server_processes")
        print("Removed process for port", port, "from server_processes")

    else:
        logging.warning(f"No process found for port {port}")

    # Mark the state as dirty to trigger UI update
    control_state.dirty("server_list")

    # Update the UI to reflect the change
    render_ui()

# Register the stop_server function with the controller
@control_ctrl.trigger("handle_stop_server")
def handle_stop_server(port):
    stop_server(port)

# Define the color mapping for server status
control_state.level_to_color = {
    "Running": "green",
    "Stopped": "red"
}

def render_ui():
    print(f"Rendering UI with server list in layout: {control_state.server_list}")  # Debugging statement

    layout.title.set_text("Server Manager")
    layout.content.clear()

    with layout.content:
        # Start New Server Button
        with vuetify.VRow():
            with vuetify.VCol(cols="auto"):
                vuetify.VBtn(
                    "Start New Server",
                    click=start_new_server,
                    classes="ma-2",
                    color="primary",
                    dark=True,
                )

        # Display current servers
        with vuetify.VCard():
            vuetify.VCardText("Active Servers:")
            with vuetify.VList(shaped=True):
                print(f"self.control_state: {control_state}") 
                with vuetify.VListItem(v_for="(server, idx) in server_list", key="idx"):
                    print(f"server_list: {control_state.server_list}")
                    with vuetify.VListItemIcon():
                        vuetify.VIcon("mdi-server", color=("level_to_color[server.status]",))
                    with vuetify.VListItemContent():
                        vuetify.VListItemTitle("{{ server.port }} - {{ server.status }}")
                    with vuetify.VBtn(icon=True, click="trigger('handle_stop_server', [server.port.toString()])"):
                        vuetify.VIcon("mdi-stop", color=("level_to_color[server.status]",))

# -----------------------------------------------------------------------------
# Main interface layout
# -----------------------------------------------------------------------------

with SinglePageLayout(control_server) as layout:
    render_ui()

# -----------------------------------------------------------------------------
# Start the main control server
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    if "--launch_server" in sys.argv:
        # If we are launching a specific server (dynamic server creation)
        port = int(sys.argv[sys.argv.index("--launch_server") + 1])

        # Use the dynamic server creation code from the previous example
        task, _ = create_server(f"server_{port}", port)

        print("Type of task:", type(task))

        loop = asyncio.get_event_loop()
        loop.run_until_complete(task)
    else:
        # If we're running the control interface
        control_server.start(port=8080)