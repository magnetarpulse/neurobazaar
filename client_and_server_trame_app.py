# Needed for the launcher to work. You can comment this out if you are not using the launcher.
#import argparse

# Needed for trame to work.
from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vtk, vuetify

# The backend or the server side code of trame, which is VTK.
import vtk as standard_vtk

# Needed to work with data manipulation, too slow for large (byte size and row/column size) datasets.
# Edit: My original statement/assumpution was half correct and half incorrect.
# Indeed, for larger datatsets (byte size and row/column size) Dask is faster than NumPy.

# But it is not because NumPy is slower computing the data, actually it is faster than Dask for small datasets.
# Instead the reason why NumPy is slower or cannot handle large datasets is because it loads the entire dataset into memory.
# This is not a problem for small datasets, but for large datasets it is a problem.
# Dask on the other hand, does not load the entire dataset into memory, instead it loads the dataset in chunks.
# This makes Dask slower for smaller datasets in comparison to NumPy, because the operations are not done in memory.
# However, Dask can handle larger datasets because it does not load the entire dataset into memory and therefore "faster" than NumPy who cannot handle large datasets.
# A more accurate description of the situation is that NumPy is faster than Dask for small datasets, but Dask is able to handle larger datasets while NumPy cannot.
import numpy as np

# Ideally used for large (byte size and row/column size) datasets instead of numpy.
import dask

# Needed to read CSV files.
import pandas as pd

# This is needed to get the available memory of the system.
# This is used because we want to know how much memory is available to us and if NumPy or Dask can handle the dataset.
import psutil

# Needed if you want to use Dask DataFrame, which is a parallelized version of Pandas and used to read the CSV file for large (byte size and row/column size) datasets.
# From my experiments with Dask DataFrame, it is much faster than Pandas for all datasets types (byte size and row/column size).
# I still need to do more experiments to see if it is faster than Pandas for larger (byte size and row/column size) datasets.
import dask.dataframe as dd

#
import dask.array as da

# Needed to work with file inputs.
# Honestly, I am not sure if this is needed anymore since I am using Dask DataFrame to read the CSV file.
# And we are not using pandas to read the CSV file anymore.
from io import BytesIO

# Needed to do benchmarking/performance testing.
# Might in the future replace the time module with something else which is more accurate.
# But for now, I will be using the time module since it is easy and accurate enough for now.
import time

# Used to increase the recursion limit
# Maybe needed to increase recursion limit for large (byte size and row/column size) datasets.
# I am not sure if this is needed anymore since I only increased the recursion limit to try to fix the Dask recursion error.
# But now I no longer have the Dask recursion error.
# But in the future maybe I will need it for large (byte size and row/column size) datasets so I will keep it here for now.
import sys

# For debugging purposes.
# Will always be useful, therefore I will keep it here, although I will comment it out.
#import logging

# Needed to work with temporary files (for file inputs using Dask).
import tempfile
import os

# -----------------------------------------------------------------------------
# Increase recursion limit for large datasets
# -----------------------------------------------------------------------------

# I am not sure if this is needed anymore since I no longer have the Dask recursion error. 
# But I will keep it here for now. This might be useful in the future for very large (byte size and row/column size) datasets.
sys.setrecursionlimit(10000) 

# -----------------------------------------------------------------------------
# Logging setup (for debugging)
# -----------------------------------------------------------------------------

#logging.basicConfig(level=logging.DEBUG) # For debugging purposes.

# -----------------------------------------------------------------------------
# Trame setup
# -----------------------------------------------------------------------------

# One of the disadvantages of using trame and writing the client and the server side code in the same file is that it expects the client to be vue2.
# Although, there is probably a way to change the client type to vue3 and not encounter errors, I have not yet tried to do that in depth. 
# Though if somebody wants to, I think all you need to do for it work with vue3 is to modify the GUI section to include vue3 components.

# The reason I mention the difference between vue2 and vue3 is that the code below is written for vue2.
# But ideally we would want to use vue3 since it is the latest version of vue. 

# But I don't care that much since I will not be writing production code with trame written as a single file, instead I will be writing the client and the server-side code in separate files.
# The only reason why I want to write and continue to update this file is to see the feasability of concepts and do some easy benchmarking/performance(latency) testing. 

# But if somebody else were to write the client and the server-side code in the same file, I would recommend using vue3.
# Because not only is it the latest version but it is also faster and has more features than vue2.

