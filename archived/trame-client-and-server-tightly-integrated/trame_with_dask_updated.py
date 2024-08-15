# import argparse if you want to launch multiple instances of the app with different ports.
# import argparse

from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vtk, vuetify
import vtk as standard_vtk

import numpy as np

import dask.dataframe as dd
import dask.array as da

import tempfile
import os

# -----------------------------------------------------------------------------
# Trame setup
# -----------------------------------------------------------------------------

server = get_server(client_type="vue2")
state, ctrl = server.state, server.controller

# -----------------------------------------------------------------------------
# VTK code
# -----------------------------------------------------------------------------

np_data = np.random.normal(size=1000)
bins = np.linspace(-3, 3, 20)
    
data_size = np_data.size * np_data.itemsize
    
if data_size < 5_000_000:
    hist, bin_edges = np.histogram(np_data, bins)
else:
    dask_data = da.from_array(np_data, chunks='auto')  
    data_min, data_max = dask_data.min().compute(), dask_data.max().compute()
    hist, bin_edges = da.histogram(dask_data, bins=bins, range=(data_min, data_max))

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


layout = SinglePageLayout(server, "Histogram Viewer")

# -----------------------------------------------------------------------------
# State change handler for updating histogram
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# State change handler for file input
# -----------------------------------------------------------------------------

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

            global np_data
            
            state.np_data = df_dask[state.selected_column].values.compute()

            update_histogram(state.bins)
        except KeyError as e:
            print(f"KeyError: {e} - Check the structure of file_input and the CSV file.")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

            
# -----------------------------------------------------------------------------
# State change handler for selected column
# -----------------------------------------------------------------------------

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


            global np_data
            
            np_data = df_dask[selected_column].values.compute() 

            update_histogram(state.bins)
        except KeyError as e:
            print(f"KeyError: {e} - Check the structure of the CSV file.")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

# -----------------------------------------------------------------------------
# GUI
# -----------------------------------------------------------------------------

state.trame__title = "Histogram Viewer"
state.bins = 5 
state.file_input = None
state.column_options = []

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

'''
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the app with specified port.")
    parser.add_argument("--port", type=int, default=5454, help="Port to run the server on.")
    args = parser.parse_args()
    
    server.start(port=args.port)
'''