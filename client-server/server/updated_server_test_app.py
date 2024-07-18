from trame.app import get_server
from trame.decorators import TrameApp, change, trigger
from trame.widgets import vtk
import numpy as np
import vtk as standard_vtk
import pandas as pd
from io import BytesIO
import base64

@TrameApp()
class HistogramApp:
    '''
    This class is using VTK to render and visualize a histogram.
    It is interactive and allows the user to change the number of bins, upload a CSV file, and select a column.
    When the user changes the number of bins, the histogram updates.
    By default the number of bins is set to 5.
    '''
    
    def __init__(self):
        
        '''
        This is the equivalent of Trame setup in test_app.py. However, Trame set up is done in the __init__ method.
    
        >>> server = get_server(client_type="vue2") from test_app.py is now self.server = get_server().
        >>> html_view = vtk.VtkRemoteView(view.GetRenderWindow()) from test app is now:
        ... self.client_view = vtk.VtkRemoteView(
        ...     self.renderWindow, trame_server=self.server, ref="view"
        ... )
        
        Since we are writing only the server part of the code, we will not include the client_type="vue2" argument or any argument at all.
        However, since the client I want to use is vue.js to connect to the server, I will include the client_type="vue2" argument.
        ''' 
        
        # Ignore the client_type="vue2" argument if you are not using vue.js to connect to the server
        # self.server = get_server() 
        
        self.server = get_server(client_type="vue2") # This is the equivalent of server = get_server(client_type="vue2") from test_app.py
        # print("server:", self.server) for debugging purposes
    
        self.np_data = np.random.normal(size=1000) # np_data = np.random.normal(size=1000) from test_app.py
        # print("np_data:", self.np_data) for debugging purposes
        
        self.server.state.bins = 5 # bins = np.linspace(-3, 3, 20) from test_app.py
        # print ("bins:", self.server.state.bins) for debugging purposes
        
        self.server.state.file_input = None # file_input = None from test_app.py
        # print ("file_input:", self.server.state.file_input) for debugging purposes
        
        self.server.state.selected_column = None # selected_column = None from test_app.py
        # print ("selected_column:", self.server.state.selected_column) for debugging purposes
        
        # TODO: BIG PROBLEM: The client-side is not reciving the updated column_options. The server is updating the column_options correctly but the client is not reciving the updated column_options.
        # TODO: Issue 1. An error occurred (file_input): 'NoneType' object is not callable.
        # Reason for Issue 1: Unkonwn and not sure how to fix it. Low priority for now as there seem to be another solution to the problem.
        # TODO: Need to delete this issue and line of code, it is no longer needed, the main issue is now resolved.
        # Yes, the solution to the problem is to use the on_column_options_change method (state variable "column_options") and write JavaScript code to update the client side.
        # However, for now I will keep this line of code here just in case I need to refer back to it. I will need to remove the code once in late development or early production.
        
        # self.server.state.update_state = None 
        # print ("selected_column:", self.server.state.selected_column) for debugging purposes
        
        # A temporary fix for Issue 2. Cannot Control+C to stop the server. The server is not stopping. Not a big issue, closing the terminal window will stop the server. But strange behavior.
        self.call_count = 0 
        
        # This is the equivalent of the VTK code from test_app.py
        self.histogram_vtk() 
        
        # This is the equivalent of html_view = vtk.VtkRemoteView(view.GetRenderWindow()) from test_app.py, without this line of code, the render window will not be displayed on the client side.
        self.client_view = vtk.VtkRemoteView(
            self.renderWindow, trame_server=self.server, ref="view"
        )
    
    # -----------------------------------------------------------------------------
    # VTK code
    # -----------------------------------------------------------------------------
    
    def histogram_vtk(self):
            
            '''
            This is the equivalent of the VTK code from test_app.py. The VTK code is now in a method called histogram_vtk
            '''
            
            # Initial histogram data
            self.hist, self.bin_edges = np.histogram(self.np_data, self.server.state.bins)
            
            # Create a vtkTable
            self.table = standard_vtk.vtkTable()
            
            # Create vtkFloatArray for X and Y axes
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
            
            # Create vtkPlotBar and set data
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
            
            # Get the render window
            self.renderWindow = self.view.GetRenderWindow()
            self.view.GetRenderWindow().SetSize(800, 600)
            
    # -----------------------------------------------------------------------------
    # VTK code for updating histogram
    # -----------------------------------------------------------------------------
    
    def update_histogram(self, bins):
        '''
        This update_histogram method updates the histogram when invoked.
        This code is similar/equivalent to the update_histogram method in test_app.py.
        >>> From test_app.py:
        >>> @state.change("bins")
        ... def update_histogram(bins, **kwargs):
        ...     bins = int(bins)
        ...     hist, bin_edges = np.histogram(np_data, bins)
        ...     arrX.Reset()
        ...     arrY.Reset()
        ...     for i in range(len(hist)):
        ...         arrX.InsertNextValue(bin_edges[i])
        ...         arrY.InsertNextValue(hist[i])
        ...     table.Modified()
        ...     ctrl.view_update()
        '''
        
        bins = int(bins)
        self.hist, self.bin_edges = np.histogram(self.np_data, bins=bins)
        
        self.arrX.Reset()
        self.arrY.Reset()
        
        for i in range(len(self.hist)):
            self.arrX.InsertNextValue(self.bin_edges[i])
            self.arrY.InsertNextValue(self.hist[i])
            
        self.table.Modified()
        #self.server.view_update() #unsure about this line of code
        self.renderWindow.Render()
        #self.renderWindow = self.view.GetRenderWindow()
        print("Histogram successfully rerendered")
    
    # -----------------------------------------------------------------------------
    # State change handler for updating histogram
    # -----------------------------------------------------------------------------
    
    @change("bins")
    def on_bins_change(self, bins, **kwargs):
        '''
        This on_bins_change method updates the histogram when the bins change.
        It does this by invoking the update_histogram method and using the @change decorator.
        This code is similar/equivalent to the update_histogram method in test_app.py except that it invokes the update_histogram method.
        >>> From test_app.py:
        >>> @state.change("bins")
        ... def update_histogram(bins, **kwargs):
        ...     bins = int(bins)
        ...     hist, bin_edges = np.histogram(np_data, bins)
        ...     arrX.Reset()
        ...     arrY.Reset()
        ...     for i in range(len(hist)):
        ...         arrX.InsertNextValue(bin_edges[i])
        ...         arrY.InsertNextValue(hist[i])
        ...     table.Modified()
        ...     ctrl.view_update()
        '''
        
        self.update_histogram(bins)
        self.client_view.update()
        print("Changed bins to:", bins)
    
        
    # -----------------------------------------------------------------------------
    # State change handler for file input
    # -----------------------------------------------------------------------------
    
    @change("file_input")
    def on_file_input_change(self, file_input, **kwargs):
        '''
        This on_file_input_change method updates the histogram when the file input changes.
        It does this by invoking the update_histogram method and using the @change decorator.
        This code is similar/equivalent to the on_file_input_change method in test_app.py.
        >>> From test_app.py:
        >>> @state.change("file_input")
        ... def on_file_input_change(file_input, **kwargs):
        ...     if file_input:
        ...         try:
        ...              content = file_input['content']
        ...              df = pd.read_csv(BytesIO(content))
        ...              state.column_options = df.columns.tolist()
        ...              state.selected_column = state.column_options[0]
        ...              global np_data
        ...              np_data = df[state.selected_column].values
        ...              update_histogram(state.bins)
        ...     except KeyError as e:
        ...         print(f"KeyError: {e} - Check the structure of file_input and the CSV file.")
        ...     except Exception as e:
        ...         print(f"An error occurred: {e}")
        '''
        
        if file_input:
            print("A file is being uploaded...") #Debugging purposes
            try:
                # Load the CSV data from the 'content' key                
                content = BytesIO(base64.b64decode(file_input['content']))
                df = pd.read_csv(content)
                
                # Update the dropdown options with the DataFrame columns
                self.server.state.column_options = df.columns.tolist()
                print(f"Column options updated: {self.server.state.column_options}") #Debugging purposes
                
                # Send the column options to the client
                # self.server.state.dirty('column_options')
                # print("Column options sent to the client") #Debugging purposes
                
                self.on_column_options_change(self.server.state.column_options)
                
                # TODO: BIG PROBLEM: The client-side is not reciving the updated column_options. The server is updating the column_options correctly but the client is not reciving the updated column_options.
                # TODO: Issue: 1. An error occurred (file_input): 'NoneType' object is not callable.
                # Reason for Issue 1: Unkonwn and not sure how to fix it. Low priority for now as there seem to be another solution to the problem (writing JS code and writing a new state variable).
                # TODO: Need to delete this issue and line of code, it is no longer needed, the main issue is now resolved. 
                # Yes, the solution to the problem is to use the on_column_options_change method (state variable "column_options") and write JavaScript code to update the client side.
                # However, for now I will keep this line of code here just in case I need to refer back to it. I will need to remove the code once in late development or early production.
                
                # Send the column options to the client
                #self.server.state.update_state([
                    #{ "key": "column_options", "value": self.server.state.column_options }
                #])
                
                # Select the first column by default
                self.server.state.selected_column = self.server.state.column_options[0] 
                print(f"Selected column: {self.server.state.selected_column}") #Debugging purposes
                
                # Select the column to use
                self.np_data = df[self.server.state.selected_column].values
                print(f"Data for selected column: {self.np_data}") #Debugging purposes
                
                # Update the histogram with the new data
                self.update_histogram(self.server.state.bins)
                print("Histogram updated") #Debugging purposes
            except KeyError as e:
                print(f"KeyError: {e} - Check the structure of file_input and the CSV file.")
            except Exception as e:
                print(f"An error occurred (file_input): {e}")
                
    # -----------------------------------------------------------------------------
    # State change handler for column_options
    # -----------------------------------------------------------------------------
    
    # TODO: Issue 2. Cannot Control+C to stop the server. The server is not stopping. Not a big issue, closing the terminal window will stop the server. But strange behavior.
    # Issue 2 is temporarily fixed by adding a call_count variable and a condition to stop the on_column_options_change method from being called more than 5 times.
    # Reason for the Issue 2: This method is being called again and again, will run indefinitely, and will not stop, and therefore the Control+C command is not working.
    @change("column_options")
    def on_column_options_change(self, column_options, **kwargs):
        '''
        This on_column_options_change method updates the client side column options, after the server has successfully read the file.
        It does this by invoking using dirty and using a @change decorator.
        >>> from https://trame.readthedocs.io/en/latest/core.state.html:
        ... dirty(*_args):
        ...     Mark existing variable name(s) to be modified in a way that they will be pushed again at flush time.
        '''
        
        # Check if the method has been called more than 5 times
        if self.call_count >= 5:
            print("on_column_options_change has been called 5 times. It will not be called again.")
            return

        self.server.state.column_options = column_options
        self.server.state.dirty('column_options')
        print("Column options sent to the client") #Debugging purposes
        
        self.call_count += 1
                
    # -----------------------------------------------------------------------------
    # State change handler for selected_column
    # -----------------------------------------------------------------------------
    
    @change("selected_column")
    def on_selected_column_change(self, selected_column, **kwargs):
        '''
        This on_selected_column_change method updates the histogram when the selected column changes.
        It does this by invoking the update_histogram method and using the @change decorator.
        This code is similar/equivalent to the on_selected_column_change method in test_app.py.
        >>> From test_app.py:
        >>> @state.change("selected_column")
        ... def on_selected_column_change(selected_column, **kwargs):
        ...     if state.file_input and selected_column:
        ...         try:
        ...             content = state.file_input['content']
        ...             df = pd.read_csv(BytesIO(content))
        ...             global np_data
        ...             np_data = df[selected_column].values
        ...             update_histogram(state.bins)
        ...         except KeyError as e:
        ...             print(f"KeyError: {e} - Check the structure of the CSV file.")
        ...         except Exception as e:
        ...             print(f"An error occurred: {e}")
        '''
        
        if self.server.state.file_input and selected_column:
            try:
                # Load the CSV data from the 'content' key
                content = base64.b64decode(self.server.state.file_input['content'])
                df = pd.read_csv(BytesIO(content))

                # Select the column to use
                self.np_data = df[selected_column].values
                print(f"Data for selected column: {self.np_data}") #Debugging purposes

                # Update the histogram with the new data
                self.update_histogram(self.server.state.bins)
            except KeyError as e:
                print(f"KeyError: {e} - Check the structure of the CSV file.")
            except Exception as e:
                print(f"An error occurred (selected_column): {e}")
                