# From the offical vue.js website (https://vuejs.org/about/faq): 
# "In general, Vue 3 provides smaller bundle sizes, better performance, better scalability, and better TypeScript / IDE support. 
# If you are starting a new project today, Vue 3 is the recommended choice. 
# There are only a few reasons for you to consider Vue 2 as of now:
# You need to support IE11. Vue 3 leverages modern JavaScript features and does not support IE11."
server = get_server(client_type="vue2")
state, ctrl = server.state, server.controller

# -----------------------------------------------------------------------------
# VTK code
# -----------------------------------------------------------------------------

# For testing performance:
# The start time for the creation of the "histogram" (actually the render window).
# This does not really matter to be honest since this is irrelevant when there is no inital data.
# Read the comments below to understand why this is irrelevant.
#start_time = time.time()

# Initial histogram data
# I am including inital data for easy verification of the code (such as interactivity of the slider), in production, there will be no inital data.
np_data = np.random.normal(size=1000)
bins = np.linspace(-3, 3, 20)
#hist, bin_edges = np.histogram(np_data, bins)

# Get available memory
available_memory = psutil.virtual_memory().available
print(f"Available memory: {available_memory}") # For debugging purposes.
    
# Convert to bytes
available_memory_bytes = available_memory * (1024 ** 2)
print(f"Available memory in bytes: {available_memory_bytes}") # For debugging purposes.
    
# Set a threshold for memory usage, say 80%
memory_usage_threshold = 0.8 * available_memory_bytes
print(f"Memory usage threshold: {memory_usage_threshold}") # For debugging purposes.
    
data_size = np_data.size * np_data.itemsize  # size in bytes
#data_size = np_data.size
    
if data_size < 5_000_000:
    # Use NumPy for small datasets, it is faster than Dask for small datasets.
    computation_type = "NumPy"
    numpy_start_time = time.time()
    hist, bin_edges = np.histogram(np_data, bins)
    numpy_end_time = time.time() #
    print(f"Calculating the histogram using {computation_type} took {numpy_end_time - numpy_start_time} seconds") # For testing performance (latency), this measure how long it takes to calculate the histogram.
