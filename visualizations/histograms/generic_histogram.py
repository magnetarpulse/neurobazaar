import os
import sys
from typing import List, Optional, Set, Any
import time

def get_neurobazaar_dir() -> str:
    """Returns the neurobazaar directory."""
    cwd = os.getcwd()
    index = cwd.index('neurobazaar')
    return cwd[:index + len('neurobazaar')]

neurobazaar = get_neurobazaar_dir()
sys.path.insert(0, neurobazaar)

from trame.app import get_server
from trame.decorators import TrameApp, change
from trame.widgets import vtk, vuetify
from trame.ui.vuetify import SinglePageLayout

from visualizations.histograms.backends.asbtract_histogram import BaseHistogramApp
from visualizations.histograms.backends.computing.boost_histogram_processor import BoostHistogramProcessor
from visualizations.histograms.backends.rendering.vtk.vtk_renderer import HistogramVTKRenderer
from visualizations.histograms.backends.utils.dask_utils import DaskUtils
from visualizations.histograms.backends.utils.numpy_utils import NumpyUtils
from visualizations.histograms.backends.computing.csv.localfs_watcher import LocalFSDataConverter
from neurobazaar.services.datastorage.localfs_datastore import LocalFSDatastore
from home.models import Files
from queue import Queue
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import numpy.typing as npt

def test():
    files = Files.objects.all()
    print(files)