if __name__ == "__main__":
    histogram_app= HistogramApp()
    #print("Server starting...")
    histogram_app.server.start()

# TODO: Improvement needed but not an issue:
# From the client side, the user needs to click or interact with the application render window for the changes to be applied/changed/reflected/rendered/staged/updated.
# This is pretty annoying, and it should be the job of the client (without user interaction) to automatically update the render window when the server state changes.

# More detail into the needed improvement:
# The server state changes are being detected and the server is updating correctly. Correctly in the sense that the server is detecting the all changes in the state and updating it interactively. 
# This can be seen when the server updates the bin state interactively.
# Interactively: The server captures ALL the bin numbers when the slider is being moved to a new position and not only the final position.
# However, the client is not updating the render window automatically. The user needs to click or interact with the application render window for the changes to be applied/changed/reflected/rendered/staged/updated.

# Suggestions one for the improvement:
# Use the .dirty() method to mark the variable name(s) to be modified in a way that they will be pushed again at flush time.
# This will allow the server to push the changes to the client without the need for user interaction.
# Reason why I believe this will work: 
# From issue 2, the Control+C command is not working because the on_column_options_change method is being called again and again, will run indefinitely, and will not stop.
# Therefore if we use the .dirty() method to continuously push the changes to the client, the client will automatically update the render window without the need for user interaction.
# Edit: Now that I have thought about it more, this might not work because actually the client is not updating the render window automatically. Since the server side is already interactively updating the states, the .dirty method might not work, since it is redundant.
# However, we could try to .dirty the render window and see if that works. But I am not sure if that will work.
# Edit two: No this suggestion does not seem to work as initally thought. It is redundant and not needed. The server is already updating the states interactively. The client is not updating the render window automatically.
# I will keep this here just in case I or somebody else who looks at the code in the future thinks this might work but currently (7/14/2024) it does not seem like it will work.

