from trame.app import get_server
from trame.decorators import TrameApp, change
from trame.widgets import vtk
import numpy as np
import vtk as standard_vtk
import pandas as pd
from io import BytesIO
import base64

@TrameApp()
class HistogramApp:
    def __init__(self):
        self.server = get_server(client_type="vue2")
    
        self.np_data = np.random.normal(size=1000)
        
        self.server.state.bins = 5 

        self.server.state.file_input = None 

        self.server.state.selected_column = None 
        
        self.histogram_vtk() 

        self.client_view = vtk.VtkRemoteView(
            self.renderWindow, trame_server=self.server, ref="view"
        )
    
    # -----------------------------------------------------------------------------
    # VTK code
    # -----------------------------------------------------------------------------
    
    def histogram_vtk(self):
        self.hist, self.bin_edges = np.histogram(self.np_data, self.server.state.bins)
        
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
            
    # -----------------------------------------------------------------------------
    # VTK code for updating histogram
    # -----------------------------------------------------------------------------
    
    def update_histogram(self, bins):
        bins = int(bins)
        self.hist, self.bin_edges = np.histogram(self.np_data, bins=bins)
        
        self.arrX.Reset()
        self.arrY.Reset()
        
        for i in range(len(self.hist)):
            self.arrX.InsertNextValue(self.bin_edges[i])
            self.arrY.InsertNextValue(self.hist[i])
            
        self.table.Modified()
        self.renderWindow.Render()
        self.client_view.update()
    
    # -----------------------------------------------------------------------------
    # State change handler for updating histogram
    # -----------------------------------------------------------------------------
    
    @change("bins")
    def on_bins_change(self, bins, **kwargs):        
        self.update_histogram(bins)
     
    # -----------------------------------------------------------------------------
    # State change handler for file input
    # -----------------------------------------------------------------------------
    
    @change("file_input")
    def on_file_input_change(self, file_input, **kwargs):        
        if file_input:
            print("A file is being uploaded...") #Debugging purposes
            try:        
                content = BytesIO(base64.b64decode(file_input['content']))
                df = pd.read_csv(content)
                
                self.server.state.column_options = df.columns.tolist()
                
                self.on_column_options_change(self.server.state.column_options)
                
                self.server.state.selected_column = self.server.state.column_options[0] 
                
                self.np_data = df[self.server.state.selected_column].values
                
                self.update_histogram(self.server.state.bins)
            except KeyError as e:
                print(f"KeyError: {e} - Check the structure of file_input and the CSV file.")
            except Exception as e:
                print(f"An error occurred (file_input): {e}")
                
    # -----------------------------------------------------------------------------
    # State change handler for column_options
    # -----------------------------------------------------------------------------

    @change("column_options")
    def on_column_options_change(self, column_options, **kwargs):
        self.server.state.column_options = column_options
                
    # -----------------------------------------------------------------------------
    # State change handler for selected_column
    # -----------------------------------------------------------------------------
    
    @change("selected_column")
    def on_selected_column_change(self, selected_column, **kwargs):        
        if self.server.state.file_input and selected_column:
            try:
                content = base64.b64decode(self.server.state.file_input['content'])
                df = pd.read_csv(BytesIO(content))

                self.np_data = df[selected_column].values

                self.update_histogram(self.server.state.bins)
            except KeyError as e:
                print(f"KeyError: {e} - Check the structure of the CSV file.")
            except Exception as e:
                print(f"An error occurred (selected_column): {e}")
                
if __name__ == "__main__":
    histogram_app= HistogramApp()
    histogram_app.server.start()