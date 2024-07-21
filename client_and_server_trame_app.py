# needed for the launcher to work
import argparse

# needed for trame to work
from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vtk, vuetify

# the backend of trame to use, which is VTK
import vtk as standard_vtk

# needed to work with data manipulation (too slow for large datasets)
import numpy as np

# ideally used for large datasets instead of numpy
import dask

# needed to read CSV files
import pandas as pd

# needed to work with Dask DataFrames, which is a parallelized version of Pandas and used to read the CSV file for large datasets
import dask.dataframe as dd

# needed to work with file input
from io import BytesIO

# needed to do benchmarking
import time

# needed to increase recursion limit for large datasets
import sys

# for debugging purposes
import logging

# needed to work with temporary files (for file input using dask)
import tempfile
import os

# -----------------------------------------------------------------------------
# Increase recursion limit for large datasets
# -----------------------------------------------------------------------------

sys.setrecursionlimit(10000)

# -----------------------------------------------------------------------------
# Logging setup (for debugging)
# -----------------------------------------------------------------------------

#logging.basicConfig(level=logging.DEBUG)

# -----------------------------------------------------------------------------
# Trame setup
# -----------------------------------------------------------------------------

server = get_server(client_type="vue2")
state, ctrl = server.state, server.controller

# -----------------------------------------------------------------------------
# VTK code
# -----------------------------------------------------------------------------

# For testing performance
start_time = time.time()

# Initial histogram data
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

# For testing performance
end_time = time.time()
print(f"Histogram creation took {end_time - start_time} seconds")

# Create trame layout
layout = SinglePageLayout(server, "Histogram Viewer")

# -----------------------------------------------------------------------------
# State change handler for updating histogram
# -----------------------------------------------------------------------------

@state.change("bins")
def update_histogram(bins, **kwargs):
    start_time = time.time() # For testing performance
    bins = int(bins)
    hist, bin_edges = np.histogram(np_data, bins)
    arrX.Reset()
    arrY.Reset()
    for i in range(len(hist)):
        arrX.InsertNextValue(bin_edges[i])
        arrY.InsertNextValue(hist[i])
    table.Modified()
    ctrl.view_update()
    end_time = time.time() # For testing performance
    print(f"Histogram update took {end_time - start_time} seconds") # For testing performance

# -----------------------------------------------------------------------------
# State change handler for file input
# -----------------------------------------------------------------------------

@state.change("file_input")
def on_file_input_change(file_input, **kwargs):
    print("on_file_input_change invoked") # for debugging purposes
    if file_input:
        tmp_path = None
        try:
            content = file_input['content']
            #print(f"Content type: {type(content)}") # for debugging purposes
            #print(f"Content preview: {content[:500]}")  # for debugging purposes

            # Write content to a temporary file
            # This is important because dask will not work with BytesIO
            # dask will encounter a recursion error when reading from BytesIO:
            # An error occurred: An error occurred while calling the read_csv method registered to the pandas backend.
            # Original Message: maximum recursion depth exceeded while calling a Python object
            # We workaround this by writing the content to a temporary file and reading from it using dask
            with tempfile.NamedTemporaryFile(delete=False, mode='wb') as tmp:
                start_time_of_writing_to_temporary_file = time.time()
                tmp.write(content)
                tmp_path = tmp.name
                end_time_of_writing_to_temporary_file = time.time()
                print(f"Writing to temporary file took {end_time_of_writing_to_temporary_file - start_time_of_writing_to_temporary_file} seconds")

            print(f"Temporary file path: {tmp_path}")
            start_time_for_dask_to_read_csv = time.time()
            df_dask = dd.read_csv(tmp_path)
            end_time_for_dask_to_read_csv = time.time()
            print("Dask read_csv succeeded")
            print(f"Reading CSV file using Dask took {end_time_for_dask_to_read_csv - start_time_for_dask_to_read_csv} seconds")
            combined_time = (end_time_of_writing_to_temporary_file - start_time_of_writing_to_temporary_file) + (end_time_for_dask_to_read_csv - start_time_for_dask_to_read_csv)
            print(f"Over all time it took using dask took {combined_time} seconds")

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
            np_data = df_dask[state.selected_column].values.compute()  # compute() to materialize values

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
                print(f"Temporary file {tmp_path} deleted.")

            
# -----------------------------------------------------------------------------
# State change handler for selected column
# -----------------------------------------------------------------------------

@state.change("selected_column")
def on_selected_column_change(selected_column, **kwargs):
    if state.file_input and selected_column:
        try:
            # TODO: Replace pandas with dask
            # Load the CSV data from the 'content' key
            content = state.file_input['content']
            df = pd.read_csv(BytesIO(content))
            #df = dd.read_csv(BytesIO(content))

            # Select the column to use
            global np_data
            np_data = df[selected_column].values

            # Update the histogram with the new data
            update_histogram(state.bins)
        except KeyError as e:
            print(f"KeyError: {e} - Check the structure of the CSV file.")
        except Exception as e:
            print(f"An error occurred: {e}")

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