else:
    computation_type = "Dask"
        
    # Assuming np_data is a NumPy array, convert it to a Dask array
    star_time_to_change_np_data_to_dask_data = time.time() # For testing performance (latency), this measure how long it takes to change the NumPy array to a Dask array.
    dask_data = da.from_array(np_data, chunks='auto')
    end_time_to_change_np_data_to_dask_data = time.time() # For testing performance (latency), this measure how long it takes to change the NumPy array to a Dask array.
    print(f"Changing NumPy array to Dask array took {end_time_to_change_np_data_to_dask_data - star_time_to_change_np_data_to_dask_data} seconds") # For testing performance (latency), this measure how long it takes to change the NumPy array to a Dask array.
        
    # Calculate the minimum and maximum values of the data
    start_time_to_calculate_min_and_max = time.time() # For testing performance (latency), this measure how long it takes to calculate the minimum and maximum values of the data.
    data_min, data_max = dask_data.min().compute(), dask_data.max().compute()
    end_time_to_calculate_min_and_max = time.time() # For testing performance (latency), this measure how long it takes to calculate the minimum and maximum values of the data.
    print(f"Calculating the minimum and maximum values of the data took {end_time_to_calculate_min_and_max - start_time_to_calculate_min_and_max} seconds") # For testing performance (latency), this measure how long it takes to calculate the minimum and maximum values of the data.
        
    with dask.config.set(scheduler='threads'):
        # Different types of schedulers: https://docs.dask.org/en/latest/scheduling.html and https://docs.dask.org/en/stable/scheduling.html
        # Scheduler Overview: https://docs.dask.org/en/latest/scheduler-overview.html and https://docs.dask.org/en/stable/scheduler-overview.html
        # Explanations of the different kinds of schedulers:
        ''' 
            1. single-threaded:
                This like having one chef in the kitchen who does all the cooking tasks one by one. 
                They can only do one thing at a time, so if they're chopping vegetables, they can't be stirring the soup. 
                It's simple and there's no confusion about who does what, but it might not be very efficient if there are many tasks to do.
                
            2. threads:
                This is like having multiple chefs in the kitchen who can work on different tasks at the same time.
                One chef could be chopping vegetables while another is stirring the soup. 
                This can be more efficient than a single chef, but it requires careful coordination to make sure the chefs don't get in each other's way. 
                For example, two chefs trying to use the same chopping board at the same time.
                In programming, the scenario "two chefs trying to use the same chopping board at the same time" is analogous to a situation where two threads are trying to access or modify the same shared resource simultaneously.
                This is generally significantly faster than the single-threaded scheduler, as more workers (chefs) are available to perform the computations concurrently than if a single worker (chef) was to perform all the computations sequentially.
            
            3. processes:
                This like having multiple kitchens, each with its own chef. 
                Each chef can work independently without worrying about the others, but it takes more resources (space, equipment, etc.) to set up multiple kitchens. 
                Also, if one chef needs to pass a bowl of chopped vegetables to another chef in a different kitchen, it's more complicated than passing it to a chef in the same kitchen.
                This would be the ideal scenario for a situation where you have multiple CPUs or cores available and you want to take advantage of parallel processing.
                In the context of cloud computing, the term "nodes" often refers to the individual servers or machines that make up the cloud infrastructure. 
                These nodes can be located in different parts of the world, but they are all connected through the Internet and can be used to store, manage, and process data. 
                This is similar to having multiple "kitchens" in the analogy, where each kitchen has its own chef and equipment.
                When we say that processes can be used in cloud computing where you have many nodes available for processing, we're referring to the idea of distributing the computation across multiple nodes. 
                Each node can run one or more processes, and these processes can operate independently without interfering with each other, similar to how each chef in a separate kitchen can work independently.
                This distributed processing can significantly speed up computation, especially for large-scale tasks. 
                For example, if you're processing a large dataset, you can split the dataset into smaller chunks and have each node process a different chunk. 
                This is known as data parallelism.
                However, it's important to note that communication between processes on different nodes can be more complex than communication within the same node. 
                This is similar to how passing a bowl of chopped vegetables to another chef in a different kitchen is more complicated than passing it to a chef in the same kitchen. 
                In the context of cloud computing, this inter-node communication often involves transferring data over the network, which can be slower than communication within the same node.
                This is similar to the threads scheduler, but instead of having multiple threads in the same kitchen, you have multiple kitchens with their own chefs.
        '''
        # Calculate histogram with range specified
        start_time_to_calculate_histogram = time.time() # For testing performance (latency), this measure how long it takes to calculate the histogram.
        hist, bin_edges = da.histogram(dask_data, bins=bins, range=(data_min, data_max))
        end_time_to_calculate_histogram = time.time() # For testing performance (latency), this measure how long it takes to calculate the histogram.
        print(f"Calculating the histogram using {computation_type} took {end_time_to_calculate_histogram - start_time_to_calculate_histogram} seconds") # For testing performance (latency), this measure how long it takes to calculate the histogram.

# Create a vtkTable
start_time_to_create_vtk_table = time.time() # For testing performance (latency), this measure how long it takes to create the vtkTable.
table = standard_vtk.vtkTable()
end_time_to_create_vtk_table = time.time() # For testing performance (latency), this measure how long it takes to create the vtkTable.
print(f"Creating the vtkTable took {end_time_to_create_vtk_table - start_time_to_create_vtk_table} seconds") # For testing performance (latency), this measure how long it takes to create the vtkTable.

# Create vtkFloatArray for X and Y axes
start_time_to_create_vtkFloatArray = time.time() # For testing performance (latency), this measure how long it takes to create the vtkFloatArray for X and Y axes.
arrX = standard_vtk.vtkFloatArray()
arrX.SetName("X Axis")
arrY = standard_vtk.vtkFloatArray()
arrY.SetName("Frequency")
end_time_to_create_vtkFloatArray = time.time() # For testing performance (latency), this measure how long it takes to create the vtkFloatArray for X and Y axes.
print(f"Creating the vtkFloatArray for X and Y axes took {end_time_to_create_vtkFloatArray - start_time_to_create_vtkFloatArray} seconds") # For testing performance (latency), this measure how long it takes to create the vtkFloatArray.

# Populate vtkFloatArray(s) with data
for i in range(len(hist)):
    start_time_to_populate_vtkFloatArray_with_data = time.time() # For testing performance (latency), this measure how long it takes to populate the vtkFloatArray with data.
    arrX.InsertNextValue(bin_edges[i])
    arrY.InsertNextValue(hist[i])
    end_time_to_populate_vtkFloatArray_with_data = time.time() # For testing performance (latency), this measure how long it takes to populate the vtkFloatArray.
    print(f"Populating the vtkFloatArray(s) with data took {end_time_to_populate_vtkFloatArray_with_data - start_time_to_populate_vtkFloatArray_with_data} seconds") # For testing performance (latency), this measure how long it takes to populate the vtkFloatArray with data.