@TrameApp()
class GenericHistogramApp(BaseHistogramApp):    
    """A generic histogram application using VTK for visualization and Trame for the web interface.
    
    This class provides functionality to create and display interactive histograms from numerical data,
    with support for real-time file watching and dynamic updates.
    
    Attributes:
        server (trame_server.core.Server): The Trame server instance for web interface.
        port (int): The port number for the server.
        neurobazaar_dir (str): Directory path for neurobazaar data.
        histogram_renderer (HistogramVTKRenderer): VTK renderer for histogram visualization.
        boost_histogram_processor (BoostHistogramProcessor): Processor for histogram computations.
        dask_utils (DaskUtils): Utility class for Dask operations.
        numpy_utils (NumpyUtils): Utility class for NumPy operations.
        executor (ThreadPoolExecutor): Thread pool executor for parallel processing.
        loop (asyncio.AbstractEventLoop): Asynchronous event loop for async operations.
        np_data (npt.NDArray): NumPy array containing the data to visualize.
        dask_data (dask.array.Array): Dask array for distributed computing.
        data_min (Optional[float]): Minimum value in the dataset.
        data_max (Optional[float]): Maximum value in the dataset.
        data_changed (bool): Flag indicating if data has been modified.
        state_update_queue (Queue): Queue for managing state updates.
        state_lock (threading.Lock): Threading lock for state modifications.
    """

    def __init__(self, name: str, port: int, np_data: Optional[npt.NDArray] = None) -> None:
        """Initialize the GenericHistogramApp.
        
        Args:
            name (str): Name of the application.
            port (int): Port number for the server.
            np_data (Optional[npt.NDArray]): Optional initial numpy array data. If None, generates 
                random normal data.
        """
        self.server = get_server(name, client_type="vue2")
        self.port: int = port
        self.neurobazaar_dir: str = get_neurobazaar_dir()
        self.histogram_renderer: HistogramVTKRenderer = HistogramVTKRenderer(hist=[], bin_edges=[])
        self.boost_histogram_processor: BoostHistogramProcessor = BoostHistogramProcessor()
        self.dask_utils: DaskUtils = DaskUtils()
        self.numpy_utils: NumpyUtils = NumpyUtils()

        self.executor:ThreadPoolExecutor = ThreadPoolExecutor(max_workers=4)
        
        self.loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.np_data: npt.NDArray = np_data if np_data is not None else np.random.normal(size=1_000)
        self.dask_data: Any = self.dask_utils.create_empty_array(shape=(0,))
        
        self.server.state.bins: int = 5                          # type: ignore
        self.server.state.file_input: Optional[str] = None       # type: ignore
        self.server.state.selected_column: Optional[str] = None  # type: ignore
        self.server.state.column_options: List[str] = []         # type: ignore
        self.server.state.dataset_names: List[str] = []          # type: ignore

        self.data_min: Optional[float] = None
        self.data_max: Optional[float] = None
        self.data_changed: bool = True

        self.state_update_queue: Queue = Queue()
        self.state_lock: threading.Lock = threading.Lock()

        self.state_update_thread: threading.Thread = threading.Thread(
            target=self._process_state_updates, 
            daemon=True
        )
        self.state_update_thread.start()
        
        self.setup_histogram() 

        self.client_view = vtk.VtkRemoteView(
            self.histogram_renderer.renderWindow, 
            trame_server=self.server, 
            ref="view"
        )

        self.setup_layout()
        self._setup_file_watcher()
        self._start_file_watcher()

    def setup_histogram(self) -> None:
        """Set up the initial histogram using the current data and bin settings.
        
        Sets up the histogram renderer with computed histogram data using the current
        dask_data and bin settings from the server state.
        """
        self.hist, self.bin_edges = self.boost_histogram_processor.compute_histogram(
            self.dask_data, 
            self.server.state.bins
        )

        self.histogram_renderer.hist = self.hist
        self.histogram_renderer.bin_edges = self.bin_edges
        self.histogram_renderer.render_histogram()

    def update_histogram(self, bins: int) -> None:
        """Update the histogram with new bin settings and render it.

        This method updates both the histogram computation and the visual
        representation in the VTK renderer.
        
        Args:
            bins (int): Number of bins for the histogram.
        """
        init_time = time.time()

        bins = int(bins)

        if self.data_changed:
            self.dask_data = self.dask_utils.to_dask_array(self.np_data)
            self.data_changed = False

        self.hist, self.bin_edges = self.boost_histogram_processor.compute_histogram(
            self.np_data, 
            bins
        )

        self.histogram_renderer.arrX.Reset()
        self.histogram_renderer.arrY.Reset()
        for i in range(len(self.hist)):
            self.histogram_renderer.arrX.InsertNextValue(self.bin_edges[i])
            self.histogram_renderer.arrY.InsertNextValue(self.hist[i])

        self.update_the_client_view()

        final_time = time.time()

        print(f"Time to update histogram: {final_time - init_time} seconds")

    def update_the_client_view(self) -> None:
        """Update the client-side view with the current render window state.
        
        Triggers a refresh of the VTK remote view to reflect any changes
        in the visualization.
        """
        self.client_view.update()   

    @change("bins")
    def on_bins_change(self, bins: int, **trame_scripts: Any) -> None:
        """Handle changes to the number of histogram bins.
        
        Args:
            bins (int): New number of bins for the histogram.
            **trame_scripts (Any): Additional Trame script arguments passed by the decorator.
        """
        self.update_histogram(bins)

    @change("column_options")
    def on_column_options_change(self, column_options: List[str], **trame_scripts: Any) -> None:
        """Handle changes to the available column options.
        
        Args:
            column_options (List[str]): List of available column names.
            **trame_scripts (Any): Additional Trame script arguments passed by the decorator.
        """
        self.server.state.column_options = column_options

    @change("selected_column")
    def on_selected_column_change(self, selected_column: str, **trame_scripts: Any) -> None:
        """Handle changes to the selected column.
        
        Args:
            selected_column (str): Name of the selected column in the dataset.
            **trame_scripts (Any): Additional Trame script arguments passed by the decorator.
        """
        self.data_min = None
        self.data_max = None
        self.data_changed = True
        if self.server.state.selected_column and selected_column:
            try:
                self.np_data = self.dask_utils.compute_values(
                    self.computed_df[self.server.state.selected_column]
                )
                self.update_histogram(self.server.state.bins)
                    
            except KeyError as e:
                print(f"KeyError: {e} - Check the structure of the CSV file.")
            except Exception as e:
                print(f"An error occurred (selected_column): {e}")

    def _process_state_updates(self) -> None:
        """Process state updates from the queue in a separate thread.
        
        Continuously processes update functions from the queue and executes them
        in a thread-safe manner. Handles any exceptions that occur during processing.
        """
        asyncio.set_event_loop(self.loop)

        while True:
            try:
                update_func = self.state_update_queue.get()
                if update_func:
                    if asyncio.iscoroutinefunction(update_func):
                        self.loop.run_until_complete(update_func())
                    else:
                        update_func()
                self.state_update_queue.task_done()
            except Exception as e:
                print(f"Error processing state update: {str(e)}")

    def _safe_update_state(self, update_func: callable) -> None:
        """Safely update state through the state update queue.
        
        Args:
            update_func (callable): Callback function to update the state in a thread-safe manner.
        """
        self.state_update_queue.put(update_func)

    def _setup_file_watcher(self) -> None:
        """Set up the file watcher components.
        
        Initializes the datastore, file converter, and processing queue for
        watching file system changes.
        """
        datastore_dir = os.path.join(self.neurobazaar_dir, 'datastore')
        self.datastore = LocalFSDatastore(storeDirPath=datastore_dir)
        self.converter = LocalFSDataConverter(self.datastore)
        
        self.processing_queue: Queue = Queue()
        self._processed_files: Set[str] = set()

    def _start_file_watcher(self) -> None:
        """Start the file watcher in separate threads.
        
        Launches two daemon threads:
            - One for watching file system changes
            - One for processing the file queue
        """
        self.watcher_thread = threading.Thread(target=self._watch_files, daemon=True)
        self.watcher_thread.start()
        
        self.processing_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.processing_thread.start()

    def _watch_files(self) -> None:
        """Watch for new files and add them to processing queue.
        
        Continuously monitors the file system for changes and updates the
        application state when new files are detected.
        """
        self.converter.start_watching()
        
        names, _ = self.converter.convert_existing_files()

        def update_initial_state() -> None:
            with self.state_lock:
                self.server.state.dataset_names = names
                if names and not self.server.state.selected_dataset:
                    self.server.state.selected_dataset = names[0]
                    
        self._safe_update_state(update_initial_state)
        
        try:
            while True:
                time.sleep(1) 
                
                new_names, _ = self.converter.convert_existing_files()
                if set(new_names) != set(self.server.state.dataset_names or []):
                    def update_new_files_state() -> None:
                        with self.state_lock:
                            current_names = list(self.server.state.dataset_names or [])
                            for name in new_names:
                                if name not in current_names:
                                    current_names.append(name)
                            self.server.state.dataset_names = current_names
                            
                    self._safe_update_state(update_new_files_state)
                    
        except Exception as e:
            print(f"Error in file watcher: {str(e)}")

    def _process_queue(self) -> None:
        """Process files from the queue and update the visualization.
        
        Continuously processes files from the queue, converts them, and updates
        the application state accordingly.
        
        Raises:
            Exception: If an error occurs during file processing.
        """
        while True:
            try:
                uuid = self.processing_queue.get()
                if uuid not in self._processed_files:
                    result = self.converter._convert_file(uuid)
                    if result:
                        name, _ = result
                        self._processed_files.add(uuid)
                        
                        def update_state() -> None:
                            with self.state_lock:
                                current_names = list(self.server.state.dataset_names or [])
                                if name not in current_names:
                                    current_names.append(name)
                                    self.server.state.dataset_names = current_names
        
                                    if len(current_names) == 1:
                                        self.server.state.selected_dataset = name
                                        
                        self._safe_update_state(update_state)
                        
                self.processing_queue.task_done()
            except Exception as e:
                print(f"Error processing file: {str(e)}")

    @change("selected_dataset")
    def compute_dataset(self, selected_dataset: str, **trame_scripts: Any) -> None:
        """Compute statistics for the selected dataset.
        
        Args:
            selected_dataset (str): Name of the selected dataset to compute.
            **trame_scripts (Any): Additional Trame script arguments passed by the decorator.
            
        Raises:
            Exception: If an error occurs while computing the dataset statistics.
        """
        if selected_dataset is None:
            return 
            
        def update_computed_dataset() -> None:
            with self.state_lock:
                try:
                    csv_file_path = os.path.join(
                        self.datastore._datasets_dir, 
                        f"{selected_dataset}.csv"
                    )
                    
                    if not os.path.exists(csv_file_path):
                        print(f"Dataset file not found: {csv_file_path}")
                        return
                    
                    df = self.dask_utils.read_csv(csv_file_path, assume_missing=True)
                    self.computed_df = df

                    self.server.state.column_options = self.computed_df.columns.tolist()
                    if self.server.state.column_options:
                        self.server.state.selected_column = self.server.state.column_options[0]
                        
                        selected_column_data = self.dask_utils.compute_values(
                            self.computed_df[self.server.state.selected_column]
                        )

                        self.np_data = selected_column_data
                        self.data_min = None
                        self.data_max = None
                        self.data_changed = True
                        self.update_histogram(self.server.state.bins)
                        
                except Exception as e:
                    print(f"An error occurred while computing the dataset:\n{e}")
                    
        self._safe_update_state(update_computed_dataset)

    async def _async_compute_dataset(self, selected_dataset: str) -> None:
        """Async version of dataset computation."""
        with self.state_lock:
            try:
                csv_file_path = os.path.join(
                    self.datastore._datasets_dir, 
                    f"{selected_dataset}.csv"
                )
                
                if not os.path.exists(csv_file_path):
                    print(f"Dataset file not found: {csv_file_path}")
                    return
                
                df = await self.loop.run_in_executor(
                    self.executor, 
                    self.dask_utils.read_csv, 
                    csv_file_path, 
                    True
                )
                self.computed_df = df

                self.server.state.column_options = self.computed_df.columns.tolist()
                if self.server.state.column_options:
                    self.server.state.selected_column = self.server.state.column_options[0]
                    
                    selected_column_data = await self.loop.run_in_executor(
                        self.executor,
                        self.dask_utils.compute_values,
                        self.computed_df[self.server.state.selected_column]
                    )

                    self.np_data = selected_column_data
                    self.data_min = None
                    self.data_max = None
                    self.data_changed = True
                    self.update_histogram(self.server.state.bins)
                    
            except Exception as e:
                print(f"An error occurred while computing the dataset:\n{e}")

    def setup_layout(self) -> None:
        """Set up the UI layout using Vuetify components."""
        with SinglePageLayout(self.server) as layout:
            layout.title.set_text(self.server.name)

            with layout.toolbar:
                vuetify.VSpacer()
                vuetify.VSlider(
                    v_model=("bins", 5), 
                    min=1,
                    max=100,
                    label="Number of Bins",  
                    hide_details=False,
                    dense=True,
                    thumb_label=True,  
                    thumb_size=20, 
                    style="padding-top: 20px;", 
                )
                vuetify.VSelect(
                    v_model=("selected_dataset", None),
                    items=("dataset_names",),
                    label="Select Datasets",
                    style="padding-top: 20px;", 
                )
                vuetify.VSelect(
                    v_model=("selected_column", None),
                    items=("column_options",),
                    label="Select Columns",
                    style="padding-top: 20px;", 
                )

            with layout.content:
                with vuetify.VContainer(
                    fluid=True,
                    classes="pa-0 fill-height", 
                ):
                    self.client_view = vtk.VtkRemoteView(
                        self.histogram_renderer.renderWindow, 
                        trame_server=self.server, 
                        ref="view"
                    )

    def start_now(self) -> None:
        """Start a new server instance immediately.
        
        This method is not intended for use in a multi-process environment.
        """
        print(f"Starting {self.server.name} immediately at http://localhost:{self.port}/index.html")
        self.server.start(exec_mode="main", port=self.port, auth_key="key")
    
    async def start_later(self) -> None:
        """Start a new server instance asynchronously.
        
        This method is intended for use in a multi-process environment.
        """
        print(f"Starting {self.server.name} asynchronously at http://localhost:{self.port}/index.html")
        await self.server.start(exec_mode="task", port=self.port, auth_key="key")

    def stop_server(self) -> None:
        """Stop the server instance."""
        self.server.stop()
    
if __name__ == "__main__":
    # app = GenericHistogramApp("Histogram", 8080)
    # app.start_now()
    test()