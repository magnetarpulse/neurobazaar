# For multi-server management, also for system management 
import os
import sys

cwd = os.getcwd()
index = cwd.index('neurobazaar')
neurobazaar_dir = cwd[:index + len('neurobazaar')]
sys.path.insert(0, neurobazaar_dir)

# Core libraries for rendering
from trame.app import get_server
from trame.decorators import TrameApp, change
from trame.widgets import vtk, vuetify
from trame.ui.vuetify import SinglePageLayout
import vtk as standard_vtk

# Core libraries for data processing
import numpy as np
import dask.dataframe as dd
import dask.array as da
import dask_histogram as dh
import boost_histogram as bh
from dask.distributed import Client

# For manipulating CSV files
import csv
import tempfile
from neurobazaar.services.datastorage.localfs_datastore import LocalFSDatastore

# Base class for the histogram application
from abc import abstractmethod

## ================================================================= ## 
## Visualization service. Histogramming sub service. The base class. ##         
## ================================================================= ##

@TrameApp()
class DemoBaseHistogram:    

    # ---------------------------------------------------------------------------------------------
    # Constructor for the BaseHistogramApp class.
    # --------------------------------------------------------------------------------------------- 

    def __init__(self, name, port, np_data=None):
        self.server = get_server(name, client_type="vue2")
        self.port = port

        self.np_data = np_data if np_data is not None else np.random.normal(size=1_000)
        self.dask_data = da.empty(shape=(0,))
        
        self.server.state.bins = 5 
        self.server.state.file_input = None
        self.server.state.selected_column = None
        self.server.state.column_options = []
        self.server.state.dataset_names = [] 
        
        self.data_min = None
        self.data_max = None
        self.data_changed = True
        self.hist_cache = {}
        
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
    # Method using VTK to update histogram and render it on the server-side
    # ---------------------------------------------------------------------------------------------
    
    def update_histogram(self, bins):
        bins = int(bins)

        if self.data_changed:
            self.dask_data = da.from_array(self.np_data, chunks='auto')
            self.data_changed = False
            print("Data changed. Computing histogram data...")

        self.compute_histogram_data_with_dask(self.dask_data, bins)

        self.arrX.Reset()
        self.arrY.Reset()

        for i in range(len(self.hist)):
            self.arrX.InsertNextValue(self.bin_edges[i])
            self.arrY.InsertNextValue(self.hist[i])

        self.update_the_client_view()
    
    # ---------------------------------------------------------------------------------------------
    # Method to update the render window to the client-side
    # ---------------------------------------------------------------------------------------------
    
    def update_the_client_view(self):
        self.client_view.update()   

    # ---------------------------------------------------------------------------------------------
    # Method using Dask to compute histogram data
    # ---------------------------------------------------------------------------------------------
    
    def compute_histogram_data_with_dask(self, dask_data, bins):        
        if not isinstance(dask_data, da.Array):
            dask_data = da.from_array(dask_data, chunks='auto')
        else:
            dask_data = dask_data
        
        if self.data_min is None or self.data_max is None:
            self.data_min, self.data_max = self.compute_min_and_max_values_using_dask(dask_data)

        key = (bins, self.data_min, self.data_max)

        if key in self.hist_cache:
            self.hist, self.bin_edges = self.hist_cache[key]
        else:
            dask_hist = dh.factory(dask_data, axes=(bh.axis.Regular(bins, self.data_min, self.data_max+1),))
            dask_hist = dask_hist.persist() 
            hist_result = self.convert_agghistogram_to_numpy_array_of_frequencies(dask_hist)
            self.hist = hist_result
            _, self.bin_edges = da.histogram(dask_data, bins=bins, range=(self.data_min, self.data_max))

            self.hist_cache[key] = (self.hist, self.bin_edges)

        if not isinstance(self.hist, np.ndarray):
            self.hist = self.convert_dask_to_numpy(self.hist)

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
            temp_file.write(content)
            temp_path=temp_file.name
        
        dask_df = dd.read_csv(temp_path)
        
        return dask_df, temp_path
    
    # ---------------------------------------------------------------------------------------------
    # Method using Dask to calculate the minimum and maximum values of data
    # ---------------------------------------------------------------------------------------------
    
    def compute_min_and_max_values_using_dask(self, dask_data):
        if not isinstance(dask_data, da.Array):
            dask_data = da.from_array(dask_data, chunks='auto')
        else:
            dask_data = dask_data
        
        data_min = dask_data.min().compute()
        data_max = dask_data.max().compute()
        
        return data_min, data_max
    
    # ---------------------------------------------------------------------------------------------
    # State change handler for bins
    # ---------------------------------------------------------------------------------------------
    
    @change("bins")
    def on_bins_change(self, bins, **trame_scripts):
        self.update_histogram(bins)

    # ---------------------------------------------------------------------------------------------
    # State change handler for file_input
    # ---------------------------------------------------------------------------------------------
    
    @change("file_input")
    def on_file_input_change(self, file_input, **trame_scripts):
        if file_input:
            self.data_min = None
            self.data_min = None
            self.data_changed = True
            try:
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
                
                self.update_histogram(self.server.state.bins)
                
            except KeyError as e:
                print(f"KeyError: {e} - Check the structure of file_input and the CSV file.")
            except Exception as e:
                print(f"An error occurred (file_input): {e}")
                
    # ---------------------------------------------------------------------------------------------
    # State change handler for column_options
    # ---------------------------------------------------------------------------------------------
    
    @change("column_options")
    def on_column_options_change(self, column_options, **trame_scripts):
        self.server.state.column_options = column_options
    
    # ---------------------------------------------------------------------------------------------
    # State change handler for selected_column
    # ---------------------------------------------------------------------------------------------
    
    @change("selected_column")
    def on_selected_column_change(self, selected_column, **trame_scripts):
        self.data_min = None
        self.data_max = None
        self.data_changed = True
        if self.server.state.selected_column and selected_column:
            try:
                self.np_data =  self.compute_with_threads(self.computed_df[self.server.state.selected_column])
                self.update_histogram(self.server.state.bins)
                    
            except KeyError as e:
                print(f"KeyError: {e} - Check the structure of the CSV file.")
            except Exception as e:
                print(f"An error occurred (selected_column): {e}")

    # ---------------------------------------------------------------------------------------------
    # State change handler for dataset_names
    # ---------------------------------------------------------------------------------------------

    @change("selected_dataset")
    def compute_dataset(self, selected_dataset, **trame_scripts):
        self.data_min = None
        self.data_min = None
        self.data_changed = True
        try:
            if selected_dataset is None:
                print("No dataset selected.")
                return
            
            csv_file_path = os.path.join(neurobazaar_dir, 'datasets_server', f"{selected_dataset}.csv")
            df = dd.read_csv(csv_file_path, assume_missing=True)
            self.computed_df = df

            self.server.state.column_options = self.computed_df.columns.tolist()
            self.on_column_options_change(self.server.state.column_options)
            self.server.state.selected_column = self.server.state.column_options[0] 

            selected_column_data = self.computed_df[self.server.state.selected_column] 
            selected_column_data = self.compute_with_threads(selected_column_data)

            self.np_data = selected_column_data

            self.update_histogram(self.server.state.bins)
        except Exception as e:
            print("An error occurred while computing the dataset:")
            print(e)

    # ---------------------------------------------------------------------------------------------
    # UI layout
    # ---------------------------------------------------------------------------------------------

    def setup_layout(self):
        with SinglePageLayout(self.server) as layout:
            layout.title.set_text(self.server.name)

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
                vuetify.VSelect(
                    v_model=("selected_dataset", None),
                    items=("dataset_names",),
                    label="Select Datasets",
                    style="padding-top: 20px;", 
                )
                vuetify.VSelect(
                    v_model=("selected_column", None),
                    items=("column_options",),
                    label="Select Columns",
                    style="padding-top: 20px;", 
                )

            with layout.content:
                with vuetify.VContainer(
                    fluid=True,
                    classes="pa-0 fill-height", 
                ):
                    self.client_view = vtk.VtkRemoteView(
                        self.renderWindow, trame_server=self.server, ref="view"
                    )

    # ---------------------------------------------------------------------------------------------
    # Get data from the user uploading to local file store, retrieved using LocalFSDatastore
    # ---------------------------------------------------------------------------------------------

    @abstractmethod
    def get_data_from_user(self):
        datastore_dir = os.path.join(neurobazaar_dir, 'datastore')
        datastore = LocalFSDatastore(storeDirPath=datastore_dir)

        uuids = os.listdir(datastore_dir)
        print("UUIDs:", uuids)

        uuid_to_name = {
            uuids[0]: "MaxSlices_newMode_Manuf_Int",
            uuids[1]: "MaxSlices_wOoDScore",
            uuids[2]: "Patient_Level-Table_Test",
            uuids[3]: "AllSlices_Manuf",
            uuids[4]: "UCI_AIDS"
        }

        names = []
        csv_files = []

        for uuid in uuids:
            dataset_file = datastore.getDataset(uuid)
            if dataset_file is not None:
                data = dataset_file.read()
                print("Type of data:", type(data))
                name = uuid_to_name[uuid]
                print(f"Name: {name}")

                data_list = data.decode('utf-8').split(',')

                csv_file_path = os.path.join(neurobazaar_dir, 'datasets_server', f"{name}.csv")
                with open(csv_file_path, 'w', newline='') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(data_list)
                    print(f"Data written to CSV file: {csv_file_path}")

                with open(csv_file_path, 'r') as file:
                    lines = file.read().replace('"', '')

                with open(csv_file_path, 'w') as file:
                    file.write(lines)

                names.append(name)
                csv_files.append(csv_file_path)
            else:
                print(f"No dataset found with UUID {uuid}")

        return names, csv_files

    # ---------------------------------------------------------------------------------------------
    # Get the names of the datasets from the user (hard coded for now)
    # ---------------------------------------------------------------------------------------------

    @abstractmethod
    def update_dataset_names(self):
        names, _ = self.get_data_from_user()
        self.server.state.dataset_names = names
        print(self.server.state.dataset_names)

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

# ----------------------------------------------------------------------------- 
# Main (Guard) # Commented out for import. Uncomment for testing
# ----------------------------------------------------------------------------- 

'''
if __name__ == "__main__":
    app = DemoBaseHistogram("Histogram", 8000)
    print("Getting data from the user...")
    names, csv_file = app.get_data_from_user()
    app.update_dataset_names()
    app.start_new_server_immediately()

    # for files in csv_file:
    #   if os.stat(files).st_size != 0:  
    #        try:
    #            df = dd.read_csv(files)
    #            first_column = df.columns[0]
    #            print(f"First column of {files}: {first_column}")
    #        except pd.errors.ParserError as e:
    #            print(f"Error reading {files}: {e}")
    #    else:
    #        print(f"File {files} is empty.")
'''