# Add vtkFloatArray(s) to vtkTable
start_time_adding_vtkFloatArray_to_vtkTable = time.time() # For testing performance (latency), this measure how long it takes to add the vtkFloatArray(s) to the vtkTable.
table.AddColumn(arrX)
table.AddColumn(arrY)
end_time_adding_vtkFloatArray_to_vtkTable = time.time() # For testing performance (latency), this measure how long it takes to add the vtkFloatArray(s) to the vtkTable.
print(f"Adding the vtkFloatArray to the vtkTable took {end_time_adding_vtkFloatArray_to_vtkTable - start_time_adding_vtkFloatArray_to_vtkTable} seconds") # For testing performance (latency), this measure how long it takes to add the vtkFloatArray to the vtkTable.

# Create vtkPlotBar and set data
start_time_create_vtkPlotBar_and_set_data = time.time() # For testing performance (latency), this measure how long it takes to create the vtkPlotBar and set the data.
plot = standard_vtk.vtkPlotBar()
plot.SetInputData(table)
plot.SetInputArray(0, "X Axis")
plot.SetInputArray(1, "Frequency")
plot.SetColor(0, 0, 0, 255)
end_time_create_vtkPlotBar_and_set_data = time.time() # For testing performance (latency), this measure how long it takes to create the vtkPlotBar and set the data.
print(f"Creating the vtkPlotBar and setting the data took {end_time_create_vtkPlotBar_and_set_data - start_time_create_vtkPlotBar_and_set_data} seconds") # For testing performance (latency), this measure how long it takes to create the vtkPlotBar and set the data.

# Create vtkChartXY and add plot
start_time_to_create_vtkChartXY_and_add_plot = time.time() # For testing performance (latency), this measure how long it takes to create the vtkChartXY and add the plot.
chart = standard_vtk.vtkChartXY()
chart.SetBarWidthFraction(1.0)
chart.GetAxis(0).SetTitle("Frequency")
chart.GetAxis(1).SetTitle("Feature")
chart.AddPlot(plot)
end_time_to_create_vtkChartXY_and_add_plot = time.time() # For testing performance (latency), this measure how long it takes to create the vtkChartXY and add the plot.
print(f"Creating the vtkChartXY and adding the plot took {end_time_to_create_vtkChartXY_and_add_plot - start_time_to_create_vtkChartXY_and_add_plot} seconds") # For testing performance (latency), this measure how long it takes to create the vtkChartXY and add the plot.

# Create vtkContextView and add chart and get render window
start_time_to_create_vtkContextView_and_add_chart_and_get_render_window = time.time() # For testing performance (latency), this measure how long it takes to create the vtkContextView and add the chart and get the render window.
view = standard_vtk.vtkContextView()
view.GetScene().AddItem(chart)
view.GetRenderWindow().SetSize(800, 600)
end_time_to_create_vtkContextView_and_add_chart_and_get_render_window = time.time() # For testing performance (latency), this measure how long it takes to create the vtkContextView and add the chart and get the render window.
print(f"Creating the vtkContextView, adding the chart, and getting the render window took {end_time_to_create_vtkContextView_and_add_chart_and_get_render_window - start_time_to_create_vtkContextView_and_add_chart_and_get_render_window} seconds") # For testing performance (latency), this measure how long it takes to create the vtkContextView, add the chart, and get the render window.

# For testing performance:
# The end time for the creation of the histogram (actually the render window).
# This does not really matter to be honest since this is irrelevant when there is no inital data.
# Read the comments below to understand why this is irrelevant.
#end_time = time.time()

# For testing performance;
# The print statement.
# This is pretty much irrelevant, I would even go as far to say as it is having the reverse effect of what it is supposed to do.
# Therefore I will be commenting this code out and delete in the future, but for now I will keep it here.

# Why am I deleting it?:
# It is confusing and is misleading for those who do not understand.
# This is not the same as the time/latency it takes to generate the inital histogram based on the data from the CSV file.
# To actually measure the time/latency it took to generate the histogram based on the data from the CSV file you would have to do something different.
# To do that, the performance testing code (start_time, end_time, and print statement) would have to be placed in the update_histogram function (already done).

