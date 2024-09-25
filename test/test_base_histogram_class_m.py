import os
import sys
import asyncio
import subprocess
import signal
import threading

import inspect
import traceback

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

@TrameApp()
class BaseHistogramApp:    
    def __init__(self, name, port, np_data=None):
        self.server = get_server(name, client_type="vue2")

        self.port = port
        
        # self.np_data = np_data if np_data is not None else np.random.normal(size=1_000_000_000)

        self.np_data = np_data if np_data is not None else np.random.normal(size=1_000)

        # self.np_data = np.abs(np_data) if np_data is not None else np.abs(np.random.normal(size=1_000))

        # self.np_data = da.random.normal(size=1_000_000, chunks='auto')

        self.dask_data = da.empty(shape=(0,))
        
        self.server.state.bins = 1

        self.server.state.file_input = None
        
        self.server.state.selected_column = None

        self.server.state.column_options = [] 
        
        self.dask_method_invoked = 0
        
        self.numpy_method_invoked = 0
        
        self.data_min = None
        self.data_max = None
        self.data_changed = True
        self.hist_cache = {}
        self.initial_render_done = True
        self.histogram_vtk() 

        self.client_view = vtk.VtkRemoteView(
            self.renderWindow, trame_server=self.server, ref="view"
        )
        
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
        self.plot.SetColor(22, 29, 111, 255)

        outline = standard_vtk.vtkPen()
        outline.SetColor(255, 255, 255, 255)
        self.plot.SetPen(outline)
            
        self.chart = standard_vtk.vtkChartXY()
        self.chart.SetBarWidthFraction(1.0)
        self.chart.GetAxis(0).SetTitle("Frequency")
        self.chart.GetAxis(1).SetTitle("Data Values")
        
        font_size_title = 16  # X and Y axis titles
        title_props_x = self.chart.GetAxis(0).GetTitleProperties()
        title_props_y = self.chart.GetAxis(1).GetTitleProperties()
        title_props_x.SetFontSize(font_size_title)
        title_props_y.SetFontSize(font_size_title)

        font_size=12 # X and Y axis numbers
        label_props_x = self.chart.GetAxis(0).GetLabelProperties()
        label_props_y = self.chart.GetAxis(1).GetLabelProperties()
        label_props_x.SetFontSize(font_size)
        label_props_y.SetFontSize(font_size)
        
        # self.chart.GetAxis(0).SetBehavior(standard_vtk.vtkAxis.FIXED)
        self.chart.GetAxis(1).SetMinimum(0)
        self.chart.GetAxis(1).SetMaximum(7000)
        self.chart.GetAxis(1).SetBehavior(standard_vtk.vtkAxis.FIXED)
        self.chart.AddPlot(self.plot)
            
        self.view = standard_vtk.vtkContextView()
        self.view.GetScene().AddItem(self.chart)
            
        self.renderWindow = self.view.GetRenderWindow()
        self.view.GetRenderWindow().SetSize(800, 600)

           
    # ---------------------------------------------------------------------------------------------
    # Method using VTK to update histogram and render it on the server-side
    # ---------------------------------------------------------------------------------------------
    
    def update_histogram(self, bins):

        if self.np_data is None:
            # Handle the case when there is no data
            print("No data available to update the histogram.")
            # Clear the histogram data
            self.arrX.Reset()
            self.arrY.Reset()
        
            # Optionally set axis limits to zero to hide the plot
            self.chart.GetAxis(0).SetMaximum(0)  # Hide x-axis
            self.chart.GetAxis(1).SetMaximum(0)  # Hide y-axis
        
            # Update the client view to reflect that there is no data
            self.update_the_client_view()
            return  # Exit the method to prevent further processing
            
        # Proceed with creating the Dask array if data is available
        self.dask_data = da.from_array(self.np_data, chunks='auto')

        start_time_to_update_histogram = time.time()
    
        bins = int(bins)

        if self.data_changed:
            self.dask_data = da.from_array(self.np_data, chunks='auto')
            self.data_changed = False

        print(f"Updating histogram with number of bins: {bins} and count of data: {len(self.dask_data)}")

        self.compute_histogram_data_with_dask(self.dask_data, bins)

        start_time_vtk = time.time()

        # Reset the arrays for new data
        self.arrX.Reset()
        self.arrY.Reset()

        for i in range(len(self.hist)):
            self.arrX.InsertNextValue(self.bin_edges[i])
            self.arrY.InsertNextValue(self.hist[i])

        # Set the x-axis max to the max bin edge
        max_x = max(self.bin_edges)
        self.chart.GetAxis(0).SetMaximum(max_x)

        # Set the y-axis max to the maximum histogram frequency
        max_y = max(self.hist)
        self.chart.GetAxis(1).SetMaximum(max_y)

        self.update_the_client_view()

        end_time_vtk = time.time()
    
        end_time_to_update_histogram = time.time()
        print(f"VTK rendering took {end_time_vtk - start_time_vtk} seconds")
        print(f"Updating the histogram, after all computations and rendering, took {end_time_to_update_histogram - start_time_to_update_histogram} seconds")

    # ---------------------------------------------------------------------------------------------
    # Method to update the render window to the client-side
    # ---------------------------------------------------------------------------------------------
    
    def update_the_client_view(self):
        self.client_view.update()   
        print("The client view has been updated") 

    # ---------------------------------------------------------------------------------------------
    # Method using Dask to compute histogram data
    # ---------------------------------------------------------------------------------------------
    
    def compute_histogram_data_with_dask(self, dask_data, bins):
        computation_type = "Dask (threaded scheduler)"
        
        if not isinstance(dask_data, da.Array):
            dask_data = da.from_array(dask_data, chunks='auto')
        else:
            dask_data = dask_data
        
        if self.data_min is None or self.data_max is None:
            # print("Detected that data_min and data_max are None")
            self.data_min, self.data_max = self.compute_min_and_max_values_using_dask(dask_data)
        
        start_time_to_calculate_histogram = time.time()

        key = (bins, self.data_min, self.data_max)

        if key in self.hist_cache:
            start_time_to_retrieve = time.time() 
            self.hist, self.bin_edges = self.hist_cache[key]
            end_time_to_retrieve = time.time()
            print(f"Retrieving the cached result took {end_time_to_retrieve - start_time_to_retrieve} seconds")
        else:
            dask_hist = dh.factory(dask_data, axes=(bh.axis.Regular(bins, self.data_min, self.data_max),))
            dask_hist = dask_hist.persist() 
            hist_result = self.convert_agghistogram_to_numpy_array_of_frequencies(dask_hist)
            # hist_result = self.convert_agghistogram_to_numpy_array_of_frequencies_distributed(dask_hist)
            self.hist = hist_result
            _, self.bin_edges = da.histogram(dask_data, bins=bins, range=(self.data_min, self.data_max+1))

            self.hist_cache[key] = (self.hist, self.bin_edges)
            
        end_time_to_calculate_histogram = time.time()

        if not isinstance(self.hist, np.ndarray):
            self.hist = self.convert_dask_to_numpy(self.hist)

        print(f"Calculating the histogram using {computation_type} took {end_time_to_calculate_histogram - start_time_to_calculate_histogram} seconds")

    # ---------------------------------------------------------------------------------------------
    # Method using Dask compute method to convert AggHistogram to a NumPy array of frequencies
    # ---------------------------------------------------------------------------------------------

    def convert_agghistogram_to_numpy_array_of_frequencies(self, dask_object):
        result = dask_object.compute(scheduler='threads', num_workers=21) 
        frequencies = result.to_numpy()[0]
        return frequencies

    # ---------------------------------------------------------------------------------------------
    # Method using Dask distributed to convert AggHistogram to a NumPy array of frequencies
    # ---------------------------------------------------------------------------------------------

    def convert_agghistogram_to_numpy_array_of_frequencies_distributed(self, dask_object):
        client = Client()
        dask_hist = client.compute(dask_object)
        frequencies = dask_hist.result().to_numpy()[0]
        return frequencies

    # ---------------------------------------------------------------------------------------------
    # Method using Dask compute method to convert Dask object to NumPy array
    # ---------------------------------------------------------------------------------------------

    def convert_dask_to_numpy(self, dask_object):
        result = dask_object.compute(scheduler='threads', num_workers=21) 
        return result
        
    # ---------------------------------------------------------------------------------------------
    # Method using Dask compute method with the scheduler argument passed as 'threads'
    # ---------------------------------------------------------------------------------------------
    
    def compute_with_threads(self, dask_object):
        return dask_object.values.compute(scheduler='threads')
    
    # ---------------------------------------------------------------------------------------------
    # Method using Dask to read a comma-separated values (csv) file into a Dask DataFrame
    # ---------------------------------------------------------------------------------------------
    
    def dask_read_csv(self, content):
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            # temp_file.write(content.getvalue())
            temp_file.write(content)
            temp_path=temp_file.name
        
        dask_df = dd.read_csv(temp_path)
        
        return dask_df, temp_path
    
    # ---------------------------------------------------------------------------------------------
    # Method using Dask to calculate the minimum and maximum values of data
    # ---------------------------------------------------------------------------------------------
    
    def compute_min_and_max_values_using_dask(self, dask_data):
        if not isinstance(dask_data, da.Array):
            # print("Changing the data to Dask data")
            # start_time_to_change_data_to_dask_data = time.time()
            dask_data = da.from_array(dask_data, chunks='auto')
            # end_time_to_change_data_to_dask_data = time.time()
            # print(f"Changing the data to Dask data during min and max took {end_time_to_change_data_to_dask_data - start_time_to_change_data_to_dask_data} seconds")
        else:
            dask_data = dask_data
        
        data_min = dask_data.min().compute()
        data_max = dask_data.max().compute()
        
        # print("Invoked method: compute_min_and_max_values_using_dask")
        # print("Method output - Min: ", data_min)
        # print("Method output - Max: ", data_max)
        self.dask_method_invoked += 1
    
        print("The number of times the compute_min_and_max_values_using_dask method has been been called: ", self.dask_method_invoked)
        
        return data_min, data_max
    
    # ---------------------------------------------------------------------------------------------
    # State change handler for bins
    # ---------------------------------------------------------------------------------------------
    
    @change("bins")
    def on_bins_change(self, bins, **kwargs):
        self.update_histogram(bins)
             

    # ---------------------------------------------------------------------------------------------
    # State change handler for file_input
    # ---------------------------------------------------------------------------------------------
    
    @change("file_input")
    def on_file_input_change(self, file_input, **kwargs):
        if file_input:
            self.data_min = None
            self.data_min = None
            self.data_changed = True
            try:
                # content = BytesIO(base64.b64decode(file_input['content']))
                content = file_input['content']
                dask_df, temp_path = self.dask_read_csv(content)
                
                self.server.state.column_options = dask_df.columns.tolist()
                self.on_column_options_change(self.server.state.column_options)
                self.server.state.selected_column = self.server.state.column_options[0] 

                selected_column_data = dask_df[self.server.state.selected_column] 
                selected_column_data = self.compute_with_threads(selected_column_data)

                self.np_data = selected_column_data
                
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
                else:
                    pass
                
                self.bins = 5
                self.update_histogram(self.bins)
                
            except KeyError as e:
                print(f"KeyError: {e} - Check the structure of file_input and the CSV file.")
            except Exception as e:
                print(f"An error occurred (file_input): {e}")
        else:
            
            # Clear the selected column when the file input is cleared
            self.server.state.column_options = []
            self.server.state.selected_column = None
            
            self.np_data = None  # Clear the data from plot
            #self.server.state.bins = 1  # Set bins to 5
            self.clear_histogram()
            #self.update_histogram(self.server.state.bins)  # Update the histogram with new bins
        
    def clear_histogram(self):
        # Implement logic to clear or reset the plot
        # For example, set empty data or reinitialize your histogram
        self.dask_data = None  # Or whatever is needed to clear the plot
        self.server.state.bins = 5  # Set bins to 1
        self.update_histogram(self.server.state.bins)


    # ---------------------------------------------------------------------------------------------
    # State change handler for column_options
    # ---------------------------------------------------------------------------------------------
    
    @change("column_options")
    def on_column_options_change(self, column_options, **kwargs):
        self.server.state.column_options = column_options
    
    # ---------------------------------------------------------------------------------------------
    # State change handler for selected_column
    # ---------------------------------------------------------------------------------------------
    
    @change("selected_column")
    def on_selected_column_change(self, selected_column, **kwargs):
        self.data_min = None
        self.data_max = None
        self.data_changed = True
        if self.server.state.file_input and self.server.state.selected_column and selected_column:
            try:
                # content = base64.b64decode(self.server.state.file_input['content'])
                content = self.server.state.file_input['content']
                # df, temp_path = self.dask_read_csv(BytesIO(content))  
                df, temp_path = self.dask_read_csv(content)  
                
                self.np_data =  self.compute_with_threads(df[self.server.state.selected_column])

                self.update_histogram(self.server.state.bins)
                
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
                else:
                    pass
                    
            except KeyError as e:
                print(f"KeyError: {e} - Check the structure of the CSV file.")
            except Exception as e:
                print(f"An error occurred (selected_column): {e}")

    # ---------------------------------------------------------------------------------------------
    # UI layout
    # ---------------------------------------------------------------------------------------------

    def setup_layout(self):
        with SinglePageLayout(self.server) as layout:
            layout.title.set_text(self.server.name)

            # Top toolbar
            with layout.toolbar:
                
                vuetify.VSpacer()
                vuetify.VSlider(
                    v_model=("bins", 1),
                    min=1,
                    max=100,
                    step=1,
                    label="Number of Bins",
                    hide_details=False,
                    dense=True,
                    style="padding-top: 20px;",
                    color="rgb(22, 29, 111)",
                       
                )
                vuetify.VSpacer()
                
                vuetify.VFileInput(
                    v_model=("file_input", None),
                    label="Upload CSV File",
                    accept=".csv",
                    style="padding-top: 20px;",
                    clear_icon="mdi-delete",
                     
                )
                vuetify.VSpacer()
                vuetify.VSelect(
                    v_model=("selected_column", None),
                    items=("column_options",),
                    label="Select Column",
                    style="padding-top: 20px;",
                    clearable=True,
                    dense=True,  # Compact style
                     
                )
                vuetify.VSpacer()


            # Content area for VTK rendering
            with layout.content:
                with vuetify.VContainer(
                    fluid=True,
                    classes="pa-0 fill-height",  
                    style={"width": "85%", "height": "650px", "margin": "30px auto 30px auto"}
                ):
                    # Directly inset the client view
                    self.client_view = vtk.VtkRemoteView(
                        self.renderWindow, trame_server=self.server, ref="view"
                    )
                    # Insert VTK Remote View inside the container
                    '''
                    vtk.VtkRemoteView(
                        self.renderWindow, trame_server=self.server, ref="view"
                    )
                    '''

    # ---------------------------------------------------------------------------------------------
    # Method to start a new server (main). Not to be used in a multi-process environment
    # ---------------------------------------------------------------------------------------------

    @abstractmethod
    def start_new_server_immediately(self):
        print(f"Starting {self.server.name} at http://localhost:{self.port}/index.html")
        self.server.start(exec_mode="main", port=self.port)

    # ---------------------------------------------------------------------------------------------
    # Method to start a new server (async). To be used in a multi-process environment
    # ---------------------------------------------------------------------------------------------

    @abstractmethod
    async def start_new_server_async(self):
        print(f"Starting {self.server.name} at http://localhost:{self.port}/index.html")
        return await self.server.start(exec_mode="task", port=self.port)

    # ---------------------------------------------------------------------------------------------
    # Method to kill a server. Child/derived classes should implement this method
    # ---------------------------------------------------------------------------------------------

    @abstractmethod
    def kill_server(self):
        # print(f"Stopping {self.server.name} at port {self.port}")
        # self.server.stop()
        pass

    # ---------------------------------------------------------------------------------------------
    # Method to debug the server: Get the entire stack trace
    # ---------------------------------------------------------------------------------------------

    def trace_calls(self, frame, event, arg):
        with open('logging_stack.txt', 'a') as f:  
            if event == 'call':
                code = frame.f_code
                function_name = code.co_name
                file_name = code.co_filename
                line_number = frame.f_lineno
                f.write(f"Calling {function_name} in {file_name} at line {line_number}\n")
        
        return self.trace_calls

