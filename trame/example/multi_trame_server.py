# For multi-server management, also for system management 
import os
import sys
import argparse

# For multi-server management
import asyncio
import subprocess
import signal
import threading

# For debugging
import inspect
import traceback

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

# For reading CSV files
import tempfile

# For benchmarking purposes
import time

# Base class for the histogram application
from abc import abstractmethod

## ================================================================= ## 
## Visualization service. Histogramming sub service. The base class. ##         
## ================================================================= ##

@TrameApp()
class BaseHistogramApp:

    # ---------------------------------------------------------------------------------------------
    # Constructor for the BaseHistogramApp class.
    # --------------------------------------------------------------------------------------------- 
       
    def __init__(self, name, port, np_data=None): 
        '''
        Note to self: Write the docstring for the constructor later.

        Signed off by: Huy Nguyen

        Signed off at: Sep 23, 9:42 PM, 2024
        '''

        '''
        The initialization of the BaseHistogramApp class server (trame server).
        Some important notes:
        - The client_type is set to "vue2" for the Vue.js version 2.
        - Chose Vue.js version 2 because it is easier to work with.
        - Vue.js version 3 is supported by Trame. To use it, set the client_type to "vue3".
        - The syntax for Vue.js version 3 is different from version 2.
        - If any derived class changes the client_type, it is the responsibility of the derived class to change the layout and UI accordingly.

        We are also creating an attribute/instance variable called port to store the port number.
        It is then assigned to the port parameter passed to the constructor.
        '''
        self.server = get_server(name, client_type="vue2")
        self.port = port

        '''
        The np_data attribute/instance variable is used to store the data that will be used to generate the histogram.
        Some important notes:
        - If the np_data parameter is not None, then the data is set to the value of the np_data parameter.
        - By default, the parameter is set to None/the argument given is None.
        - By default, the data is set to a random normal distribution with 1,000 data points.
        - The reason why we set it to 1,000 data points is to make it easier to work with (debugging and testing).
        - The other reason is it is not visible during the init rendering of the histogram. Illustrating an empty histogram. 
        '''
        self.np_data = np_data if np_data is not None else np.random.normal(size=1_000)

        '''
        The dask_data attribute/instance variable is used to store the dask array that will be used to generate the histogram.
        Some important notes:
        - By default, the dask array is set to an empty array with a shape of (0,).
        - This is the underlying data structure that will be used to generate the histogram.
        - The call stack (big picture) is as follows: User data -> NumPy Array -> dask array -> dask histogram -> NumPy array -> VTK.
        '''
        self.dask_data = da.empty(shape=(0,))
        
        '''
        These are essential attributes/instance variables that will be used to store the histogram data.
        '''
        self.server.state.bins = 5 
        self.server.state.file_input = None
        self.server.state.selected_column = None
        self.server.state.column_options = [] 
        
        '''
        These are attributes/instance variables that is used to debug the class.
        They can be commented out or removed in the final version.
        But they are useful for debugging and testing purposes.
        '''
        # self.dask_method_invoked = 0
        # self.numpy_method_invoked = 0
        
        '''
        These are essential attributes/instance variables to increase performance.
        They are cache attributes/instance variables.

        Some important notes (data_min and data_max):
        - The data_min and data_max are set to None by default. This is because we do not know the minimum and maximum values of the data.
        - The data_min and data_max attributes/instance variables are managed and manipulated by the state change handlers.
        - No other method should change the data_min and data_max attributes/instance variables.

        Some important notes (data_changed):
        - The data_changed attribute/instance variable is set to True by default.
        - Methods that change the manipulate data and or underlying data should set the data_changed attribute/instance variable to False.
        - These methods are usually methods that convert data from one data structure to another (e.g., NumPy array to dask array).
        - Methods that actually change the data itself should set the data_changed attribute/instance variable to True.
        - Primarily only state change handlers should set the data_changed attribute/instance variable to True.

        Some important notes (hist_cache):
        - The hist_cache attribute/instance variable is used to store the histogram data.
        - The key is a tuple of (bins, data_min, data_max).
        - Beware of the size of the hist_cache attribute/instance variable. It can grow very large depending on the data.
        '''
        self.data_min = None
        self.data_max = None
        self.data_changed = True
        self.hist_cache = {}
        
        '''
        The initial setup of the histogram application.
        Some important notes:
        - The histogram_vtk method is invoked to define the renderer to the server. 
        - It initializes all the necessary VTK objects/attributes/instance variables and sets up the renderer.
        - The data that is rendered is determined by the np_data attribute/instance variable.
        '''
        self.histogram_vtk() 

        '''
        An instance of the VTKRemoteView class is created and assigned to the client_view attribute/instance variable.
        Some important notes:
        - An instance of the VTKRemoteView class is created and assigned to the client_view attribute/instance variable.
        - The instance of VTKRemoteView is given/passed the renderWindow attribute/instance variable initialized in the histogram_vtk method.
        - The instance of VTKRemoteView is given/passed the server attribute/instance variable initialized in the constructor.
        - The instance of VTKRemoteView is given/passed the "view" identifier. This allows the server to interact with the client. 
        - You do not need to worry about the understanding ref parameter, it is not required. It is only used by the server under the hood.
        '''
        self.client_view = vtk.VtkRemoteView(
            self.renderWindow, trame_server=self.server, ref="view"
        )

        '''
        The setup_layout method is invoked to define the layout of the user interface.
        Without this method, the user interface will not be rendered.
        Some important notes:
        - The setup_layout is primarily used to define the layout of the user interface.
        - You can ignore using the setup_layout method if you are not interested in the user interface, and want to write your own custom layout/client.
        - By using the setup_layout method, there is no need to write any JavaScript code. Everything is handled by trame and the server under the hood.
        - If you are knowledgeable in JavaScript and want more control over the client, you can write your own custom UI/layout/client.
        - If you lack knowledge in JavaScript and want to focus on the server-side, you can use the setup_layout method.
        '''
        self.setup_layout()
    
    # ---------------------------------------------------------------------------------------------
    # Method using VTK to define histogram from data and render it
    # ---------------------------------------------------------------------------------------------
    
    def histogram_vtk(self):      
        '''
        Note to self: Write the docstring for the histogram_vtk method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 23, 9:43 PM, 2024
        ''' 

        '''
        Invoke the compute_histogram_data_with_dask method to compute the histogram data.
        Pass the arguments self.np_data and self.server.state.bins to the compute_histogram_data_with_dask.
        Computation of data is required before rendering the histogram.
        It is up to your discretion on how to compute the data and the implementation of such method(s).
        Some important notes:
        - It is important to remember the call stack of the histogram application.
        - The call stack (big picture) is as follows: Computation -> Rendering -> Client.
        ''' 
        self.compute_histogram_data_with_dask(self.np_data, self.server.state.bins)

        '''
        Initialize the vtkTable object and assign it to the table attribute/instance variable.
        This is required. 
        Some important notes:
        - If you are overriding the histogram_vtk method, this initialization is one of the first steps.
        - It is also required to display a histogram (1d/tabular) using VTK.
        '''
        self.table = standard_vtk.vtkTable()
        
        '''
        Initialize the vtkFloatArray objects and assign it to the arrX attributes/instance variables.
        This is required, but the data type of the arrays can be changed and the name of the arrays can be changed.
        Some important notes:
        - There are different types of arrays in VTK. In this case, we are using vtkFloatArray. I would recommend using this data type array since the computations generally return float values.
        - The arrX attribute/instance variable is used to store the X-axis (bin edges) data.
        - The arrY attribute/instance variable is used to store the Y-axis (counts) data.
        - We set the name of the arrays to "X Axis" and "Frequency" respectively, this is up to your discretion.
        '''
        self.arrX = standard_vtk.vtkFloatArray()
        self.arrX.SetName("X Axis")
        self.arrY = standard_vtk.vtkFloatArray()
        self.arrY.SetName("Frequency")

        '''
        A for loop is used to iterate through the histogram data after it has been computed by the compute_histogram_data_with_dask method.
        Insertion of the values into the data type array is required. 
        How the data is inserted is up to your discretion.
        Some important notes:
        - This can be further optimized, since this is a simple and a base class implementation.
        - Some ways to optimize this is to just write this loop using a compiled language (e.g., C++) or using some extension.
        '''
        for i in range(len(self.hist)):
            self.arrX.InsertNextValue(self.bin_edges[i])
            self.arrY.InsertNextValue(self.hist[i])

        '''
        We add the values computed from the histogram data to the vtkTable object.
        This is required.
        Some important notes:
        - The order of addition of the arrays to the column matters.
        - The table is a FIFO (first-in, first-out) data structure.
        '''
        self.table.AddColumn(self.arrX)
        self.table.AddColumn(self.arrY)

        '''
        We need to initialize the vtkPlotBar object and assign it to the plot attribute/instance variable.
        We then add the columns of data (FIFO) to the plot object.
        Some important notes:
        - vtkPlotBar is not natively used to draw histograms.
        - The official VTK documentation says that vtkPlotBar is used draw an XY plot given two columns from a vtkTable.
        - There are many types of XY plots that can be drawn using the vtkPlotBar class (e.g., bar, line, scatter, etc.).
        - Officially VTK does not support continuous bar plots. This is a limitation of VTK.
        - As a workaround we can use the vtkPlotBar class to draw bars and manipulate the bars and renderer to make it continuous.
        - SetInputData is FIFO (first-in, first-out) data structure, so the order of addition matters.
        - We set the color of the bars to black (0, 0, 0, 255) using the SetColor method, but this is up to your discretion.
        - Distorting the bars and renderer to make it continuous does not occur at this stage. This is done later.
        '''    
        self.plot = standard_vtk.vtkPlotBar()
        self.plot.SetInputData(self.table)
        self.plot.SetInputArray(0, "X Axis")
        self.plot.SetInputArray(1, "Frequency")
        self.plot.SetColor(0, 0, 0, 255)

        '''
        This is only use to stylize the histogram bars.
        We do this because continuous bar plots are not natively supported by VTK.
        Even after distorting the bars and renderer and making them continuous, we want someways to distinct the different bars from one another.
        The most clean and simple way to do this is to add an outline to the bars.
        The outline of the bars is set to white (255, 255, 255, 255) using the SetColor method.
        Some important notes:
        - Distorting the bars and renderer to make it continuous does not occur at this stage. This is done later.
        - vtKPen is pretty much only exclusively used to add an outline to 2d shapes/objects (e.g., bars).
        '''
        outline = standard_vtk.vtkPen()
        outline.SetColor(255, 255, 255, 255)
        self.plot.SetPen(outline)
        
        '''
        We initialize the vtkChartXY object and assign it to the chart attribute/instance variable.
        This is required.
        Some important notes:
        - The official VTK documentation says that vtkChartXY class is a factory class is used to draw XY plots.
        - The reason why we use vtkChartXY and vtkPlotBar is because it is IMPOSSIBLE to have the VTK renderer render an vtkPlotBar object directly.
        - We need to add the plot directly to the chart object and have the renderer render the chart object. This is done after this step.
        - We should manipulate the bars and renderer to make the bars continuous. This is done next.
        - We first need to distort the bars and make them continuous. This is done by invoking the SetBarWidthFraction method and setting the value to 1.0. This is REQUIRED to make the bars continuous.
        - Since we have distorted the bars and made them continuous, the renderer SHOULD BE be distorted to make so that the visualization is interpretable.
        - We do this by setting the minimum and maximum values of the X-axis to 0 and 7000 respectively. This is up to your discretion but I HIGHLY recommend 0 as the minimum value.
        - We also set the behavior of the X-axis to FIXED. This makes the the visualization interpretable.
        - self.chart.GetAxis(0).SetBehavior(standard_vtk.vtkAxis.FIXED) is not required, it is up to your discretion.
        - Also, you might be wondering why Axis(0) is the Y axis and Axis(1) is the X axis. This is because actually insertion of the plot is done in the reverse order (LIFO).
        '''
        self.chart = standard_vtk.vtkChartXY()
        self.chart.SetBarWidthFraction(1.0)
        self.chart.GetAxis(0).SetTitle("Frequency")
        self.chart.GetAxis(1).SetTitle("Feature")
        # self.chart.GetAxis(0).SetBehavior(standard_vtk.vtkAxis.FIXED) 
        self.chart.GetAxis(1).SetMinimum(0)
        self.chart.GetAxis(1).SetMaximum(7000)
        self.chart.GetAxis(1).SetBehavior(standard_vtk.vtkAxis.FIXED)

        '''
        After manipulating the bars and renderer to make the bars continuous, we add the plot to the chart object.
        This is required.
        Some important notes:
        - The insertion of the bars to the chart object is done in a LIFO (last-in, first-out) manner.
        - As mentioned earlier, the type of plot can vary depending on the data and the implementation. 
          But the AddPlot method is not only limited to adding vtkPlotBar objects.
        '''
        self.chart.AddPlot(self.plot)
        
        '''
        We initialize the vtkContextView object and assign it to the view attribute/instance variable.
        This is what is the plot is being rendered on.
        We add the chart object (containing the plot) to the scene of the view object.
        This is required. Without it, we cannot render the histogram.
        '''
        self.view = standard_vtk.vtkContextView()
        self.view.GetScene().AddItem(self.chart)
        
        '''
        We get the render window from the view object and assign it to the renderWindow attribute/instance variable.
        We set the size of the render window to 800 x 600. This is up to your discretion.
        This is required.
        Some important notes:
        - This is passed as the first argument to the VTKRemoteView class.
        - The size of the render window does not actually affect the renderer on the client side. 
          The size only matters if looking at the renderer on the server side with a GUI (non-headless).
        '''
        self.renderWindow = self.view.GetRenderWindow()
        self.view.GetRenderWindow().SetSize(800, 600)
    
    # ---------------------------------------------------------------------------------------------
    # Method using VTK to update histogram and render it on the server-side
    # ---------------------------------------------------------------------------------------------
    
    def update_histogram(self, bins):
        '''
        Note to self: Write the docstring for the update_histogram method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 23, 11:21 PM, 2024
        ''' 

        # Used for benchmarking purposes, is commented out.
        # start_time_to_update_histogram = time.time() 
        
        '''
        The argument given to the bins parameter should be an integer already (since it is a number of bins).
        But we need to make sure that the bins is an integer, since bins can be have a decimal value.
        This is not required, but it is recommended to catch any potential errors.
        '''
        bins = int(bins)

        # Debugging statements, are commented out.
        # print("Type of self.np_data: ", type(self.np_data))
        # print("Number of data: ", len(self.np_data))
        # print("Bins: ", bins)
        # print("Data min: ", self.data_min)
        # print("Data max: ", self.data_max)
        # print("Size of data: ", self.np_data.size * self.np_data.itemsize)
        # print("self.hist", self.hist)
        # print("self.bin_edges", self.bin_edges)
        

        '''
        If the data has changed, we need to convert the NumPy array data structure to a dask array data structure.
        Some important notes:
        - In the current implementation, dask is auto chunking the data. This is up to your discretion.
        - Be aware that dask auto chunking is not the most optimal way to chunk the data.
        - We also need to set the data_changed attribute/instance variable to False.
        '''
        if self.data_changed:
            self.dask_data = da.from_array(self.np_data, chunks='auto')
            self.data_changed = False

        # Used for debugging purposes, is commented out.
        # print(f"Updating histogram with number of bins:", bins, "and count of data:", len(self.dask_data))

        '''
        Invoke the compute_histogram_data_with_dask method to compute the histogram data.
        Pass the arguments self.dask_data and bins (local variable) to the compute_histogram_data_with_dask.
        Computation of data is required before rendering the histogram.
        It is up to your discretion on how to compute the data and the implementation of such method(s).
        Some important notes:
        - It is important to remember the call stack of the histogram application.
        - The call stack (big picture) is as follows: Computation -> Rendering -> Client.
        - The arguments passed to the compute_histogram_data_with_dask method are the dask array are different than in the constructor.
        - The compute_histogram_data_with_dask method will convert a NumPy array data structure to a dask array data structure.
          However, it is best to pass the dask array data structure since it is easier to work with and we do not want to accidentally change the underlying data (np_data attribute/instance variable).
        - We also pass the bins (local variable) to the compute_histogram_data_with_dask method. 
          It is not recommended to pass the bins attribute/instance variable since we do not want to accidentally change the state (self.server.state.bins) of the server.
        ''' 
        self.compute_histogram_data_with_dask(self.dask_data, bins)
        
        # Used for benchmarking purposes, is commented out.
        # start_time_vtk = time.time()

        '''
        We need to reset the arrays (arrX and arrY) to insert new values.
        This is required.
        '''
        self.arrX.Reset()
        self.arrY.Reset()

        # Used for debugging purposes, is commented out.
        # print("Self.bin_edges: ", self.bin_edges)
        # print("Self.hist: ", self.hist) 

        '''
        A for loop is used to iterate through the histogram data after it has been computed by the compute_histogram_data_with_dask method.
        Insertion of the values into the data type array is required. 
        How the data is inserted is up to your discretion.
        Some important notes:
        - This can be further optimized, since this is a simple and a base class implementation.
        - Some ways to optimize this is to just write this loop using a compiled language (e.g., C++) or using some extension.
        '''
        for i in range(len(self.hist)):
            # print("Bin edge: ", self.bin_edges[i])
            # print("Frequency: ", self.hist[i])
            # print(f"Bin edge: {self.bin_edges[i]} - Frequency: {self.hist[i]}")
            self.arrX.InsertNextValue(self.bin_edges[i])
            self.arrY.InsertNextValue(self.hist[i])

        '''
        We need to force push the update to the client view.
        Regardless of custom UI/layout/client or the default UI/layout/client, we need to update the client view.
        This is required.
        '''
        self.update_the_client_view()

        # Benchmarking statements, is commented out.
        # end_time_vtk = time.time()
        # end_time_to_update_histogram = time.time()
        # print(f"VTK rendering took {end_time_vtk - start_time_vtk} seconds")
        # print(f"Updating the histogram, after all computations and rendering, took {end_time_to_update_histogram - start_time_to_update_histogram} seconds")
        
    # ---------------------------------------------------------------------------------------------
    # Method to update the render window to the client-side
    # ---------------------------------------------------------------------------------------------
    
    def update_the_client_view(self):
        '''
        Note to self: Write the docstring for the update_the_client_view method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 23, 11:23 PM, 2024
        '''

        '''
        The .update method is used to update the client view.
        Without this update method, the client view will not be updated.
        This is required most of the time, required for this implementation.
        Some important notes:
        - The only time this is not required is perhaps when you are writing the application functionally.
        - For class based implementations, this is required.
        - For custom UI/layout/client, this is required.
        '''
        self.client_view.update()

        # Used for debugging purposes, is commented out.   
        # print("The client view has been updated") 

    # ---------------------------------------------------------------------------------------------
    # Method using dask to compute histogram data
    # ---------------------------------------------------------------------------------------------
    
    def compute_histogram_data_with_dask(self, dask_data, bins):
        '''
        Note to self: Write the docstring for the compute_histogram_data_with_dask method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 23, 11:23 PM, 2024
        '''

        # Used for benchmarking purposes and debugging purposes, is commented out.
        # computation_type = "dask (threaded scheduler)"
        
        '''
        Since the implementation of the this method requires us to use dask arrays, we need to make sure that the data is a dask array.
        This is not required, but it is recommended to catch any potential errors.
        Some important notes:
        - In the current implementation, dask is auto chunking the data. This is up to your discretion.
        - Be aware that dask auto chunking is not the most optimal way to chunk the data.
        - It is not recommended to set the data_changed attribute/instance variable to False, 
          since the argument passed to this method is could be something different than what you expect.
        '''
        if not isinstance(dask_data, da.Array):
            dask_data = da.from_array(dask_data, chunks='auto')
        else:
            dask_data = dask_data
        
        '''
        We need to compute the minimum and maximum values of the data.
        This is not required, but it is recommended.
        '''
        if self.data_min is None or self.data_max is None:
            # Used for debugging purposes, is commented out.
            # print("Detected that data_min and data_max are None")

            self.data_min, self.data_max = self.compute_min_and_max_values_using_dask(dask_data)
        
        # Used for benchmarking purposes, is commented out.
        # start_time_to_calculate_histogram = time.time()

        '''
        We want to cache the histogram data to increase performance.
        If this key is in the cache, we retrieve the histogram data from the cache.
        The key is a tuple of (bins, data_min, data_max).
        '''
        key = (bins, self.data_min, self.data_max)

        '''
        If the key is in the hist_cache attribute/instance variable, we retrieve the histogram data from the cache.
        This is not required, but it is recommended since it increases performance.
        If it is not in the cache, we compute the histogram data.
        Some important notes:
        - We compute the bin_edges using the native dask method histogram, da.histogram.
          We do this because da.histogram returns the bin_edges as a NumPy array already, saving us the trouble of converting from a dask array to a NumPy array.
        - For an increase in performance (explained in "Results of implementation"), we are using the dask-histogram library to compute the histogram counts.
        - Since using dask-histogram returns an aggregated histogram, which is a dask collection (type), we need to convert it to a NumPy array.
        - We convert the aggregated histogram to a NumPy array using the convert_agghistogram_to_numpy_array_of_frequencies method.
        - We finally cache the data (self.hist and self.bin_edges) in the hist_cache attribute/instance variable after computing the data, so that we do not have to recompute the data in the future.

        Results of implementation :
        - We are able to achieve results and performance equivalent to the best papers in the field of high performance histogramming computing.
        - We recommend using the dask-histogram and/or using the boost_histogram for high performance histogramming computing.
        - Since we are using a combination of dask and boost_histogram, we are able to achieve high performance and scalability.
        '''
        if key in self.hist_cache:
            # Used for benchmarking purposes, is commented out.
            # start_time_to_retrieve = time.time() 

            self.hist, self.bin_edges = self.hist_cache[key]

            # Used for benchmarking purposes, is commented out.
            # end_time_to_retrieve = time.time()
            # print(f"Retrieving the cached result took {end_time_to_retrieve - start_time_to_retrieve} seconds")
        else:
            dask_hist = dh.factory(dask_data, axes=(bh.axis.Regular(bins, self.data_min, self.data_max+1),))
            dask_hist = dask_hist.persist() 
            hist_result = self.convert_agghistogram_to_numpy_array_of_frequencies(dask_hist)

            '''
            This is an alternative method to compute the histogram using dask distributed, recommended for clusters or large data sets.
            For cluster, it will require customization and custom implementation.
            And it is not so easy to implement.Which is why it is commented out. Since this current implementation is for a single machine.
            '''
            # hist_result = self.convert_agghistogram_to_numpy_array_of_frequencies_distributed(dask_hist)

            self.hist = hist_result
            _, self.bin_edges = da.histogram(dask_data, bins=bins, range=(self.data_min, self.data_max))

            self.hist_cache[key] = (self.hist, self.bin_edges)
        
        # Used for benchmarking purposes, is commented out.
        # end_time_to_calculate_histogram = time.time()

        '''
        This make sure that self.hist is a NumPy array and not a dask array. 
        This is only for insurance if for some reason the self.hist is a dask array.
        It does this by invoking the convert_dask_to_numpy method, which turns ANY dask collection (type) to the equivalent in-memory type (e.g., NumPy array).
        This is not required, but it is recommended to catch any potential errors.
        '''
        if not isinstance(self.hist, np.ndarray):
            self.hist = self.convert_dask_to_numpy(self.hist)

        # Used for benchmarking purposes, is commented out.
        # print(f"Calculating the histogram using {computation_type} took {end_time_to_calculate_histogram - start_time_to_calculate_histogram} seconds")

    # ---------------------------------------------------------------------------------------------
    # Method using dask compute method to convert AggHistogram to a NumPy array of frequencies
    # ---------------------------------------------------------------------------------------------

    def convert_agghistogram_to_numpy_array_of_frequencies(self, dask_object):
        '''
        Note to self: Write the docstring for the convert_agghistogram_to_numpy_array_of_frequencies method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 24, 12:00 AM, 2024
        '''

        '''
        We need to make the dask object, which should be an AggHistogram, a dask collection (type), is converted into a tuple NumPy arrays (it's in-memory equivalent).
        Also, after converting the AggHistogram to a NumPy array, it actually returns a tuple of NumPy arrays, the first index is the frequencies and the second index is the bin edges.
        We only need the frequencies, so we only return the first NumPy array.
        This is required.
        Some important notes:
        - The memory equivalent of AggHistogram, a dask collection (type) is a tuple of NumPy arrays.
        - The first index of the tuple is the frequencies and the second index is the bin edges.
        - We only need the frequencies, so we only return the first NumPy array.
        - We are using a threaded scheduler (single-machine scheduler), but for large data sets, we recommend using the distributed scheduler, 
        - We are also using 21 workers, but this is up to your discretion.
        '''
        result = dask_object.compute(scheduler='threads', num_workers=21) 
        frequencies = result.to_numpy()[0]
        return frequencies

    # ---------------------------------------------------------------------------------------------
    # Method using dask distributed to convert AggHistogram to a NumPy array of frequencies
    # ---------------------------------------------------------------------------------------------

    def convert_agghistogram_to_numpy_array_of_frequencies_distributed(self, dask_object):
        '''
        Note to self: Write the docstring for the convert_agghistogram_to_numpy_array_of_frequencies_distributed method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 24, 12:20 AM, 2024
        '''

        '''
        We need to make the dask object, which should be an AggHistogram, a dask collection (type), is converted into a tuple NumPy arrays (it's in-memory equivalent).
        Also, after converting the AggHistogram to a NumPy array, it actually returns a tuple of NumPy arrays, the first index is the frequencies and the second index is the bin edges.
        We only need the frequencies, so we only return the first NumPy array.
        This is required.
        Some important notes:
        - The memory equivalent of AggHistogram, a dask collection (type) is a tuple of NumPy arrays.
        - The first index of the tuple is the frequencies and the second index is the bin edges.
        - We only need the frequencies, so we only return the first NumPy array. 
        - This is using a client object, which is a dask distributed client object, for distributed computing (local).
        - Under the hood, when the client uses the compute method, it uses the multiprocessing scheduler.
        - To make it use a threaded scheduler, you need to pass the "processes=False" argument to the Client -> Client(processes=False).
        - It is much more complex to use a distributed scheduler across a cluster, but it is possible, you will have to research and implement it since it is not covered in this implementation.
        '''
        client = Client()
        dask_hist = client.compute(dask_object)
        frequencies = dask_hist.result().to_numpy()[0]
        return frequencies

    # ---------------------------------------------------------------------------------------------
    # Method using dask compute method to convert dask object to NumPy array
    # ---------------------------------------------------------------------------------------------

    def convert_dask_to_numpy(self, dask_object):
        '''
        Note to self: Write the docstring and description for the convert_dask_to_numpy method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 24, 12:08 AM, 2024
        '''

        '''
        We need to make ANY dask collection (type) and turn it into it's in-memory equivalent.
        This is not required, but it is recommended to catch any potential errors.
        Some important notes:
        - We are using the threaded scheduler, but for large data sets, we recommend using the distributed scheduler.
        - We are also using 21 workers, but this is up to your discretion.
        '''
        result = dask_object.compute(scheduler='threads', num_workers=21) 
        return result
        
    # ---------------------------------------------------------------------------------------------
    # Method using dask compute method with the scheduler argument passed as 'threads'
    # ---------------------------------------------------------------------------------------------
    
    def compute_with_threads(self, dask_object):
        '''
        Note to self: Write the docstring for the compute_with_threads method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 24, 12:20 AM, 2024
        '''

        '''
        The compute_with_threads method is used to convert a dask dataframe, to a dask array, to a NumPy array.
        Specifically to be used to convert a dask dataframe to the NumPy array data structure.
        It will likely throw an error if the dask object is not a dask dataframe since we are using the .values method from the dask library, which is exclusive to dask dataframes.
        This is required. But the implementation is up to your discretion.
        Some important notes:
        - We are using the threaded scheduler, but for large data sets, we recommend using the distributed scheduler.
        - Stack call is as follows: dask dataframe -> dask array -> NumPy array.
        '''
        return dask_object.values.compute(scheduler='threads')
    
    # ---------------------------------------------------------------------------------------------
    # Method using dask to read a comma-separated values (csv) file into a dask DataFrame
    # ---------------------------------------------------------------------------------------------
    
    def dask_read_csv(self, content):
        '''
        Note to self: Write the docstring for the dask_read_csv method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 24, 12:36 AM, 2024
        '''

        '''
        We need to write the content of the file to a temporary file.
        This is not required, but is one of the many ways to read a csv file using dask.
        You could possibly directly use dask to read the content of the file, but this is up to your discretion.
        This is only just a suggestion, and not required, but I would recommend it since it catches any potential errors.
        Some important notes:
        - IF you are writing your own custom UI/layout/client, you will need to write your own method to read the content of the file.
          I would recommend using a temporary file, but this is up to your discretion.
        - We also do deliberately do not delete the temporary file, 
          since we want to make sure that the file is deleted after all the method which requires the use of the temporary file is done.
          We will delete it after the last method that requires the use of the temporary file is done.
          And since we are not deleting it, we need a path to the temporary file so we can delete it later, which is why we return the path.
        - This is also not optimized at all, but it is a simple and a base class implementation.
        '''
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            '''
            Required for BytesIO, which is usually used for custom UI/layout/client.
            It is up to your discretion on how to read the content of the file.
            But I would recommend just commenting out the code below and using it directly since it is easy to work with and I know it works.
            I am unsure about other implementations. But there are probably different and more efficient ways to read the content of the file if you are not using the default UI/layout/client.
            '''
            # temp_file.write(content.getvalue())

            temp_file.write(content)
            temp_path=temp_file.name
        
        dask_df = dd.read_csv(temp_path)
        
        return dask_df, temp_path
    
    # ---------------------------------------------------------------------------------------------
    # Method using dask to calculate the minimum and maximum values of data
    # ---------------------------------------------------------------------------------------------
    
    def compute_min_and_max_values_using_dask(self, dask_data):
        '''
        Note to self: Write the docstring for the compute_min_and_max_values_using_dask method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 24, 12:36 AM, 2024
        '''

        '''
        This make sure that the argument given to the dask_data parameter is a dask array and not a dask array. 
        This is only for insurance if for some reason the dask array is not a dask array.
        It does this by invoking dask.array from_array method, which turns ANY array-like object (including NumPy) to a dask array.
        This is not required, but it is recommended to catch any potential errors.
        Some important notes:
        - In the current implementation, dask is auto chunking the data. This is up to your discretion.
        - Be aware that dask auto chunking is not the most optimal way to chunk the data.
        '''
        if not isinstance(dask_data, da.Array):

            # Is used for benchmarking purposes, is commented out.
            # print("Changing the data to dask data")
            # start_time_to_change_data_to_dask_data = time.time()

            dask_data = da.from_array(dask_data, chunks='auto')

            # Is used for benchmarking purposes, is commented out.
            # end_time_to_change_data_to_dask_data = time.time()
            # print(f"Changing the data to dask data during min and max took {end_time_to_change_data_to_dask_data - start_time_to_change_data_to_dask_data} seconds")
        else:
            dask_data = dask_data
        
        '''
        We need to compute the minimum and maximum values of the data.
        We then need to convert the dask array to a NumPy array.
        This is required, if you are using dask to compute the histogram data since dask will explicitly ask for the minimum and maximum values.
        This is not required, if you are using NumPy to compute the histogram data, since NumPy under the hood will compute the minimum and maximum values if not given.
        Some important notes:
        - Under the hood, when .compute() is invoked, it uses the threaded scheduler by default.
        - For large data sets, we recommend using the distributed scheduler.
        '''
        data_min = dask_data.min().compute()
        data_max = dask_data.max().compute()
        
        # print("Invoked method: compute_min_and_max_values_using_dask")
        # print("Method output - Min: ", data_min)
        # print("Method output - Max: ", data_max)
        # self.dask_method_invoked += 1
    
        # print("The number of times the compute_min_and_max_values_using_dask method has been been called: ", self.dask_method_invoked)
        
        return data_min, data_max
    
    # ---------------------------------------------------------------------------------------------
    # State change handler for bins
    # ---------------------------------------------------------------------------------------------
    
    @change("bins")
    def on_bins_change(self, bins, **trame_scripts):
        '''
        Note to self: Write the docstring for the on_bins_change method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 24, 1:53 AM, 2024
        '''

        '''
        We are using a decorator to handle the state change of the bins attribute/instance variable.
        When the bins attribute/instance variable changes, we need to update the histogram.
        We do this by invoking the update_histogram method and passing the bins attribute/instance variable to the update_histogram method.
        Some important notes:
        - This class is currently using the decorator from the trame.decorators library to handle the state changes.
        - There is another way to handle the state changes, which is slightly more complicated.
          This would involve assigning the state of the server to `self.state` and then applying the `change("___")` decorator 
          from `self.state` to the `self.___` method.
          Such as:
          -> self.state = self.server.state
          -> self.state.change("bins")(self.on_bins_change)
        '''
        self.update_histogram(bins)

    # ---------------------------------------------------------------------------------------------
    # State change handler for file_input
    # ---------------------------------------------------------------------------------------------
    
    @change("file_input")
    def on_file_input_change(self, file_input, **trame_scripts):
        '''
        Note to self: Write the docstring for the on_file_input_change method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 24, 1:53 AM, 2024
        '''
        if file_input:
            '''
            We need to reset the minimum and maximum values of the data.
            We need to set the data_changed attribute/instance variable to True.
            This is required if you are using these attributes/instance variables in the update_histogram method and or other methods to compute the histogram data.
            '''
            self.data_min = None
            self.data_min = None
            self.data_changed = True
            try:
                '''
                If you are using a custom UI/layout/client, you will need to write your own method to read the content of the file.
                I would suggest uncommenting out the code below and using it directly since it is easy to work with and I know it works.
                I am unsure about other implementations. 
                But I know that my custom UI/layout/client needed to encode the content of the file and then I had to decode it on the server side, using BytesIO to wrap the content.
                However, there are probably different implementation, this is only a suggestion and not required.
                '''
                # content = BytesIO(base64.b64decode(file_input['content']))

                '''
                From the file_input dictionary, we extract the content of the file using the key 'content'.
                We assign the content of the file to the content variable.
                We then read the content of the file using the dask_read_csv method.
                This is not required, but heavily recommended.
                Some important notes:
                - dask_read_csv could be further optimized, since this is a simple and a base class implementation.
                - There are likely many different ways to receive the content of the file, but this is only a suggestion and not required.
                - This would definitely need to be changed if you are using a custom UI/layout/client, something like above would be required.
                '''
                content = file_input['content']
                dask_df, temp_path = self.dask_read_csv(content)
                
                '''
                After reading the content of the file, we need to set the column_options attribute/instance variable to the columns of the dask dataframe.
                We then invoke the on_column_options_change method and pass the column_options attribute/instance variable to the on_column_options_change method.
                We then access the first column of the dask dataframe and assign it to the selected_column attribute/instance variable.
                This is not required, but heavily recommended.
                Some important notes:
                - self.on_column_options_change seems pretty redundant, the since on_column_options_change method is already a state change handler.
                  But out of precaution, we invoke the on_column_options_change method in unforeseen events such as server does not detect the state change or for some other reason.
                  Basically, this is just out of precaution and paranoia.
                - Also we choose the first column of the dask dataframe, but you could choose any column you want, this is up to your discretion.
                '''
                self.server.state.column_options = dask_df.columns.tolist()
                self.on_column_options_change(self.server.state.column_options)
                self.server.state.selected_column = self.server.state.column_options[0] 

                '''
                Since the we have selected the column, we need to get the data of the selected column.
                And since this implementation works with dask arrays, we need to convert the dask dataframe to the equivalent NumPy array data structure.
                Some important notes:
                - compute_with_threads is only used to convert a dask dataframe to the equivalent dask array data structure in memory, a NumPy array.
                  It is not meant to be used for any other conversion of a dask collection (type) to a different in memory data structure.
                - compute_with_threads is not optimized at all, but it is a simple and a base class implementation.
                '''
                selected_column_data = dask_df[self.server.state.selected_column] 
                selected_column_data = self.compute_with_threads(selected_column_data)

                '''
                Since selected_column_data is now a NumPy array, we assign it to the np_data attribute/instance variable.
                This represents the data has been changed.
                This is required.
                Some important notes:
                - This is one of the very few methods that should be able to directly access the np_data attribute/instance variable.
                - This is required, since the data has changed and we need to update the histogram, and without this, the histogram will not be updated with the new data.
                - It might be possible to directly avoid converting the dask dataframe to a dask array and then to a NumPy array, and keeping it as a dask array, and then assigning it to the dask_data attribute/instance variable.
                  But this is up to your discretion and I have not tested this. If it does work, it would be more optimal.
                '''
                self.np_data = selected_column_data
                
                '''
                Finally, since we have the new data, we no longer need the temporary file.
                We get the path of the temporary file and check if it exists.
                If it does, we remove the temporary file.
                '''
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
                else:
                    pass

                '''
                We then invoke the update histogram method and pass the bins attribute/instance variable to the update_histogram method.
                This is required.
                Some important notes:
                - We do this because the data has changed and we need to update the histogram.
                - And the bins does not necessarily have to change, but we need to update the histogram anyway, 
                  so we cannot rely on the state change handler for the bins attribute/instance variable to update the histogram.
                - The update needs to be immediate as long as the data has changed.
                '''
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
        '''
        Note to self: Write the docstring for the on_column_options_change method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 24, 2:32 AM, 2024
        '''

        '''
        Get all the columns of the dask dataframe and assign it to the column_options attribute/instance variable.
        This should be invoked by the server whenever the column_options attribute/instance variable changes.
        '''
        self.server.state.column_options = column_options
    
    # ---------------------------------------------------------------------------------------------
    # State change handler for selected_column
    # ---------------------------------------------------------------------------------------------
    
    @change("selected_column")
    def on_selected_column_change(self, selected_column, **trame_scripts):
        '''
        Note to self: Write the docstring for the on_file_input_change method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 24, 2:56 AM, 2024
        '''

        '''
        We need to reset the minimum and maximum values of the data.
        We need to set the data_changed attribute/instance variable to True.
        This is required if you are using these attributes/instance variables in the update_histogram method and or other methods to compute the histogram data.
        '''
        self.data_min = None
        self.data_max = None
        self.data_changed = True
        if self.server.state.file_input and self.server.state.selected_column and selected_column:
            try:
                '''
                If you are using a custom UI/layout/client, you will need to write your own method to read the content of the file.
                I would suggest uncommenting out the code below and using it directly since it is easy to work with and I know it works.
                I am unsure about other implementations. 
                But I know that my custom UI/layout/client needed to encode the content of the file and then I had to decode it on the server side, using BytesIO to wrap the content.
                However, there are probably different implementation, this is only a suggestion and not required.
                '''
                # content = base64.b64decode(self.server.state.file_input['content'])
                # df, temp_path = self.dask_read_csv(BytesIO(content))  

                '''
                From the file_input dictionary, we extract the content of the file using the key 'content'.
                We assign the content of the file to the content variable.
                We then read the content of the file using the dask_read_csv method.
                This is not required, but heavily recommended.
                Some important notes:
                - dask_read_csv could be further optimized, since this is a simple and a base class implementation.
                - There are likely many different ways to receive the content of the file, but this is only a suggestion and not required.
                - This would definitely need to be changed if you are using a custom UI/layout/client, something like above would be required.
                '''
                content = self.server.state.file_input['content']
                df, temp_path = self.dask_read_csv(content)

                '''
                We need to make sure that selected_column_data is a NumPy array, therefore we invoke the compute_with_threads method.
                We pass the dask dataframe indexed by the selected_column attribute/instance variable to the compute_with_threads method.
                After the method is invoked, we assign the result to the np_data attribute/instance variable.
                This is required.
                Some important notes:
                - This is one of the very few methods that should be able to directly access the np_data attribute/instance variable.
                - This is required, since the data has changed and we need to update the histogram, and without this, the histogram will not be updated with the new data.
                - It might be possible to directly avoid converting the dask dataframe to a dask array and then to a NumPy array, and keeping it as a dask array, and then assigning it to the dask_data attribute/instance variable.
                  But this is up to your discretion and I have not tested this. If it does work, it would be more optimal.
                '''
                self.np_data = self.compute_with_threads(df[self.server.state.selected_column])

                '''
                We then invoke the update histogram method and pass the bins attribute/instance variable to the update_histogram method.
                This is required.
                Some important notes:
                - We do this because the data has changed and we need to update the histogram.
                - And the bins does not necessarily have to change, but we need to update the histogram anyway, 
                  so we cannot rely on the state change handler for the bins attribute/instance variable to update the histogram.
                - The update needs to be immediate as long as the data has changed.
                '''
                self.update_histogram(self.server.state.bins)

                '''
                Finally, since we have the new data, we no longer need the temporary file.
                We get the path of the temporary file and check if it exists.
                If it does, we remove the temporary file.
                '''
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
        '''
        Note to self: Write the docstring for the setup_layout method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 24, 4:06 AM, 2024
        '''

        '''
        We are using the SinglePageLayout class from the trame.layout library to create the layout.
        This is required if you are not using a custom UI/layout/client.
        We are required to pass the server to the SinglePageLayout class as an argument.
        Some important notes:
        - The SinglePageLayout class is a layout class that is used to create a single page layout.
        - It is not meant to be used to build a multi-page layout, but it is possible, but you will need to research and implement it.
          Since this current implementation is for a single page layout, multi-page layout is not discussed or implemented.
        - If you are using a custom UI/layout/client, you do not need to use the SinglePageLayout class, 
          you will be primarily writing your own custom UI/layout/client using JavaScript, HTML, and CSS.
        - This is a lot easier to use and is recommended if you have little experience with web development.
        '''
        with SinglePageLayout(self.server) as layout:
            '''
            We get the server name and set it as the title of the layout.
            '''
            layout.title.set_text(self.server.name)

            '''
            For the basic layout, we are using the Vuetify library to create the layout.
            We have a toolbar and a content area.
            The toolbar contains the VSpacer, VSlider, VFileInput, and VSelect components.
            Some important notes:
            - The VSpacer component is used to create space between the components.
            - The VSlider component is used to create a slider to select the number of bins.
            - The minimum value of the slider is 1 and the maximum value is 100.
            - The initial value of the slider is 5, to match the initial value of the bins attribute/instance variable.
            - The VFileInput component is used to upload a CSV file and only accepts CSV files.
            - The VSelect component is used to select a column from the dask dataframe.
            '''
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
                vuetify.VFileInput(
                    v_model=("file_input", None),
                    label="Upload CSV File",
                    accept=".csv",
                    style="padding-top: 20px;", 
                )
                vuetify.VSelect(
                    v_model=("selected_column", None),
                    items=("column_options",),
                    label="Select Column",
                    style="padding-top: 20px;", 
                )

            '''
            For the content area, we are using the Vuetify library to create the layout.
            We have a VContainer component that contains the VRemoteView component.
            Some important notes:
            - Use either of the following code solutions to create the VRemoteView component.
            - The VRemoteView component is used to display the histogram. Without it the histogram will not be displayed.
            '''
            with layout.content:
                with vuetify.VContainer(
                    fluid=True,
                    classes="pa-0 fill-height",  
                ):  
                    # Default and recommended code solution to display the render window to the user/client.
                    self.client_view = vtk.VtkRemoteView(
                        self.renderWindow, trame_server=self.server, ref="view"
                    )
                    # Uncomment this and comment the above code solution if for some reason the above code does not work.
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
        '''
        Note to self: Write the docstring for the start_new_server_immediately method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 24, 4:12 AM, 2024
        '''

        # Keeping this uncommented as it allows me to click it, and it'll open the browser.
        # Instead of having to manually go to a browser, open it, and type in the URL.
        print(f"Starting {self.server.name} at http://localhost:{self.port}/index.html")

        '''
        This is meant to be used to start a new server immediately.
        This is a required method that every child/derived class must implement since it is an abstract method.
        Some important notes:
        - Since this is immediate, is is recommended that the server is started in the main thread.
        - By default, the server is started in the main thread.
        - To start the server in the main thread, you need to pass the exec_mode argument as "main".
        - This is more useful for testing, as pretty much every software application is multi-server/multi-user.
        '''
        self.server.start(exec_mode="main", port=self.port)

    # ---------------------------------------------------------------------------------------------
    # Method to start a new server (async). To be used in a multi-process environment
    # ---------------------------------------------------------------------------------------------

    @abstractmethod
    async def start_new_server_async(self):
        '''
        Note to self: Write the docstring for the start_new_server_async method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 24, 4:12 AM, 2024
        '''
        # Keeping this uncommented as it allows me to click it, and it'll open the browser.
        # Instead of having to manually go to a browser, open it, and type in the URL.
        print(f"Starting {self.server.name} at http://localhost:{self.port}/index.html")

        '''
        This is meant to be used to start a new server asynchronously.
        This is a required method that every child/derived class must implement since it is an abstract method.
        Some important notes:
        - Since this is asynchronous, we must use the async keyword.
        - We must also await, and we must use the await keyword.
        - To start the server asynchronously, you need to pass the exec_mode argument as "task".
        - This is recommended to be used in a multi-server/multi-user environment, which is basically every software application.
        '''
        return await self.server.start(exec_mode="task", port=self.port)

    # ---------------------------------------------------------------------------------------------
    # Method to kill a server. Child/derived classes should implement this method
    # ---------------------------------------------------------------------------------------------

    @abstractmethod
    def kill_server(self):
        '''
        Note to self: Write the docstring for the kill_server method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 24, 4:15 AM, 2024
        '''

        # Just a suggestion, not required.
        # print(f"Stopping {self.server.name} at port {self.port}")
        # self.server.stop()

        '''
        This is meant to be used to kill a server.
        All child/derived classes must implement this method since it is an abstract method.
        Some important notes:
        - The parent class/base class is not implementing this method.
        - This is actually not required to be implemented, but it is recommended, which is why it is an abstract method.
        - The reason the parent class/base class is not implementing this method is because it is another class is acting as the server manager.
        '''
        pass

    # ---------------------------------------------------------------------------------------------
    # Method to debug the server: Get the entire stack trace
    # ---------------------------------------------------------------------------------------------

    def trace_calls(self, frame, event, arg):
        '''
        Note to self: Write the docstring for the kill_server method later.

        Signed off by: Huy Nguyen
        
        Signed off at: Sep 24, 4:15 AM, 2024
        '''

        '''
        This is used to get the entire call stack trace.
        We are appending the call stack trace to a file called "logging_stack.txt".
        This is not required, but it is recommended for debugging purposes.
        Some important notes:
        - We are appending the call stack trace to a file called "logging_stack.txt", not writing to it.
        - This means that the file will not be overwritten, but the call stack trace will be appended to the file.
        - The reason for this is because using the write method will overwrite the file, and we want to keep the call stack trace.
        - Also, your IDE/editor might be graying out/ implying that we are not using the "arg" parameter, but it is required or there will be an error.
        '''
        with open('logging_stack.txt', 'a') as f:  
            if event == 'call':
                code = frame.f_code
                function_name = code.co_name
                file_name = code.co_filename
                line_number = frame.f_lineno
                f.write(f"Calling {function_name} in {file_name} at line {line_number}\n")
        
        return self.trace_calls


