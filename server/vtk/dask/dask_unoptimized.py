import os

from trame.app import get_server
from trame.decorators import TrameApp, change
from trame.widgets import vtk
import vtk as standard_vtk

import dask.dataframe as dd
import dask.array as da

import tempfile
from io import BytesIO
import base64
import time

@TrameApp()
class HistogramApp:    
    def __init__(self):
        self.server = get_server(client_type="vue2")

        self.np_data = 0

        self.dask_data = da.empty(shape=(0,))
        
        self.server.state.bins = 5 
    
        self.server.state.file_input = None
        
        self.server.state.selected_column = None 
        
        self.dask_method_invoked = 0
        
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
            self.dask_manager=True
            self._last_np_data = True
            print("Type of self.dask_data: ", type(self.dask_data))
        else:
            pass

        self.compute_histogram_data_with_dask(self.dask_data, bins)

        self.arrX.Reset()
        self.arrY.Reset()

        for i in range(len(self.hist)):
            self.arrX.InsertNextValue(self.bin_edges[i])
            self.arrY.InsertNextValue(self.hist[i])

        self.table.Modified()
        self.renderWindow.Render()
        
        self.update_the_client_view()
        
        end_time_to_update_histogram = time.time()
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
        
        if not isinstance(dask_data, da.Array):
            dask_data = da.from_array(dask_data, chunks='auto') 
        else:
            dask_data = dask_data
        
        if self.data_min is None or self.data_max is None:
            self.data_min, self.data_max = self.compute_min_and_max_values_using_dask(dask_data)
            print("Finished computing min and max values using Dask")
        
        start_time_to_calculate_histogram = time.time()
        self.hist, self.bin_edges = da.histogram(dask_data, bins=bins, range=(self.data_min, self.data_max))
        end_time_to_calculate_histogram = time.time()

        print(f"Calculating the histogram using took {end_time_to_calculate_histogram - start_time_to_calculate_histogram} seconds")
        
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
            print("Data is already a Dask array")
    
        data_min = dask_data.min().compute()
        data_max = dask_data.max().compute()

        self.dask_method_invoked += 1
        print(f"Invoked the Dask method {self.dask_method_invoked} times")
        
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