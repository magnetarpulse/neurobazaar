import vtk as standard_vtk
from typing import List

class HistogramVTKRenderer:
    """
    A class to render histograms using VTK (Visualization Toolkit).

    **Attributes**:
        - **hist** (List[float]): A list of histogram frequencies.
        - **bin_edges** (List[float]): A list of bin edges for the histogram.
        - **table** (standard_vtk.vtkTable): The VTK table to hold the histogram data.
        - **arrX** (standard_vtk.vtkFloatArray): The VTK array for the X-axis values.
        - **arrY** (standard_vtk.vtkFloatArray): The VTK array for the Y-axis values.
        - **plot** (standard_vtk.vtkPlotBar): The VTK bar plot for the histogram.
        - **chart** (standard_vtk.vtkChartXY): The VTK chart to display the histogram.
        - **view** (standard_vtk.vtkContextView): The VTK context view for rendering.
        - **renderWindow** (standard_vtk.vtkRenderWindow): The render window for the view.
    """

    def __init__(self, hist: List[float], bin_edges: List[float]):
        """
        Initializes the HistogramVTKRenderer with histogram data and bin edges.

        **Args**:
            - **hist** (List[float]): A list of histogram frequencies.
            - **bin_edges** (List[float]): A list of bin edges for the histogram.
        """
        self.hist = hist
        self.bin_edges = bin_edges
        self.table = None
        self.arrX = None
        self.arrY = None
        self.plot = None
        self.chart = None
        self.view = None
        self.renderWindow = None

    def setup_table(self) -> None:
        """
        Sets up the VTK table and populates it with the histogram data.
        """
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

    def setup_plot(self) -> None:
        """
        Configures the VTK bar plot for the histogram.
        """
        self.plot = standard_vtk.vtkPlotBar()
        self.plot.SetInputData(self.table)
        self.plot.SetInputArray(0, "X Axis")
        self.plot.SetInputArray(1, "Frequency")
        self.plot.SetColor(0, 0, 0, 255)
        
        outline = standard_vtk.vtkPen()
        outline.SetColor(255, 255, 255, 255)
        self.plot.SetPen(outline)

    def setup_chart(self) -> None:
        """
        Configures the VTK chart and its properties for the histogram.
        """
        self.chart = standard_vtk.vtkChartXY()
        self.chart.SetBarWidthFraction(1.0)
        self.chart.GetAxis(0).SetTitle("Frequency")
        self.chart.GetAxis(1).SetTitle("Feature")
        self.chart.GetAxis(1).SetMinimum(0)
        self.chart.GetAxis(1).SetMaximum(7000)
        self.chart.GetAxis(1).SetBehavior(standard_vtk.vtkAxis.FIXED)
        self.chart.AddPlot(self.plot)

    def setup_view(self) -> None:
        """
        Configures the VTK context view for rendering the histogram.
        """
        self.view = standard_vtk.vtkContextView()
        self.view.GetScene().AddItem(self.chart)

        self.renderWindow = self.view.GetRenderWindow()
        self.view.GetRenderWindow().SetSize(800, 600)

    def render_histogram(self) -> None:
        """
        Renders the histogram by setting up the table, plot, chart, and view.
        """
        self.setup_table()
        self.setup_plot()
        self.setup_chart()
        self.setup_view()