# Suggestions two for the improvement:
# Rewrite the server code and use the @state.change decorator to update the render window automatically.
# As a sidenote, I rewrote the server this way because of the example given form the repository: https://github.com/Kitware/vtk-web-solutions/blob/master/client-server/trame-server.py (which does not use the @state.change decorator, only the @change decorator).
# The test_app.py was originally written with the @state.change decorator and the server would automatically update the render window without the need for user interaction.
# However, the test_app.py is client+server code and the client code is not written in a separate file. So unsure how it will interact with the vue-client code.
# Therefore this suggestion might take some time to implemenet and test. 
# Reason why I believe this will work:
# Since I know test_app.py automatically updates the render window without the need for user interaction while using the @state.change decorator, and the example code from the repository uses the @state.change decorator, I believe this will work.

# Suggestions three for the improvement:
# Rewrite the client code and tell the client to automatically update the render window when the server state changes.
# Reason why I believe this will work:
# It should work because the server is updating the state correctly and the client is receiving the state changes correctly. The only issue is that the client is not updating the render window automatically.
# This however is not a good suggestion because I am not good and have limited knowledgable/experience with JavaScript and I am not sure how to do this. I am not sure how to tell the client to automatically update the render window when the server state changes.
# This might be a good suggestion for someone who is good with JavaScript, is knowledgeable/experienced with JavaScript, and knows how to do this. But not for me (Huy).