# What is it?:
# What this is actually measuring is the amount of time/latency it took to generate the histogram based on the inital histogram data (np_data = np.random.normal(size=1000)).
# It would be more accurate to say that this is measuring the inital time/latency to generate the render window. As in the future, tthere won't be any inital data.
# Therefore, this would actually only be measurering the time/latency it takes to generate the render window in the future.
#print(f"Histogram creation took {end_time - start_time} seconds")

# Create trame layout
layout = SinglePageLayout(server, "Histogram Viewer")

# -----------------------------------------------------------------------------
# State change handler for updating histogram
# -----------------------------------------------------------------------------

@state.change("bins")
def update_histogram(bins, **kwargs):
    # This is what matters.
    # This is actually what we want to measure the time/latency it takes to generate the histogram based on the data from the CSV file.
    # That includes the inital histogram generated from the CSV file.
    start_time = time.time() # For testing performance (latency), this is what matters!
    bins = int(bins)
    
    # Get available memory
    available_memory = psutil.virtual_memory().available
    print(f"Available memory: {available_memory}") # For debugging purposes.
    
    # Convert to bytes
    available_memory_bytes = available_memory * (1024 ** 2)
    print(f"Available memory in bytes: {available_memory_bytes}") # For debugging purposes.
    
    # Set a threshold for memory usage, say 80%
    memory_usage_threshold = 0.8 * available_memory_bytes
    print(f"Memory usage threshold: {memory_usage_threshold}") # For debugging purposes.
    
    data_size = np_data.size * np_data.itemsize  # size in bytes
    #data_size = np_data.size
    
    if data_size < 5_000_000:
        # Use NumPy for small datasets, it is faster than Dask for small datasets.
        computation_type = "NumPy"
        numpy_start_time = time.time()
        hist, bin_edges = np.histogram(np_data, bins)
        numpy_end_time = time.time() #
        print(f"Calculating the histogram using {computation_type} took {numpy_end_time - numpy_start_time} seconds") # For testing performance (latency), this measure how long it takes to calculate the histogram.
    else:
        computation_type = "Dask"
        
        # Assuming np_data is a NumPy array, convert it to a Dask array
        star_time_to_change_np_data_to_dask_data = time.time() # For testing performance (latency), this measure how long it takes to change the NumPy array to a Dask array.
        dask_data = da.from_array(np_data, chunks='auto')
        end_time_to_change_np_data_to_dask_data = time.time() # For testing performance (latency), this measure how long it takes to change the NumPy array to a Dask array.
        print(f"Changing NumPy array to Dask array took {end_time_to_change_np_data_to_dask_data - star_time_to_change_np_data_to_dask_data} seconds") # For testing performance (latency), this measure how long it takes to change the NumPy array to a Dask array.
        
        # Calculate the minimum and maximum values of the data
        start_time_to_calculate_min_and_max = time.time() # For testing performance (latency), this measure how long it takes to calculate the minimum and maximum values of the data.
        data_min, data_max = dask_data.min().compute(), dask_data.max().compute()
        end_time_to_calculate_min_and_max = time.time() # For testing performance (latency), this measure how long it takes to calculate the minimum and maximum values of the data.
        print(f"Calculating the minimum and maximum values of the data took {end_time_to_calculate_min_and_max - start_time_to_calculate_min_and_max} seconds") # For testing performance (latency), this measure how long it takes to calculate the minimum and maximum values of the data.
        
        with dask.config.set(scheduler='threads'):
            # Different types of schedulers: https://docs.dask.org/en/latest/scheduling.html and https://docs.dask.org/en/stable/scheduling.html
            # Scheduler Overview: https://docs.dask.org/en/latest/scheduler-overview.html and https://docs.dask.org/en/stable/scheduler-overview.html
            # Explanations of the different kinds of schedulers:
            ''' 
                1. single-threaded:
                    This like having one chef in the kitchen who does all the cooking tasks one by one. 
                    They can only do one thing at a time, so if they're chopping vegetables, they can't be stirring the soup. 
                    It's simple and there's no confusion about who does what, but it might not be very efficient if there are many tasks to do.
                    
                2. threads:
                    This is like having multiple chefs in the kitchen who can work on different tasks at the same time.
                    One chef could be chopping vegetables while another is stirring the soup. 
                    This can be more efficient than a single chef, but it requires careful coordination to make sure the chefs don't get in each other's way. 
                    For example, two chefs trying to use the same chopping board at the same time.
                    In programming, the scenario "two chefs trying to use the same chopping board at the same time" is analogous to a situation where two threads are trying to access or modify the same shared resource simultaneously.
                    This is generally significantly faster than the single-threaded scheduler, as more workers (chefs) are available to perform the computations concurrently than if a single worker (chef) was to perform all the computations sequentially.
                
                3. processes:
                    This like having multiple kitchens, each with its own chef. 
                    Each chef can work independently without worrying about the others, but it takes more resources (space, equipment, etc.) to set up multiple kitchens. 
                    Also, if one chef needs to pass a bowl of chopped vegetables to another chef in a different kitchen, it's more complicated than passing it to a chef in the same kitchen.
                    This would be the ideal scenario for a situation where you have multiple CPUs or cores available and you want to take advantage of parallel processing.
                    In the context of cloud computing, the term "nodes" often refers to the individual servers or machines that make up the cloud infrastructure. 
                    These nodes can be located in different parts of the world, but they are all connected through the Internet and can be used to store, manage, and process data. 
                    This is similar to having multiple "kitchens" in the analogy, where each kitchen has its own chef and equipment.
                    When we say that processes can be used in cloud computing where you have many nodes available for processing, we're referring to the idea of distributing the computation across multiple nodes. 
                    Each node can run one or more processes, and these processes can operate independently without interfering with each other, similar to how each chef in a separate kitchen can work independently.
                    This distributed processing can significantly speed up computation, especially for large-scale tasks. 
                    For example, if you're processing a large dataset, you can split the dataset into smaller chunks and have each node process a different chunk. 
                    This is known as data parallelism.
                    However, it's important to note that communication between processes on different nodes can be more complex than communication within the same node. 
                    This is similar to how passing a bowl of chopped vegetables to another chef in a different kitchen is more complicated than passing it to a chef in the same kitchen. 
                    In the context of cloud computing, this inter-node communication often involves transferring data over the network, which can be slower than communication within the same node.
                    This is similar to the threads scheduler, but instead of having multiple threads in the same kitchen, you have multiple kitchens with their own chefs.
            '''
            # Calculate histogram with range specified
            start_time_to_calculate_histogram = time.time() # For testing performance (latency), this measure how long it takes to calculate the histogram.
            hist, bin_edges = da.histogram(dask_data, bins=bins, range=(data_min, data_max))
            end_time_to_calculate_histogram = time.time() # For testing performance (latency), this measure how long it takes to calculate the histogram.
            print(f"Calculating the histogram using {computation_type} took {end_time_to_calculate_histogram - start_time_to_calculate_histogram} seconds") # For testing performance (latency), this measure how long it takes to calculate the histogram.
    
    start_time_to_reset_vtkFloatArray_of_X_and_Y_axes = time.time() # For testing performance (latency), this measure how long it takes to reset the vtkFloatArray of X and Y axes.
    
    # Reset vtkFloatArray of X and Y axes
    arrX.Reset()
    arrY.Reset()
    end_time_to_reset_vtkFloatArray_of_X_and_Y_axes = time.time() # For testing performance (latency), this measure how long it takes to reset the vtkFloatArray of X and Y axes.
    print(f"Resetting the vtkFloatArray of X and Y axes took {end_time_to_reset_vtkFloatArray_of_X_and_Y_axes - start_time_to_reset_vtkFloatArray_of_X_and_Y_axes} seconds") # For testing performance (latency), this measure how long it takes to reset the vtkFloatArray of X and Y axes.
    
    # Populate vtkFloatArray(s) with data
    for i in range(len(hist)):
        start_time_to_populate_vtkFloatArray_with_data = time.time() # For testing performance (latency), this measure how long it takes to populate the vtkFloatArray with data.
        arrX.InsertNextValue(bin_edges[i])
        arrY.InsertNextValue(hist[i])
        end_time_to_populate_vtkFloatArray_with_data = time.time() # For testing performance (latency), this measure how long it takes to populate the vtkFloatArray with data.
        print(f"Populating the vtkFloatArray with data took {end_time_to_populate_vtkFloatArray_with_data - start_time_to_populate_vtkFloatArray_with_data} seconds") # For testing performance (latency), this measure how long it takes to populate the vtkFloatArray with data.
    
    # The table.Modified() method is used to notify the observers that the table has been modified.
    start_time_table_modified = time.time() # For testing performance (latency), this measure how long it takes to notify the observers that the table has been modified.
    table.Modified()
    end_time_table_modified = time.time() # For testing performance (latency), this measure how long it takes to notify the observers that the table has been modified.
    print(f"Notifying the observers that the table has been modified took {end_time_table_modified - start_time_table_modified} seconds") # For testing performance (latency), this measure how long it takes to notify the observers that the table has been modified.
    
    # Updating the view, the render window, and the histogram
    start_time_to_update_view_render_window_and_histogram = time.time() # For testing performance (latency), this measure how long it takes to update the view, the render window, and the histogram.
    ctrl.view_update()
    end_time_to_update_view_render_window_and_histogram = time.time() # For testing performance (latency), this measure how long it takes to update the view, the render window, and the histogram.
    print(f"Updating the view, the render window, and the histogram took {end_time_to_update_view_render_window_and_histogram - start_time_to_update_view_render_window_and_histogram} seconds") # For testing performance (latency), this measure how long it takes to update the view, the render window, and the histogram.
    
    end_time = time.time() # For testing performance, this is what matters!
    print(f"Histogram update (overall) took {end_time - start_time} seconds") # For testing performance (latency), this is what matters!