class ServerManager:
    def __init__(self):
        self.servers_manager = get_server("Server_Manager", client_type="vue2")
        self.control_state, self.control_ctrl = self.servers_manager.state, self.servers_manager.controller
        self.servers = {}
        self.next_port = 5456
        self.control_state.server_list = []

        # Define the color mapping for server status
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

        # Command to start the new server
        command = [
            "python",
            "multi_trame_server_uncommented.py",  
            "--launch_server",
            str(self.next_port)
        ]

        # Start the process and store it in the dictionary
        process = subprocess.Popen(command)
        self.servers[self.next_port] = process

        print(f"Started new server on port {self.next_port} with PID {process.pid}")

        # Add the new server to the server_list
        self.control_state.server_list.append({
            'port': self.next_port,
            'status': 'Running'
        })

        print(f"Server list after starting new server: {self.control_state.server_list}")  # Debugging statement

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
            # os.kill(server.process.pid, signal.SIGTERM)
            os.kill(server.pid, signal.SIGTERM) 
            print(f"Server at port {port} has been stopped")
        except Exception as e:
            print(f"An error occurred while stopping server at port {port}: {e}")

        del self.servers[port]

        # Find the server in the server_list and update its status
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
        # print(f"Rendering UI with server list in layout: {self.control_state.server_list}")  # Debugging statement

        with SinglePageLayout(self.servers_manager) as layout:
            layout.title.set_text("Server Manager")
            layout.content.clear()

            with layout.content:
                # Start New Server Button
                with vuetify.VRow():
                    with vuetify.VCol(cols="auto"):
                        vuetify.VBtn(
                            "Start New Server",
                            click=self.start_new_server,
                            classes="ma-2",
                            color="primary",
                            dark=True,
                        )

                # Display current servers
                with vuetify.VCard():
                    vuetify.VCardText("Active Servers:")
                    with vuetify.VList(shaped=True):
                        # print(f"self.control_state: {self.control_state}")
                        with vuetify.VListItem(v_for="(server, idx) in server_list", key="idx"):
                            # print(f"server_list: {self.control_state.server_list}")
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
    app = BaseHistogramApp("Histogram", 8000)
    app.start_new_server_immediately()