## ================================================================== ## 
## Visualization service. Server Manager sub service. The base class. ##         
## ================================================================== ##

class ServerManager:

    # ---------------------------------------------------------------------------------------------
    # Constructor for the ServerManager class.
    # --------------------------------------------------------------------------------------------- 

    def __init__(self):
        '''
        Note to self: Write the docstring for the constructor later.

        Signed off by: Huy Nguyen

        Signed off at: Sep 24, 4:29 AM, 2024
        '''

        '''
        The initialization of the ServerManager class server (trame server).
        This is required.
        Some important notes:
        - The client_type is set to "vue2" for the Vue.js version 2.
        - Chose Vue.js version 2 because it is easier to work with.
        - Vue.js version 3 is supported by Trame. To use it, set the client_type to "vue3".
        - The syntax for Vue.js version 3 is different from version 2.
        - If any derived class changes the client_type, it is the responsibility of the derived class to change the layout and UI accordingly.

        We are also initializing the control_state and control_ctrl attributes/instance variables.
        We need to do this because we will be using the control_state and control_ctrl attributes/instance variables to access the state and controller of the server.
        '''
        self.servers_manager = get_server("Server_Manager", client_type="vue2")
        self.control_state, self.control_ctrl = self.servers_manager.state, self.servers_manager.controller

        '''
        The initialization of the servers attribute/instance variable.
        The servers attribute/instance variable is a dictionary that will store the servers.
        The key will be the port number and the value will be the process.

        We are also initializing the next_port attribute/instance variable.
        This is the next port number that will be used to start a new server.
        By default, the first server will be started on port 5456 and for every new server, the port number will be incremented by 1.

        We are also initializing the server_list attribute/instance variable.
        The server_list attribute/instance variable is a list that will store the servers.
        It is required for the UI to display the servers icon and status.
        The initialization of the server_list attribute/instance variable is an empty list.

        You are required to initialize these attributes/instance variables.
        '''
        self.servers = {}
        self.next_port = 5456
        self.control_state.server_list = []

        '''
        We are initializing the level_to_color attribute/instance variable.
        The level_to_color attribute/instance variable is a dictionary that will store the color of the server status.
        The key will be the server status and the value will be the color.
        The color will be used to display the server status in the UI.
        Running servers will be displayed in green and stopped servers will be displayed in red.
        This is not required, but it is recommended for the UI to display the server status.
        '''
        self.control_state.level_to_color = {
        "Running": "green",
        "Stopped": "red"
        }
        
        '''
        We are invoking the trigger method to register the triggers with the controller.
        '''
        self.register_triggers()

        '''
        We are invoking the render_ui_layout method to render the UI layout.
        We need to do this because we need to display the UI layout to the user/client.
        In a custom UI/layout/client, you do not need to invoke this method, since you will be writing your own UI/layout/client.
        This is only required if you are using the default UI/layout/client.
        Some important notes:
        - The render_ui_layout method is required to be invoked to display the UI layout to the user/client if using the default UI/layout/client.
        - The render_ui_layout method is NOT required to be invoked to display the UI layout to the user/client if NOT using the default UI/layout/client.
        - I would suggest if you have some knowledge in web development, to write your own custom UI/layout/client, since it will be a lot cleaner and a lot more customizable.
        - However, for those who do not have any knowledge in web development, I would suggest using the default UI/layout/client.
        - This base class assumes that you do not have any knowledge in web development, and that is why it is using the default UI/layout/client, 
          and this base class will provide you with a simple default UI/layout/client that you can extend and customize if you want.
        '''
        self.render_ui_layout()

    # ---------------------------------------------------------------------------------------------
    # Method to start a different application server
    # ---------------------------------------------------------------------------------------------
    
    def start_new_server(self):
        '''
        Note to self: Write the docstring for the start_new_server method later

        Signed off by: Huy Nguyen

        Signed off at: Sep 24, 4:43 AM, 2024
        '''

        # I find this helpful for debugging purposes, for easy viewing from the terminal.
        # Therefore this is not being commented out. You can comment it out if you want.
        print("Starting new server")

        '''
        The CLI (Command Line Interface) command to start a new server.
        The command is a list of strings.
        The first string is the Python interpreter. It is not recommended to change this string, but you can based on your Python interpreter or how you start your Python interpreter.
        I am aware of using "python3", "python3.12" or specific Python interpreter versions, but I would recommend using "python" since you are likely running this from a virtual environment.

        The second string is the name of the file that contains the server.
        This will change based on the name of the file that contains the server to be started.
        I would always recommend having the classes of the server and the server manager in the same files so you do not need to deal with path issues.

        The third string is the argument/flag to launch the server.
        DO NOT CHANGE THIS STRING. This is required to launch the server.
        The only time you would change this string is if you are changing the name of the argument/flag in the main() (__main__) method that starts the server manager.

        The fourth string is the port number.
        This is the port number that the server will be started on.
        The port number is stored in the next_port attribute/instance variable.
        The next_port attribute/instance variable is incremented by 1 for every new server that is started.

        This is required to start a new server.

        Some important notes:
        - The command is a list of strings.
        - The command is required to start a new server.
        - You might have to deal with path issues if the classes of the server and the server manager are not in the same file.
        - Do NOT the third string, it is required to launch the server, the only exception is if you are changing the name of the argument/flag in the main() (__main__) method that starts the server manager.
        '''
        command = [
            "python",
            "multi_trame_server.py",  
            "--launch_server",
            str(self.next_port)
        ]

        '''
        The subprocess module is used to spawn new processes, connect to their input/output/error pipes, and obtain their return codes.
        We are using the Popen class from the subprocess module to start a new server, using the command.
        The resulting process is stored in a local variable, 'process', and then added to the 'servers' dictionary with the key as 'next_port'.
        This is required to start a new server.
        '''
        process = subprocess.Popen(command)
        self.servers[self.next_port] = process

        # I find this helpful for debugging purposes, for easy viewing from the terminal.
        # Therefore this is not being commented out. You can comment it out if you want.
        print(f"Started new server on port {self.next_port} with PID {process.pid}")

        # Add the new server to the server_list
        '''
        We are appending the new server port to the server_list attribute/instance variable.
        Since we have started it, the status of the server is "Running".
        This is required to update the UI with the new server.
        '''
        self.control_state.server_list.append({
            'port': self.next_port,
            'status': 'Running'
        })

        # I find this helpful for debugging purposes, for easy viewing from the terminal.
        # Therefore this is not being commented out. You can comment it out if you want.
        print(f"Server list after starting new server: {self.control_state.server_list}")

        '''
        Increment the next_port attribute/instance variable by 1.
        Therefore, the next server will be started on the next port number and not the same port number.
        This is required to start a new server.
        '''
        self.next_port += 1
        
        '''
        We inform the UI that the server_list attribute/instance variable "is dirty" (has changed).
        And that it needs to be "cleaned" pushed/updated at the next "flush", the next update.
        This is required to update the UI with the new server.
        '''
        self.control_state.dirty("server_list")

        '''
        We invoke the render_ui_layout method to update and rerender the UI layout.
        This will allow the UI to update the server_list with the new server list.
        This is required to update the UI with the new server.
        Some important notes:
        - This is important because natively the layout is static, we need to rerender the layout to update the UI.
        - This is also important for the JavaScript to update the UI, since the JavaScript is not aware of the server_list attribute/instance variable.
        - It only becomes aware after the fact that the server_list attribute/instance variable has been marked as "dirty".
        '''
        self.render_ui_layout()
    
    # ---------------------------------------------------------------------------------------------
    # Method to stop a different application server
    # ---------------------------------------------------------------------------------------------

    def stop_server(self, port):
        '''
        Note to self: Write the docstring for the start_new_server method later

        Signed off by: Huy Nguyen

        Signed off at: Sep 24, 5:13 AM, 2024
        '''

        '''
        The port must be an integer.
        The port cannot be anything else other than an integer.
        This is making sure that the port is an integer.
        I would highly recommend that you do this, since I have encountered previous issues where the port was not an integer and it was breaking the code.
        This is not required but highly recommended.
        '''
        port = int(port)
        
        # I find this helpful for debugging purposes, for easy viewing from the terminal.
        # Therefore this is not being commented out. You can comment it out if you want.
        print(f"Attempting to stop server at port {port}")

        '''
        We use the .get() method to get the server at the port.
        This is required to get the server at the port.
        Some important notes:
        - servers is a dictionary that stores the servers.
        - The key is the port number and the value is the process.
        - We are using the .get() method to get the server at the port or more specifically the process at the port.
        '''
        server = self.servers.get(port)

        '''
        If there is no server at the port, we print an error message and return.
        This is not required, but it is recommended, since easier to debug and understand what is happening.
        '''
        if server is None:
            print(f"ERROR: No server found at port {port}")
            return
        '''
        If there is a server at the port, we kill the server.
        We kill the server by sending a SIGTERM signal to the server process identified by the PID (process identifier).
        We then print a message that the server has been stopped.
        If for some reason an error occurs during the stopping of the server, we print an error message.
        This is required to stop the server.
        '''
        try:
            os.kill(server.pid, signal.SIGTERM) 
            print(f"Server at port {port} has been stopped")
        except Exception as e:
            print(f"An error occurred while stopping server at port {port}: {e}")

        '''
        We remove the server from the servers dictionary.
        This reflects the server has been stopped.
        This is required to remove the server from the list of servers.
        '''
        del self.servers[port]

        '''
        The server_list attribute/instance variable is a list that stores the servers.
        We are iterating through the server_list attribute/instance variable.
        We are finding the server in the server_list attribute/instance variable and updating its status to "Stopped".
        This is required to update the UI with the new server status.
        '''
        for server in self.control_state.server_list:
            if server['port'] == port:
                server['status'] = 'Stopped'
                break

        '''
        We inform the UI that the server_list attribute/instance variable "is dirty" (has changed).
        And that it needs to be "cleaned" pushed/updated at the next "flush", the next update.
        '''
        self.control_state.dirty("server_list")

        '''
        We invoke the render_ui_layout method to update and rerender the UI layout.
        This will allow the UI to update the server_list with the new server list.
        Some important notes:
        - This is important because natively the layout is static, we need to rerender the layout to update the UI.
        - This is also important for the JavaScript to update the UI, since the JavaScript is not aware of the server_list attribute/instance variable.
        - It only becomes aware after the fact that the server_list attribute/instance variable has been marked as "dirty".
        '''
        self.render_ui_layout()

        # I find this helpful for debugging purposes, for easy viewing from the terminal.
        # Therefore this is not being commented out. You can comment it out if you want.
        print(f"Server at port {port} has been removed from the list of servers")
    
    # ---------------------------------------------------------------------------------------------
    # Method to register triggers with the controller
    # ---------------------------------------------------------------------------------------------

    def register_triggers(self):
        '''
        Note to self: Write the docstring for the start_new_server method later

        Signed off by: Huy Nguyen

        Signed off at: Sep 24, 5:21 AM, 2024
        '''

        '''
        We are registering the trigger to manager server with the controller.
        This is required because we need to call a method from JavaScript to Python to stop a server.
        The only exception is if you are using a custom UI/layout/client, then you will not need to register the trigger.
        You would directly bind it through a state, and have it be a state change handler.
        But since we are using the default UI/layout/client, we need to register the trigger.
        '''
        self.control_ctrl.trigger("handle_stop_server")(self.handle_stop_server)

    # ---------------------------------------------------------------------------------------------
    # Trigger to handle stopping a server
    # ---------------------------------------------------------------------------------------------

    def handle_stop_server(self, port):
        '''
        Note to self: Write the docstring for the start_new_server method later

        Signed off by: Huy Nguyen

        Signed off at: Sep 24, 5:24 AM, 2024
        '''

        # I find this helpful for debugging purposes, for easy viewing from the terminal.
        # Therefore this is not being commented out. You can comment it out if you want.
        print("Stopping server with port:", port)

        '''
        We are invoking the stop_server method to stop the server.
        We are passing the port to the stop_server method.
        The reason we are not directly using the stop_server method is because users do not need to know what the stop_server method does.
        They just need to give the port and know that the server will be stopped.
        This is required to stop the server.
        '''
        self.stop_server(port) 

    # ---------------------------------------------------------------------------------------------
    # The interface for the server manager
    # ---------------------------------------------------------------------------------------------
    
    def render_ui_layout(self):
        '''
        Note to self: Write the docstring for the start_new_server method later

        Signed off by: Huy Nguyen

        Signed off at: Sep 24, 5:27 AM, 2024
        '''

        '''
        We are using the SinglePageLayout class from the trame.layout library to create the layout.
        This is required if you are not using a custom UI/layout/client.
        We are required to pass the server to the SinglePageLayout class as an argument.
        Some important notes:
        - The SinglePageLayout class is a layout class that is used to create a single page layout.
        - It is not meant to be used to build a multi-page layout, but it is possible, but you will need to research and implement it.
          Since this current implementation is for a single page layout, multi-page layout is not discussed or implemented.
        - If you are using a custom UI/layout/client, you do not need to use the SinglePageLayout class, 
          you will be primarily writing your own custom UI/layout/client using JavaScript, HTML, and CSS.
        - This is a lot easier to use and is recommended if you have little experience with web development.
        '''
        with SinglePageLayout(self.servers_manager) as layout:
            '''
            We get the server name and set it as the title of the layout.
            We are also clearing the content of the layout. Since it needs to be rerendered whenever the UI is updated (by invoking the render_ui_layout method).
            '''
            layout.title.set_text("Server Manager")
            layout.content.clear()

            '''
            The basic layout for the server manager.
            To the very left of the layout, we have a button to start a new server.
            Some important notes:
            - The button is to the left of the layout, since most people read from left to right.
            - Upon clicking the button, a new server will be started by invoking the start_new_server method.

            Underneath the button, we have a card that displays the active servers.
            The card contains a list of the active servers.
            Each server is displayed with its port number and status.
            The status of the server is displayed in the color green if the server is running and red if the server is stopped.
            To the right of the server status, there is a stop button.
            The stop button is used to stop the server, this is done by invoking the handle_stop_server trigger.
            '''
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
        '''
        Note to self: Write the docstring for the start_new_server method later

        Signed off by: Huy Nguyen

        Signed off at: Sep 24, 5:27 AM, 2024
        '''
        # If I give the --server argument to the server manager, the browser won't open.
        # But just in case I want to open the browser, I have this print statement to use if I do need to open the browser.
        # Keeping this uncommented as it allows me to click it, and it'll open the browser.
        # Instead of having to manually go to a browser, open it, and type in the URL.
        print(f"Starting Server_Manager at http://localhost:{port}/index.html")

        '''
        We start the server manager at the specified port given as an argument.
        '''
        self.servers_manager.start(port=port)