# -----------------------------------------------------------------------------
# State change handler for file input
# -----------------------------------------------------------------------------

@state.change("file_input")
def on_file_input_change(file_input, **kwargs):
    #print("on_file_input_change invoked") # For debugging purposes.
    if file_input:
        tmp_path = None
        try:
            content = file_input['content']
            #print(f"Content type: {type(content)}") # For debugging purposes.
            #print(f"Content preview: {content[:500]}")  # For debugging purposes.

            # Write content to a temporary file
            # This is important because Dask DataFrame will not work with BytesIO.
            # Dask DataFrame will encounter a recursion error when reading from BytesIO:
            # An error occurred: An error occurred while calling the read_csv method registered to the pandas backend.
            # Original Message: maximum recursion depth exceeded while calling a Python object.
            # We workaround this by writing the content to a temporary file and reading from it using Dask.
            with tempfile.NamedTemporaryFile(delete=False, mode='wb') as tmp:
                start_time_of_writing_to_temporary_file = time.time() # For (latency) performance testing.
                tmp.write(content)
                tmp_path = tmp.name
                end_time_of_writing_to_temporary_file = time.time() # For (latency) performance testing.
                print(f"Writing to temporary file took {end_time_of_writing_to_temporary_file - start_time_of_writing_to_temporary_file} seconds") # For (latency) performance testing.

            print(f"Temporary file path: {tmp_path}") # For debugging purposes.
            start_time_for_dask_to_read_csv = time.time() # For (latency) performance testing.
            df_dask = dd.read_csv(tmp_path) 
            end_time_for_dask_to_read_csv = time.time() # For (latency) performance testing.
            #print("Dask read_csv succeeded") # For debugging purposes.
            print(f"Reading CSV file using Dask took {end_time_for_dask_to_read_csv - start_time_for_dask_to_read_csv} seconds") # For performance (latency) testing.
            combined_time = (end_time_of_writing_to_temporary_file - start_time_of_writing_to_temporary_file) + (end_time_for_dask_to_read_csv - start_time_for_dask_to_read_csv)
            print(f"Over all time it took using dask took {combined_time} seconds") # For (latency) performance testing.

            # Update the dropdown options with the DataFrame columns
            state.column_options = df_dask.columns.tolist() 

            # Select the first column by default
            state.selected_column = state.column_options[0]

            # Select the column to use
            global np_data
            
            # Dask uses lazy evaluation, which means that computations are not executed immediately when they are declared. 
            # Instead, Dask builds up a task graph of computations to be done, and the actual computations are not performed until you explicitly ask for the result using the .compute() method.
            # The .compute() method is essentially converting the Dask array to a NumPy array and performing all the necessary computations.
            # Find more about the method here: https://docs.dask.org/en/stable/generated/dask.dataframe.DataFrame.compute.html
            
            # Extract the column specified by 'state.selected_column' from the Dask DataFrame 'df_dask'.
            # Then convert it to a NumPy array using the .values attribute. 
            # And then trigger the computation using the .compute() method.
            # The resulting NumPy array is stored in 'state.np_data'.
            state.np_data = df_dask[state.selected_column].values.compute()

            # Update the histogram with the new data
            update_histogram(state.bins)
        except KeyError as e:
            print(f"KeyError: {e} - Check the structure of file_input and the CSV file.")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            # Ensure the temporary file is deleted
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
                print(f"Temporary file {tmp_path} deleted.") # For debugging purposes.

            
