# Needed for the launcher to work. You can comment this out if you are not using the launcher.
#import argparse

# Needed for trame to work.
from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vtk, vuetify

# The backend or the server side code of trame, which is VTK.
import vtk as standard_vtk

# Needed to work with data manipulation, too slow for large (byte size and row/column size) datasets.
import numpy as np

# Ideally used for large (byte size and row/column size) datasets instead of numpy.
import dask

# Needed to read CSV files.
import pandas as pd

# Needed if you want to use Dask DataFrame, which is a parallelized version of Pandas and used to read the CSV file for large (byte size and row/column size) datasets.
# From my experiments with Dask DataFrame, it is much faster than Pandas for all datasets types (byte size and row/column size).
# I still need to do more experiments to see if it is faster than Pandas for larger (byte size and row/column size) datasets.
import dask.dataframe as dd

# Needed to work with file inputs.
# Honestly, I am not sure if this is needed anymore since I am using Dask DataFrames to read the CSV file.
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
hist, bin_edges = np.histogram(np_data, bins)

# Create a vtkTable
table = standard_vtk.vtkTable()

# Create vtkFloatArray for X and Y axes
arrX = standard_vtk.vtkFloatArray()
arrX.SetName("X Axis")
arrY = standard_vtk.vtkFloatArray()
arrY.SetName("Frequency")

# Populate vtkFloatArray(s) with data
for i in range(len(hist)):
    arrX.InsertNextValue(bin_edges[i])
    arrY.InsertNextValue(hist[i])

# Add vtkFloatArray(s) to vtkTable
table.AddColumn(arrX)
table.AddColumn(arrY)

# Create vtkPlotBar and set data
plot = standard_vtk.vtkPlotBar()
plot.SetInputData(table)
plot.SetInputArray(0, "X Axis")
plot.SetInputArray(1, "Frequency")
plot.SetColor(0, 0, 0, 255)

# Create vtkChartXY and add plot
chart = standard_vtk.vtkChartXY()
chart.SetBarWidthFraction(1.0)
chart.GetAxis(0).SetTitle("Frequency")
chart.GetAxis(1).SetTitle("Feature")
chart.AddPlot(plot)

# Create vtkContextView and add chart
view = standard_vtk.vtkContextView()
view.GetScene().AddItem(chart)
view.GetRenderWindow().SetSize(800, 600)

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
    
    start_time_to_calculate_histogram = time.time() # For testing performance, this measure how long it takes to calculate the histogram.
    hist, bin_edges = np.histogram(np_data, bins)
    end_time_to_calculate_histogram = time.time() # For testing performance, this measure how long it takes to calculate the histogram.
    print(f"Calculating the histogram took {end_time_to_calculate_histogram - start_time_to_calculate_histogram} seconds") # For testing performance, this measure how long it takes to calculate the histogram.
    
    arrX.Reset()
    arrY.Reset()
    for i in range(len(hist)):
        arrX.InsertNextValue(bin_edges[i])
        arrY.InsertNextValue(hist[i])
    table.Modified()
    ctrl.view_update()
    end_time = time.time() # For testing performance, this is what matters!
    print(f"Histogram update took {end_time - start_time} seconds") # For testing performance (latency), this is what matters!

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