if __name__ == "__main__":
    '''
    Note to self: Write the docstring for the main() method later

    Signed off by: Huy Nguyen

    Signed off at: Sep 24, 5:27 AM, 2024
    '''
    import sys

    '''
    Initialize an instance of the ServerManager class.
    We need to do this because we need to start the server manager.
    '''
    server_manager = ServerManager()
    
    '''
    If the argument "--launch_server" is in the command line arguments, we start a new server.
    sys.argv is a list in Python that contains the command-line arguments passed to the script.
    You can see the command-line arguments by looking at the command variable in start_new_server method or by printing sys.argv.
    sys.argv.index("--launch_server") + 1 finds the position of the argument "--launch_server" and adds 1, the fourth argument/flag, which is the port number.

    We iterate through the arguments/flags using list comprehension and convert the arguments/flags to integers, and assigning it to a local variable called ports.

    If you want to run the server without running the server manager, you can directly give the argument "--launch_server" followed by the port number.
    Such as (assuming you are in a virtual environment, and your file is named safety_h.py):
    python safety_h.py --launch_server 5456

    However, to start the multiple servers concurrently, you need to run the server manager.
    '''
    if "--launch_server" in sys.argv:
        ports = [int(arg) for arg in sys.argv[sys.argv.index("--launch_server") + 1:]]

        # I find this helpful for debugging purposes, for easy viewing from the terminal.
        # Therefore this is not being commented out. You can comment it out if you want.
        print("Ports: ", ports)

        '''
        We are creating a new event loop using the asyncio module.
        This is required if we are starting a new server asynchronously.
        '''
        loop = asyncio.get_event_loop()

        '''
        We are iterating through the ports and starting a new server for each port.
        We are creating a new instance of the BaseHistogramApp class and giving it a name, the port argument from the list of ports based on the iteration.
        We are creating a new asyncio Task inside the event loop.
        It needs to be using the create_task method from the event loop since we are executing the instance of the histogram app asynchronously.
        We run the event loop until the task is completed.
        Some important notes:
        - The histogram app base class, and any instance of it, is running servers as Tasks.
        - Task is a subclass of Future, and it is used to run coroutines concurrently.
        - Tasks are used to run coroutines concurrently.
        - Coroutines are used to run asynchronous code concurrently, which is what we are need to run multiple servers concurrently.
        - Coroutines functions and methods are defined with the async keyword and needed to be awaited, using the await keyword.

        This is required to start multiple servers concurrently.
        '''
        for port in ports:
            histogram_app = BaseHistogramApp("my_histogram_app", port)
            
            task = loop.create_task(histogram_app.start_new_server_async())

            loop.run_until_complete(task)
    else:
        '''
        If we don't directly give an argument to start a new server, we start the server manager.
        We start the server manager at port 8080, but this is up to your discretion.
        '''
        server_manager.start(port=8080)