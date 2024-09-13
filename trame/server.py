from trame.app import get_server
from trame.decorators import TrameApp, change
from trame.widgets import vtk
import numpy as np
import vtk as standard_vtk
import pandas as pd
from io import BytesIO
import base64
import json

@TrameApp()
class HistogramApp:
    """
    This class uses VTK to render and visualize a histogram.
    It is interactive and allows the user to change the number of bins,
    upload a CSV file, and select a column.
    By default, the number of bins is set to 5.
    """
    
    def __init__(self):
        # Initialize server
        self.server = get_server(client_type="vue2")

        # Initialize data and states
        self.np_data = np.random.normal(size=1000)
        self.server.state.bins = 5
        self.server.state.file_input = None
        self.server.state.selected_column = None

        # Initialize VTK objects
        self.histogram_vtk()
        self.client_view = vtk.VtkRemoteView(
            self.renderWindow, trame_server=self.server, ref="view"
        )

        # Register WebSocket message handler
        self.server.websocket_on_message = self.on_message

        # Debugging purposes
        self.call_count = 0 

    def histogram_vtk(self):
        """
        Setup VTK histogram visualization.
        """
        self.hist, self.bin_edges = np.histogram(self.np_data, self.server.state.bins)

        # Create vtkTable and vtkFloatArray(s)
        self.table = standard_vtk.vtkTable()
        self.arrX = standard_vtk.vtkFloatArray()
        self.arrX.SetName("X Axis")
        self.arrY = standard_vtk.vtkFloatArray()
        self.arrY.SetName("Frequency")

        # Populate vtkFloatArray(s) with data
        for i in range(len(self.hist)):
            self.arrX.InsertNextValue(self.bin_edges[i])
            self.arrY.InsertNextValue(self.hist[i])
                
        # Add vtkFloatArray(s) to vtkTable
        self.table.AddColumn(self.arrX)
        self.table.AddColumn(self.arrY)

        # Create and setup vtkPlotBar
        self.plot = standard_vtk.vtkPlotBar()
        self.plot.SetInputData(self.table)
        self.plot.SetInputArray(0, "X Axis")
        self.plot.SetInputArray(1, "Frequency")
        self.plot.SetColor(0, 0, 0, 255)

        # Create vtkChartXY and add plot
        self.chart = standard_vtk.vtkChartXY()
        self.chart.SetBarWidthFraction(1.0)
        self.chart.GetAxis(0).SetTitle("Frequency")
        self.chart.GetAxis(1).SetTitle("Feature")
        self.chart.AddPlot(self.plot)

        # Create vtkContextView and add chart
        self.view = standard_vtk.vtkContextView()
        self.view.GetScene().AddItem(self.chart)
        self.renderWindow = self.view.GetRenderWindow()
        self.view.GetRenderWindow().SetSize(800, 600)

    def update_histogram(self, bins):
        """
        Update the histogram when the bins change.
        """
        bins = int(bins)
        self.hist, self.bin_edges = np.histogram(self.np_data, bins=bins)

        self.arrX.Reset()
        self.arrY.Reset()

        for i in range(len(self.hist)):
            self.arrX.InsertNextValue(self.bin_edges[i])
            self.arrY.InsertNextValue(self.hist[i])

        self.table.Modified()
        self.renderWindow.Render()

    @change("bins")
    def on_bins_change(self, bins, **kwargs):
        """
        Handler for bin changes.
        """
        self.update_histogram(bins)
        print("Changed bins to:", bins)

    @change("file_input")
    def on_file_input_change(self, file_input, **kwargs):
        """
        Handler for file input changes.
        """
        if file_input:
            print("A file is being uploaded...")
            try:
                # Load the CSV data from the 'content' key                
                content = BytesIO(base64.b64decode(file_input['content']))
                df = pd.read_csv(content)

                # Update the dropdown options with the DataFrame columns
                self.server.state.column_options = df.columns.tolist()
                print(f"Column options updated: {self.server.state.column_options}")

                self.on_column_options_change(self.server.state.column_options)

                # Select the first column by default
                self.server.state.selected_column = self.server.state.column_options[0] 
                print(f"Selected column: {self.server.state.selected_column}")

                # Select the column to use
                self.np_data = df[self.server.state.selected_column].values
                print(f"Data for selected column: {self.np_data}")

                # Update the histogram with the new data
                self.update_histogram(self.server.state.bins)
                print("Histogram updated")
            except KeyError as e:
                print(f"KeyError: {e} - Check the structure of file_input and the CSV file.")
            except Exception as e:
                print(f"An error occurred (file_input): {e}")

    @change("column_options")
    def on_column_options_change(self, column_options, **kwargs):
        """
        Handler for column options changes.
        """
        # Prevent the method from being called indefinitely
        if self.call_count >= 5:
            print("on_column_options_change has been called 5 times. It will not be called again.")
            return

        self.server.state.column_options = column_options
        self.server.state.dirty('column_options')
        print("Column options sent to the client")

        self.call_count += 1

    @change("selected_column")
    def on_selected_column_change(self, selected_column, **kwargs):
        """
        Handler for selected column changes.
        """
        if self.server.state.file_input and selected_column:
            try:
                # Load the CSV data from the 'content' key
                content = base64.b64decode(self.server.state.file_input['content'])
                df = pd.read_csv(BytesIO(content))

                # Select the column to use
                self.np_data = df[selected_column].values
                print(f"Data for selected column: {self.np_data}")

                # Update the histogram with the new data
                self.update_histogram(self.server.state.bins)
            except KeyError as e:
                print(f"KeyError: {e} - Check the structure of the CSV file.")
            except Exception as e:
                print(f"An error occurred (selected_column): {e}")

    def on_message(self, websocket, path):
        """
        Handle incoming WebSocket messages.
        """
        try:
            msg = websocket.recv()
            data = json.loads(msg)
            if data['type'] == 'dataset':
                datasetname = data['datasetname']
                datasetDid = data['datasetDid']
                print(f"Received selected dataset did from client: {datasetDid} for dataset: {datasetname}")
                # Optionally, update server state
                self.server.state.datasetDid = datasetDid
        except json.JSONDecodeError:
            print("Failed to decode JSON message")

if __name__ == "__main__":
    histogram_app = HistogramApp()
    histogram_app.server.start()