# -----------------------------------------------------------------------------
# State change handler for selected column
# -----------------------------------------------------------------------------

@state.change("selected_column")
def on_selected_column_change(selected_column, **kwargs):
    #print("on_selected_column_change invoked") # For debugging purposes.
    if state.file_input and selected_column:
        tmp_path = None
        try:
            content = state.file_input['content']
            #print(f"Content type: {type(content)}") # For debugging purposes.
            #print(f"Content preview: {content[:500]}")  # For debugging purposes.

            # Write content to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, mode='wb') as tmp:
                start_time_of_writing_to_temporary_file = time.time() # For (latency) performance testing.
                tmp.write(content)
                tmp_path = tmp.name
                end_time_of_writing_to_temporary_file = time.time() # For (latency) performance testing.
                print(f"Writing to a second temporary file took {end_time_of_writing_to_temporary_file - start_time_of_writing_to_temporary_file} seconds") # For (latency) performance testing.

            print(f"Temporary file path (second temporary file): {tmp_path}") # For debugging purposes.
            start_time_for_dask_to_read_csv = time.time() # For (latency) performance testing.
            df_dask = dd.read_csv(tmp_path)
            end_time_for_dask_to_read_csv = time.time() # For (latency) performance testing.
            #print("Dask read_csv succeeded") #For debugging purposes.
            print(f"Reading CSV file using Dask took {end_time_for_dask_to_read_csv - start_time_for_dask_to_read_csv} seconds") # For (latency) performance testing.
            combined_time = (end_time_of_writing_to_temporary_file - start_time_of_writing_to_temporary_file) + (end_time_for_dask_to_read_csv - start_time_for_dask_to_read_csv) # For (latency) performance testing.
            print(f"Overall time using Dask: {combined_time} seconds") # For (latency) performance testing.

            # Select the column to use
            global np_data
            
            # Extract the column specified by 'state.selected_column' from the Dask DataFrame 'df_dask'.
            # Then convert it to a NumPy array using the .values attribute. 
            # And then trigger the computation using the .compute() method.
            # The resulting NumPy array is stored in 'state.np_data'.
            np_data = df_dask[selected_column].values.compute() 

            # Update the histogram with the new data
            update_histogram(state.bins)
        except KeyError as e:
            print(f"KeyError: {e} - Check the structure of the CSV file.")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            # Ensure the temporary file is deleted
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
                print(f"Temporary file {tmp_path} deleted.") # For debugging purposes.

