from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vtk, vuetify
import numpy as np
import vtk as standard_vtk
import pandas as pd
from io import BytesIO

np_data = np.array([])

def update_histogram(bins):
    global table, arrX, arrY, renderWindow, html_view, chart
    bins = int(bins)
    if np_data.size > 0:

        hist, bin_edges = np.histogram(np_data, bins=bins)

        arrX.Reset()
        arrY.Reset()

        for i in range(len(hist)):
            arrX.InsertNextValue(bin_edges[i])
            arrY.InsertNextValue(hist[i])

        arrX.InsertNextValue(bin_edges[-1])
        arrY.InsertNextValue(0)

        table.Modified()
        renderWindow.Render()
        html_view.update()

        custom_zoom_fit()
    else:
        print("No data to plot.") 

def custom_zoom_fit():
    global chart, arrX, arrY

    max_x = arrX.GetRange()[1]
    max_y = arrY.GetRange()[1]

    margin_factor = 5
    x_min, x_max = 0, max_x * margin_factor
    y_min, y_max = 0, max_y * margin_factor

    chart.GetAxis(0).SetRange(x_min, x_max)  
    chart.GetAxis(1).SetRange(y_min, y_max)  
    renderWindow.Render()

table = standard_vtk.vtkTable()

arrX = standard_vtk.vtkFloatArray()
arrX.SetName("X Axis")

arrY = standard_vtk.vtkFloatArray()
arrY.SetName("Frequency")

arrX.SetNumberOfComponents(1)
arrY.SetNumberOfComponents(1)

table.AddColumn(arrX)
table.AddColumn(arrY)

plot = standard_vtk.vtkPlotBar()
plot.SetInputData(table)
plot.SetInputArray(0, "X Axis")
plot.SetInputArray(1, "Frequency")
plot.SetColor(0, 0, 0, 255)  
plot.SetWidth(1) 

chart = standard_vtk.vtkChartXY()
chart.AddPlot(plot)

view = standard_vtk.vtkContextView()
view.GetScene().AddItem(chart)
renderWindow = view.GetRenderWindow()
renderWindow.SetSize(800, 600)

# -----------------------------------------------------------------------------
# Get a server to work with
# -----------------------------------------------------------------------------

server = get_server(client_type="vue2")

# -----------------------------------------------------------------------------
# GUI
# -----------------------------------------------------------------------------

state, ctrl = server.state, server.controller

html_view = None

state.num_bins = 20
state.file_input = None

@state.change("num_bins")
def on_num_bins_change(num_bins, **kwargs):
    update_histogram(num_bins)

@state.change("file_input")
def on_file_input_change(file_input, **kwargs):
    global np_data
    if file_input:
        try:
            content = file_input['content']
            df = pd.read_csv(BytesIO(content))
            np_data = df['Area'].values
            update_histogram(state.num_bins)
        except KeyError as e:
            print(f"KeyError: {e} - Check the structure of file_input and the CSV file.")
        except Exception as e:
            print(f"An error occurred: {e}")

with SinglePageLayout(server) as layout:
    with layout.content:
        with vuetify.VContainer(
            fluid=True,
            classes="pa-0 fill-height",
        ):
            vuetify.VSlider(
                v_model=("num_bins", 20),
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
            html_view = vtk.VtkRemoteView(renderWindow)
            ctrl.on_server_ready.add(html_view.update)

# Initialize the histogram with default number of bins
update_histogram(20)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    server.start()