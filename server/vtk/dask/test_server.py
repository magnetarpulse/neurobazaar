import os
import sys

current_dir = os.path.dirname(os.path.realpath(__file__))
relative_path = os.path.join('..', '..', 'my_modules')
my_modules_path = os.path.abspath(os.path.join(current_dir, relative_path))
sys.path.append(my_modules_path)

from trame.app import get_server
from trame.decorators import TrameApp, change
from trame.widgets import vtk
import vtk as standard_vtk

import numpy as np

import dask.dataframe as dd
import dask.array as da
import dask_histogram as dh
import boost_histogram as bh

from update_histogram import input_histogram_values

import tempfile
from io import BytesIO
import base64
import time

@TrameApp()
class HistogramApp:    
    def __init__(self, np_data=None):
        self.server = get_server(client_type="vue2")
        
        self.np_data = np_data if np_data is not None else np.random.normal(size=1_000_000_000)

        self.dask_data = da.empty(shape=(0,))
        
        self.server.state.bins = 5 
    
        self.server.state.file_input = None
        
        self.server.state.selected_column = None 
        
        self.dask_method_invoked = 0
        
        self.numpy_method_invoked = 0
        
        self.data_min = None
        self.data_max = None

        self._last_np_data = False
        self.dask_manager = False
        
        self.histogram_vtk() 

        self.client_view = vtk.VtkRemoteView(
            self.renderWindow, trame_server=self.server, ref="view"
        )
    
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

        input_histogram_values(self.bin_edges, self.hist, self.arrX, self.arrY)

        self.table.AddColumn(self.arrX)
        self.table.AddColumn(self.arrY)
            
        self.plot = standard_vtk.vtkPlotBar()
        self.plot.SetInputData(self.table)
        self.plot.SetInputArray(0, "X Axis")
        self.plot.SetInputArray(1, "Frequency")
        self.plot.SetColor(0, 0, 0, 255)
            
        self.chart = standard_vtk.vtkChartXY()
        self.chart.SetBarWidthFraction(1.0)
        self.chart.GetAxis(0).SetTitle("Frequency")
        self.chart.GetAxis(1).SetTitle("Feature")
        self.chart.AddPlot(self.plot)
            
        self.view = standard_vtk.vtkContextView()
        self.view.GetScene().AddItem(self.chart)
            
        self.renderWindow = self.view.GetRenderWindow()
        self.view.GetRenderWindow().SetSize(800, 600)
    
    # ---------------------------------------------------------------------------------------------
    # Method using VTK to update histogram and render it on the server-side
    # ---------------------------------------------------------------------------------------------
    
    def update_histogram(self, bins):
        start_time_to_update_histogram = time.time() 
        
        bins = int(bins)

        print("Type of self.np_data: ", type(self.np_data))
        print("Number of data: ", len(self.np_data))
        print("Bins: ", bins)

        if self.dask_manager==False:
            self.dask_data = da.empty(shape=(0,))
        else:
            self.dask_data = self.dask_data

        if not isinstance(self.np_data, da.Array) and self._last_np_data==False:
            self.dask_data = da.from_array(self.np_data, chunks='auto')
            self.dask_data = self.dask_data.persist()
            self.dask_manager=True
            self._last_np_data = True
        else:
            pass

        self.compute_histogram_data_with_dask(self.dask_data, bins)

        start_time_vtk = time.time()

        self.arrX.Reset()
        self.arrY.Reset()

        input_histogram_values(self.bin_edges, self.hist, self.arrX, self.arrY)
        
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

    # ---------------------------------------------------------------------------------------------
    # Method using Dask to compute histogram data
    # ---------------------------------------------------------------------------------------------
    
    def compute_histogram_data_with_dask(self, dask_data, bins):
        computation_type = "Dask (threaded scheduler)"
        
        if not isinstance(dask_data, da.Array):
            dask_data = da.from_array(dask_data, chunks='auto')
            dask_data = dask_data.persist()
        else:
            dask_data = dask_data
        
        if self.data_min is None or self.data_max is None:
            self.data_min, self.data_max = self.compute_min_and_max_values_using_dask(dask_data)
        
        start_time_to_calculate_histogram = time.time()
        
        dask_hist = dh.factory(dask_data, axes=(bh.axis.Regular(bins, self.data_min, self.data_max),), storage=bh.storage.Int64())
        
        dask_hist = dask_hist.persist() 
        hist_result = self.convert_agghistogram_to_numpy_array_of_frequencies(dask_hist)
        self.hist = hist_result
        _, self.bin_edges = da.histogram(dask_data, bins=bins, range=(self.data_min, self.data_max))
        
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
    # Method using Dask compute method with the scheduler argument passed as 'threads'
    # ---------------------------------------------------------------------------------------------
    
    def compute_with_boost_histogram_and_numpy(self, data, bins):
        bh.numpy.histogram(data, bins=bins, range=(self.data_min, self.data_max))
    
    # ---------------------------------------------------------------------------------------------
    # Method using Dask to read a comma-separated values (csv) file into a Dask DataFrame
    # ---------------------------------------------------------------------------------------------
    
    def dask_read_csv(self, content):
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(content.getvalue())
            temp_path=temp_file.name
        
        dask_df = dd.read_csv(temp_path)
        
        return dask_df, temp_path
    
    # ---------------------------------------------------------------------------------------------
    # Method using Dask to calculate the minimum and maximum values of data
    # ---------------------------------------------------------------------------------------------
    
    def compute_min_and_max_values_using_dask(self, dask_data):
        if not isinstance(dask_data, da.Array):
            start_time_to_change_data_to_dask_data = time.time()
            dask_data = da.from_array(dask_data, chunks='auto')
            end_time_to_change_data_to_dask_data = time.time()
            print(f"Changing the data to Dask data during min and max took {end_time_to_change_data_to_dask_data - start_time_to_change_data_to_dask_data} seconds")
        else:
            dask_data = dask_data
        
        data_min = dask_data.min().compute()
        data_max = dask_data.max().compute()
        
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
            try:             
                content = BytesIO(base64.b64decode(file_input['content']))
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
    def on_column_options_change(self, column_options, **kwargs):
        self.server.state.column_options = column_options
    
    # ---------------------------------------------------------------------------------------------
    # State change handler for selected_column
    # ---------------------------------------------------------------------------------------------
    
    @change("selected_column")
    def on_selected_column_change(self, selected_column, **kwargs):
        self.data_min = None
        self.data_max = None
        if self.server.state.file_input and self.server.state.selected_column and selected_column:
            try:
                content = base64.b64decode(self.server.state.file_input['content'])
                df, temp_path = self.dask_read_csv(BytesIO(content))  
                
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
                
if __name__ == "__main__":
    histogram_app= HistogramApp()
    histogram_app.server.start()