# -----------------------------------------------------------------------------
# GUI
# -----------------------------------------------------------------------------

state.trame__title = "Histogram Viewer"
state.bins = 5  # Initial number of bins
state.file_input = None # Initial file input
state.column_options = [] # Initial column options

with SinglePageLayout(server) as layout:
    layout.icon.click = ctrl.view_reset_camera
    layout.title.set_text("VTK Histogram")

    with layout.content:
        with vuetify.VContainer(
            fluid=True, 
            classes="pa-0 fill-height",
        ):
            vuetify.VSlider(
                v_model="bins",
                min=1,
                max=100,
                step=1,
                label="Number of Bins"
            )
            vuetify.VFileInput(
                v_model="file_input",
                label="Upload CSV",
                accept=".csv"
            )
            vuetify.VSelect(
                v_model=("selected_column", None),
                items=("column_options",),
                label="Select Column"
            )
            html_view = vtk.VtkRemoteView(view.GetRenderWindow())
            ctrl.view_update = html_view.update
            ctrl.view_reset_camera = html_view.reset_camera

# -----------------------------------------------------------------------------
# Start the server (no launcher/single-user)
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    server.start(port=5455)

# -----------------------------------------------------------------------------
# Start the server (launcher/multi-users)
# -----------------------------------------------------------------------------

#if __name__ == "__main__":
    #parser = argparse.ArgumentParser(description="Run the app with specified port.")
    #parser.add_argument("--port", type=int, default=5454, help="Port to run the server on.")
    #args = parser.parse_args()
    
    #server.start(port=args.port)