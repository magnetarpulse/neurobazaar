from abc import ABC, abstractmethod
from typing import Optional
import numpy as np
import numpy.typing as npt
from trame.app import get_server

class BaseHistogramApp(ABC):
    """Abstract base class for histogram applications.
    
    Provides a simple framework for creating histogram visualizations with basic
    computation, rendering, and UI capabilities.
    """
    
    def __init__(self, name: str, port: int, np_data: Optional[npt.NDArray] = None) -> None:
        """Initialize the base histogram application.
        
        Args:
            name (str): Name of the application
            port (int): Port number for the server
            np_data (Optional[npt.NDArray]): Initial numpy array data
        """
        self.name = name
        self.port = port
        self.np_data = np_data if np_data is not None else np.random.normal(size=1_000)
        self.server = get_server(name, client_type="vue2")

    @abstractmethod
    def setup_histogram(self, bins: int) -> None:
        """Set up the histogram with the specified number of bins.
        
        Args:
            bins (int): Number of bins for the histogram
        """
        pass

    @abstractmethod
    def update_histogram(self) -> None:
        """Update the histogram with the current data."""
        pass

    @abstractmethod
    def update_the_client_view(self) -> None:
        """Update the client view with the current histogram data."""
        pass

    @abstractmethod
    def setup_layout(self) -> None:
        """Set up the user interface components."""
        pass

    @abstractmethod
    def start_now(self) -> None:
        """Start the server immediately in the main thread."""
        pass

    @abstractmethod
    async def start_later(self) -> None:
        """Start the server asynchronously."""
        pass

    @abstractmethod
    def stop_server(self) -> None:
        """Stop the server and clean up resources."""
        pass