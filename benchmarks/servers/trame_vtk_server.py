from trame.app import get_server
from trame.decorators import TrameApp, change
from trame.widgets import vtk, vuetify
from trame.ui.vuetify import SinglePageLayout
import vtk as standard_vtk

import numpy as np
import dask.array as da
import dask_histogram as dh
import boost_histogram as bh

import time

@TrameApp()
class HistogramApp:    
    def __init__(self, np_data=None):
        self.server = get_server(client_type="vue2")
        
        self.np_data = np_data if np_data is not None else np.random.normal(size=1_000_000_000)
        self.dask_data = da.empty(shape=(0,))
        
        self.server.state.bins = 5 
        
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
        else:
            pass
        self.compute_histogram_data_with_dask(self.dask_data, bins)
        start_time_vtk = time.time()
        self.arrX.Reset()
        self.arrY.Reset()
        
        for i in range(len(self.hist)):
            self.arrX.InsertNextValue(self.bin_edges[i])
            self.arrY.InsertNextValue(self.hist[i])
        
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
            print("Data converted to Dask array")
        else:
            dask_data = dask_data
        
        if self.data_min is None or self.data_max is None:
            self.data_min, self.data_max = self.compute_min_and_max_values_using_dask(dask_data)
            print("Data min and max computed")
            print("Data min: ", self.data_min)
            print("Data max: ", self.data_max)
        
        start_time_to_calculate_histogram = time.time()
        
        dask_hist = dh.factory(dask_data, axes=(bh.axis.Regular(bins, self.data_min, self.data_max),))
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
    # Set up the UI layout
    # ---------------------------------------------------------------------------------------------

    def setup_layout(self) -> None:
        """Set up the UI layout using Vuetify components."""
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
            with layout.content:
                with vuetify.VContainer(
                    fluid=True,
                    classes="pa-0 fill-height", 
                ):
                    self.client_view = vtk.VtkRemoteView(
                        self.renderWindow,
                        trame_server=self.server, 
                        ref="view"
                    )
    
if __name__ == "__main__":
    histogram_app= HistogramApp()
    histogram_app.server.start(auth_key="key")