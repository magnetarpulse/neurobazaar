from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vtk, vuetify
import numpy as np
import vtk as standard_vtk
import pandas as pd
from io import BytesIO

# Initialize np_data as an empty array
np_data = np.array([])

# Function to update the histogram based on the number of bins
def update_histogram(bins):
    global table, arrX, arrY, renderWindow, html_view, chart
    bins = int(bins)
    print(f"Updating histogram with {bins} bins.")  # Debug print
    if np_data.size > 0:
        hist, bin_edges = np.histogram(np_data, bins=bins)
        print(f"Histogram: {hist}")  # Debug print
        print(f"Bin edges: {bin_edges}")  # Debug print

        arrX.Reset()
        arrY.Reset()

        for i in range(len(hist)):
            arrX.InsertNextValue(bin_edges[i])
            arrY.InsertNextValue(hist[i])

        # Insert the last bin edge
        arrX.InsertNextValue(bin_edges[-1])
        arrY.InsertNextValue(0)

        table.Modified()
        renderWindow.Render()
        print("Histogram updated.")  # Debug print
        html_view.update()
        print("html_view updated.")  # Debug print

        # Adjust the zoom to fit the data
        custom_zoom_fit()
    else:
        print("No data to plot.")  # Debug print

def custom_zoom_fit():
    global chart, arrX, arrY

    # Calculate the maximum X and Y values
    max_x = arrX.GetRange()[1]
    max_y = arrY.GetRange()[1]

    # Set the zoom window with a margin
    margin_factor = 5
    x_min, x_max = 0, max_x * margin_factor
    y_min, y_max = 0, max_y * margin_factor

    # Apply the custom zoom window to the X and Y axes
    chart.GetAxis(0).SetRange(x_min, x_max)  # X-axis
    chart.GetAxis(1).SetRange(y_min, y_max)  # Y-axis
    renderWindow.Render()

# Create a vtkTable
table = standard_vtk.vtkTable()

# Create a vtkFloatArray for X and Y axis and add the data to it
arrX = standard_vtk.vtkFloatArray()
arrX.SetName("X Axis")

arrY = standard_vtk.vtkFloatArray()
arrY.SetName("Frequency")

# Initialize the histogram arrays
arrX.SetNumberOfComponents(1)
arrY.SetNumberOfComponents(1)

table.AddColumn(arrX)
table.AddColumn(arrY)

# Create a vtkPlotBar and set the data to it
plot = standard_vtk.vtkPlotBar()
plot.SetInputData(table)
plot.SetInputArray(0, "X Axis")
plot.SetInputArray(1, "Frequency")
plot.SetColor(0, 0, 0, 255)  # Set the color to black
plot.SetWidth(1)  # Set the width of the bars to fill the entire space

# Create a vtkChartXY and add the plot to it
chart = standard_vtk.vtkChartXY()
chart.AddPlot(plot)

# Create a vtkContextView, add the chart to it, and render it
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

# Initialize the html_view as a global variable
html_view = None

state.num_bins = 20
state.file_input = None

# Define the slider change behavior
@state.change("num_bins")
def on_num_bins_change(num_bins, **kwargs):
    print(f"Slider value changed: {num_bins}")  # Debug print
    update_histogram(num_bins)

# Define the file input change behavior
@state.change("file_input")
def on_file_input_change(file_input, **kwargs):
    global np_data
    print(f"File input changed: {file_input}")  # Debug print
    if file_input:
        try:
            # Load the CSV data from the 'content' key
            content = file_input['content']
            df = pd.read_csv(BytesIO(content))
            print(f"CSV data loaded: {df.head()}")  # Debug print
            # Select the column to use
            np_data = df['Area'].values
            print(f"Selected data: {np_data}")  # Debug print
            # Update the histogram with the new data
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
                min=10,
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
