import os
import io
import sys
import contextlib
import subprocess
import multiprocessing

def get_neurobazaar_dir() -> str:
    """Returns the neurobazaar directory."""
    cwd = os.getcwd()
    index = cwd.index('neurobazaar')
    return cwd[:index + len('neurobazaar')]

neurobazaar = get_neurobazaar_dir()
sys.path.insert(0, neurobazaar)

from playwright.sync_api import sync_playwright # type: ignore
import numpy as np                              # type: ignore

from benchmarks.utils.logger import ReLogger
from benchmarks.utils.generate_synthetic_dataset import GenerateSyntheticDataset
import json

from typing import List, Optional
import warnings

from datetime import datetime
import time
import random


def run_simulations_wrapper(queue, client_simulator):
    while True:
        command = queue.get()
        if command == "STOP":
            break
        elif command == "RUN":
            client_simulator.run_simulations(headless=True, ignore_https_errors=True)

class Runner:
    """Manages the execution and reporting of server benchmarking processes.

    This class handles the entire benchmarking process, including setup, 
    execution, capturing network requests, simulating user interactions, and 
    generating detailed reports for various server and UI configurations.

    Args:
        url (str): The server endpoint URL where the benchmarking will be performed.
        server_type (str): The rendering backend of the server to benchmark
            (e.g., "VTK", "Plotly", "Matplotlib").
        ui_type (str): The frontend UI element to interact with during the benchmark
            (e.g., "slider", "input_field").
        num_benchmarks (int): Total number of benchmark iterations to run.
        snapshots (int): The threshold before considering the rendering complete. 
            Higher values provide greater confidence that the rendering has completed and is stable, 
                but result in longer runtime and are more resource-intensive. 
            Lower values provide less confidence that the rendering has completed and is stable, 
                but result in shorter runtime and are less resource-intensive.
        payload_threshold (int): Minimum payload size for WebSocket message retention.
        all_messages (bool): Flag to retain all WebSocket messages 
            regardless of payload length.

    Methods:
        deploy_runner(headless: bool = True, ignore_https_errors: bool = True) -> None:
            Initiates the benchmarking runner with specified configuration.
    """
    
    def __init__(self, url: str, server_type: str = "VTK", ui_type: str = "slider", num_benchmarks: int = 100, snapshots: int = 10, payload_threshold: int = 200, all_messages: bool = False) -> None:
        """Initializes the Runner class.

        Args:
            url (str): The URL of the server to benchmark.
            server_type (str, optional): The type of server. Defaults to "VTK". Currently supported: VTK, Plotly, Matplotlib.
            ui_type (str, optional): The type of UI to use. Defaults to "slider". Currently supported: slider, input_field.
            num_benchmarks (int, optional): The number of benchmarks to run. Defaults to 100.
            snapshots (int, optional): The number of DOM (Document Object Model) snapshots to take. Defaults to 10.
            payload_threshold (int, optional): The payload threshold of WebSocket messages to be kept. Default to 200.
                WebSocket messages with a payload length less than this threshold will be ignored unless `all_messages` is set to True.
            all_messages (bool, optional): Whether to keep all WebSocket messages regardless of payload length. Defaults to False.

        Raises:
            ValueError: If the server type is not supported.
        """
        self.url: str = url
        self.__server_type: str = server_type
        self.__ui_type = ui_type

        if ui_type not in ["slider", "input_field"]:
            raise ValueError("Invalid UI type. Currently supported: slider, input_field. Hint: Case sensitive.")

        if server_type not in ["VTK", "Plotly", "Matplotlib"]:
            raise ValueError("Invalid server type. Currently supported: VTK, Plotly, Matplotlib. Hint: Case sensitive.")
        else:
            print(f"Server type: {server_type}")

        if snapshots < 10:
            print("\033[91mWARNING: The number of snapshots is less than 10." + 
                "This may not be enough to ensure stability.\033[0m")
        elif snapshots > 100:
            print("\033[91mWARNING: The number of snapshots is greater than 100. This may be excessive. " +
                "And might slow down the benchmark.\033[0m")

        print(f"Number of snapshots: {snapshots}")
        print(f"Number of benchmarks: {num_benchmarks}")

        if self.__server_type == "VTK":
            self.__JS_SELECTOR: str = ".v-main"
            self.__JS_ELEMENT: str = ".v-main img"
            self.__JS_STATE: str = "__previous_vtk_state"
            self.__REQUEST_TIMES: list = []
            self.__WS_CONTAINER: list = []
            self.__WS_TEXT: list = []
            self.__WS_IS_BINARY: list = []
            self.__WS_TIMESTAMP: list = []
            self.__WS_TIMESTAMP_DIFFERENCES: list = []
            self.__WS_PAYLOAD_LENGTH: list = []
            self.__WS_DATA_LOCK: bool = False
            self.__WS_PAYLOAD_THRESHOLD: int = payload_threshold
            self.__WS_ALL_MESSAGES: bool = all_messages
            self.__STABLE_THRESHOLD: int = snapshots
        elif self.__server_type == "Plotly":
            self.__JS_SELECTOR: str = ".js-plotly-plot"
            self.__JS_ELEMENT: str = ".js-plotly-plot"
            self.__JS_STATE: str = "__previous_plotly_state"
            self.__WS_CONTAINER: list = []
            self.__WS_TEXT: list = []
            self.__WS_IS_BINARY: list = []
            self.__WS_TIMESTAMP: list = []
            self.__WS_TIMESTAMP_DIFFERENCES: list = []
            self.__WS_PAYLOAD_LENGTH: list = []
            self.__WS_DATA_LOCK: bool = False
            self.__WS_PAYLOAD_THRESHOLD: int = payload_threshold
            self.__WS_ALL_MESSAGES: bool = all_messages
            self.__STABLE_THRESHOLD: int = snapshots
        elif self.__server_type == "Matplotlib":
            self.__JS_SELECTOR: str = ".mpld3-figure"
            self.__JS_ELEMENT: str = ".mpld3-figure"
            self.__JS_STATE: str = "__previous_matplotlib_state"
            self.__WS_CONTAINER: list = []
            self.__WS_TEXT: list = []
            self.__WS_IS_BINARY: list = []
            self.__WS_TIMESTAMP: list = []
            self.__WS_TIMESTAMP_DIFFERENCES: list = []
            self.__WS_PAYLOAD_LENGTH: list = []
            self.__WS_DATA_LOCK: bool = False
            self.__WS_PAYLOAD_THRESHOLD: int = payload_threshold
            self.__WS_ALL_MESSAGES: bool = all_messages
            self.__STABLE_THRESHOLD: int = snapshots
        else:
            raise ValueError("Invalid server type. Currently supported: VTK, Plotly, Matplotlib. Hint: Case sensitive.")

        self.num_benchmarks: int = num_benchmarks
        self.__num_benchmarks: int = num_benchmarks + int(1) 

        self.__lock_slider = None
        self.__lock_input_field = None

        self.__lock_stable_threshold: int = self.__STABLE_THRESHOLD * (.7)
        print("Lock Stable Threshold: ", self.__lock_stable_threshold)
        self.__lock_num_benchmarks: int = int(self.__num_benchmarks * self.__lock_stable_threshold)
        print("Lock Number of Benchmarks: ", self.__lock_num_benchmarks)

        self.client_simulator = ClientSimulator(url, ui_type, self.num_benchmarks)
    
    def deploy_runner(self, headless: bool = True, ignore_https_errors: bool = True) -> None:
        """Deploys the runner for benchmarking.

        Args:
            headless (bool, optional): Whether to run the browser in headless mode. Defaults to True.
            ignore_https_errors (bool, optional): Whether to ignore HTTPS errors. Defaults to True.
        """
        render_times: List[float] = []
        detailed_timing_logs: List[str] = []

        print(f"UI Type: {self.__ui_type}")
        print(f"Headless: {headless}")
        print(f"Ignore HTTPS errors: {ignore_https_errors}")
        print(f"Starting benchmark for {self.url}")

        with sync_playwright() as the_browser:
            if headless:
                browser = the_browser.chromium.launch()
            else:
                browser = the_browser.chromium.launch(headless=False)
            
            if ignore_https_errors:
                context = browser.new_context(ignore_https_errors=True)
            else:
                context = browser.new_context(ignore_https_errors=False)
                print("INFO: HTTPS errors are not ignored. This may cause issues depending on the server." +
                    "If you encounter issues, consider setting ignore_https_errors=True.")
                
            page = context.new_page()

            print("Going to the page")
            page.goto(self.url)
            print("Page loaded")

            print("Waiting for the figure to be visible")
            page.wait_for_selector(self.__JS_SELECTOR, timeout=50000)
            print("Figure is visible")

            def slider(page, percentage: int = None, randomize: bool = False) -> None:
                """Simulates the slider movement on the page.

                Args:
                    page: The page object from Playwright.
                    percentage (int): The percentage to move the slider to (0 to 100). Default is None.
                    randomize (bool): If True, randomly select a percentage.

                Raises:
                    AssertionError: If any of the slider elements are not found.
                    Exception: If there is an error during the slider simulation.
                """
                try:
                    if randomize:
                        percentage = random.randint(0, 100)

                    slider_thumb = page.locator(".v-slider__thumb-container")
                    assert slider_thumb is not None, "Slider thumb not found"

                    slider_track = page.locator(".v-slider__track-container")  
                    assert slider_track is not None, "Slider track not found"

                    slider_track_box = slider_track.bounding_box()
                    assert slider_track_box is not None, "Unable to get slider track bounding box"

                    new_position_x = slider_track_box["x"] + slider_track_box["width"] * (percentage / 100)
                    new_position_y = slider_track_box["y"] + slider_track_box["height"] / 2

                    page.mouse.move(new_position_x, new_position_y)

                    if percentage == 0:
                        page.mouse.down()
                    elif percentage == 100:
                        page.mouse.up()
                except Exception as e:
                    print(f"Error simulating slider: {e}")

            def input_field(page, input_value: int = None, randomize: bool = False, increment_value: int = 50) -> None:
                """Simulates typing into an input field on the page.

                Args:
                    page: The page object from Playwright.
                    input_value (int): The integer value to type into the input field. Default is None.
                    randomize (bool): If True, randomly select an integer value between 0 and 1000.

                Raises:
                    AssertionError: If any of the input field elements are not found.
                    Exception: If there is an error during the input simulation.
                """
                try:
                    if randomize:
                        if self.__lock_input_field is None:
                            self.__lock_input_field = random.randint(0, 50)
                            print("Initial input field value: ", self.__lock_input_field)
                        else:
                            self.__lock_input_field += increment_value
                        input_value = self.__lock_input_field

                    input_container = page.locator(".v-input__slot")
                    assert input_container is not None, "Input container not found"

                    input_box = input_container.bounding_box()
                    assert input_box is not None, "Unable to get input container bounding box"

                    click_x = input_box["x"] + input_box["width"] / 2
                    click_y = input_box["y"] + input_box["height"] / 2

                    page.mouse.move(click_x, click_y)
                    
                    page.mouse.down()
                    page.mouse.up()
                    
                    for _ in range(10):
                        page.keyboard.press("Backspace")
                    
                    page.keyboard.type(str(input_value))
                
                except Exception as e:
                    print(f"Error simulating number input: {e}")

            def get_network_requests(page) -> list:
                """Captures network request timings during the benchmark.

                Args:
                    page: The page object from Playwright.

                Returns:
                    list: A list of request times in milliseconds.

                Raises:
                    Exception: If there is an error capturing request timings.
                """
                request_times: list = []
                benchmark_in_progress: bool = True

                def capture_requests(request) -> None:
                    """Captures the timing of a network request.

                    Args:
                        request: The network request object from Playwright.

                    Raises:
                        Exception: If there is an error capturing the request timing.
                    """
                    nonlocal benchmark_in_progress
                    if not benchmark_in_progress:
                        return

                    try:
                        response = request.response()
                        if response:
                            timing = request.timing
                            start_time = timing['startTime']  # Absolute high-precision timestamp
                            end_time = timing['responseEnd']  # Relative time delta, this is what we want to capture.
                            
                            request_time = end_time
                            request_times.append(request_time)
                            
                            # print(f"Request: {request.url}")                # Request URL     
                            # print(f"Start Time (absolute): {start_time}")   # High precision timestamp
                            print(f"Request Duration: {request_time} ms")     # Relative time delta
                    except Exception as e:
                        if benchmark_in_progress:
                            print(f"Error capturing request timing: {e}")

                page.on('request', capture_requests)
                page.goto(self.url)

                for i in range(self.__num_benchmarks):  
                    print(f"Network benchmark {i} of {self.num_benchmarks}")
                    try:
                        if self.__ui_type == "slider":
                            slider(page, randomize=True)
                            time.sleep(0.5) 
                        elif self.__ui_type == "input_field":
                            input_field(page, randomize=True)
                            time.sleep(0.5)
                    except Exception as e:
                        print(f"Error occurred during network benchmark {i}: {e}")
                        break

                page.unroute('*')
                benchmark_in_progress = False

                return request_times

            def get_websocket_details(page) -> None:
                """Captures WebSocket details during the benchmark.

                Args:
                    page: The page object from Playwright.

                Raises:
                    Exception: If there is an error capturing WebSocket details.
                """
                benchmark_in_progress: bool = True

                def capture_websocket(ws) -> None:
                    """Captures WebSocket frames.

                    Args:
                        ws: The WebSocket object from Playwright.

                    Raises:
                        Exception: If there is an error capturing WebSocket frames.
                    """
                    nonlocal benchmark_in_progress
                    
                    def on_framereceived(frame) -> None:
                        """Captures received WebSocket frames.

                        Args:
                            frame: The received WebSocket frame.

                        Raises:
                            Exception: If there is an error capturing the received frame.
                        """
                        if not benchmark_in_progress:
                            return
                        
                        try:
                            is_binary: bool = not hasattr(frame, 'text')
                            payload_length: int = len(frame.text) if hasattr(frame, 'text') else len(frame)
                            
                            self.__WS_CONTAINER.append(frame)
                            self.__WS_TEXT.append(frame.text if hasattr(frame, 'text') else frame)
                            self.__WS_IS_BINARY.append(is_binary)
                            self.__WS_TIMESTAMP.append(time.time())
                            self.__WS_PAYLOAD_LENGTH.append(payload_length)
                        
                        except Exception as e:
                            if benchmark_in_progress:
                                print(f"Error capturing received WebSocket frame: {e}")
                    
                    ws.on('framereceived', on_framereceived)
                    
                    def on_framesent(frame) -> None:
                        """Captures sent WebSocket frames.

                        Args:
                            frame: The sent WebSocket frame.

                        Raises:
                            Exception: If there is an error capturing the sent frame.
                        """
                        if not benchmark_in_progress:
                            return
                        
                        try:
                            is_binary: bool = not hasattr(frame, 'text')
                            payload_length: int = len(frame.text) if hasattr(frame, 'text') else len(frame)
                            
                            self.__WS_CONTAINER.append(frame)
                            self.__WS_TEXT.append(frame.text if hasattr(frame, 'text') else frame)
                            self.__WS_IS_BINARY.append(is_binary)
                            self.__WS_TIMESTAMP.append(time.time())
                            self.__WS_PAYLOAD_LENGTH.append(payload_length)
                        
                        except Exception as e:
                            if benchmark_in_progress:
                                print(f"Error capturing sent WebSocket frame: {e}")
                    
                    ws.on('framesent', on_framesent)

                page.on('websocket', capture_websocket)
                page.goto(self.url)

                for i in range(self.__num_benchmarks):  
                    print(f"WebSocket benchmark {i} of {self.num_benchmarks}")
                    try:
                        if self.__ui_type == "slider":
                            slider(page, randomize=True)
                            time.sleep(0.5) 
                        elif self.__ui_type == "input_field":
                            input_field(page, randomize=True)
                            time.sleep(0.5)
                    except Exception as e:
                        print(f"Error occurred during WebSocket benchmark {i}: {e}")
                        break

                page.unroute('*')
                benchmark_in_progress = False

            def filter_websocket_messages(payload_threshold: int = None, all_messages: bool = None) -> tuple:
                """Filters WebSocket messages based on payload length.

                Args:
                    payload_threshold (int, optional): The minimum payload length to keep. 
                    all_messages (bool, optional): Whether to keep all messages. 

                Returns:
                    tuple: A tuple containing filtered WebSocket containers, texts, binary flags, timestamps, and payload lengths.
                """
                if payload_threshold is not None and all_messages is not None:
                    self.__WS_PAYLOAD_THRESHOLD = payload_threshold
                    self.__WS_ALL_MESSAGES = all_messages

                if self.__WS_PAYLOAD_THRESHOLD < 1:
                    warnings.warn("Payload threshold must be greater than or equal to 1.", UserWarning)
                    user_input = input("\033[91mChoose between keeping all messages or filtering by payload length (all/filter): \033[0m")
                    if user_input.lower() == 'all':
                        self.__WS_ALL_MESSAGES = True
                        self.__WS_PAYLOAD_THRESHOLD = 1
                    elif user_input.lower() == 'filter':
                        self.__WS_ALL_MESSAGES = False
                        self.__WS_PAYLOAD_THRESHOLD = int(input("\033[91mEnter the payload threshold you want: \033[0m"))
                    else:
                        print("\033[91mInvalid choice. Operation aborted.\033[0m")
                        return ()
                
                if self.__WS_ALL_MESSAGES is True and self.__WS_PAYLOAD_THRESHOLD > 1:
                    warnings.warn("Cannot keep all messages and filter by payload length simultaneously.", UserWarning)
                    choice = input("\033[91mChoose between keeping all messages or filtering by payload length (all/filter): \033[0m")
                    if choice.lower() == 'all':
                        self.__WS_ALL_MESSAGES = True
                        self.__WS_PAYLOAD_THRESHOLD = 1
                    elif choice.lower() == 'filter':
                        self.__WS_ALL_MESSAGES = False
                        self.__WS_PAYLOAD_THRESHOLD = int(input("\033[91mEnter the payload threshold you want: \033[0m"))
                    else:
                        print("\033[91mInvalid choice. Operation aborted.\033[0m")
                        return ()

                if self.__WS_ALL_MESSAGES:
                    self.__WS_DATA_LOCK = True

                    return (
                        self.__WS_CONTAINER, 
                        self.__WS_TEXT, 
                        self.__WS_IS_BINARY, 
                        self.__WS_TIMESTAMP, 
                        self.__WS_PAYLOAD_LENGTH
                    )
                
                filtered_mask: list = [pl > self.__WS_PAYLOAD_THRESHOLD for pl in self.__WS_PAYLOAD_LENGTH]
                
                filtered_containers: list = [cont for cont, keep in zip(self.__WS_CONTAINER, filtered_mask) if keep]
                filtered_texts: list = [text for text, keep in zip(self.__WS_TEXT, filtered_mask) if keep]
                filtered_is_binary: list = [binary for binary, keep in zip(self.__WS_IS_BINARY, filtered_mask) if keep]
                filtered_timestamps: list = [ts for ts, keep in zip(self.__WS_TIMESTAMP, filtered_mask) if keep]
                filtered_payload_lengths: list = [pl for pl, keep in zip(self.__WS_PAYLOAD_LENGTH, filtered_mask) if keep]
                
                return (
                    filtered_containers, 
                    filtered_texts, 
                    filtered_is_binary, 
                    filtered_timestamps, 
                    filtered_payload_lengths
                )

            def absolute_time_to_relative_time(timestamps: list) -> list:
                """Converts a list of absolute timestamps to relative timestamps.

                Args:
                    timestamps (list): A list of absolute timestamps.

                Returns:
                    list: A list of relative timestamps, with the first timestamp as the reference point.
                """
                return [ts - timestamps[0] for ts in timestamps]
            
            def calculate_timestamp_differences(timestamps: list) -> list:
                """Calculates the differences between timestamps.

                Args:
                    timestamps (list): A list of timestamps.

                Returns:
                    list: A list of time differences between timestamps.
                """
                if self.__WS_DATA_LOCK:
                    return [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
                else:
                    return [timestamps[i + 2] - timestamps[i] for i in range(0, len(timestamps) - 2, 3)]
            
            def js_function(page) -> tuple:
                """Executes a JavaScript function on the page to track detailed timing and stability, and calculates the render time.

                It sets up detailed timing tracking for the page, including the time between checks, state changes, stability checks, and idle times. 
                It monitors the stability of a specific element on the page and calculates the render time once the element has remained stable for a specified threshold.

                Args:
                    page: The page object from Playwright.

                Returns:
                    tuple: A tuple containing the render time and a detailed log of the timing and stability checks.
                """
                result_handle = page.wait_for_function(
                    f"""
                    () => {{
                        if (!window.__initial_state_checked) {{
                            const element = document.querySelector('{self.__JS_ELEMENT}');
                            if (!element) return false;

                            window.__initial_state = {{
                                innerHTML: element.innerHTML,
                                attributes: Array.from(element.attributes).reduce((acc, attr) => {{
                                    acc[attr.name] = attr.value;
                                    return acc;
                                }}, {{}})
                            }};
                            
                            window.__initial_state_checked = true;
                            window.__first_load = true;
                            return false;
                        }}

                        if (!window.__detailed_timing) {{
                            window.__detailed_timing = {{
                                start_time: performance.now(),
                                check_times: [],
                                prev_check_time: performance.now(),
                                state_change_times: [],
                                stability_check_details: [],
                                idle_times: []
                            }};
                        }}

                        if (!window.__check_count) {{
                            window.__check_count = 0;
                        }}
                        if (!window.__stable_check_count) {{
                            window.__stable_check_count = 0;
                        }}
                        if (!window.__start_time) {{
                            window.__start_time = performance.now();
                        }}
                        if (!window.__stability_check_time) {{
                            window.__stability_check_time = 0;
                        }}
                        
                        const STABLE_THRESHOLD = {self.__STABLE_THRESHOLD};  

                        const current_time = performance.now();
                        const detailed_timing = window.__detailed_timing;

                        if (detailed_timing.prev_end_time) {{
                            const idle_time = current_time - detailed_timing.prev_end_time;
                            detailed_timing.idle_times.push(idle_time);
                        }}

                        const time_since_last_check = current_time - detailed_timing.prev_check_time;
                        detailed_timing.check_times.push(time_since_last_check);
                        detailed_timing.prev_check_time = current_time;

                        window.__check_count += 1;

                        const element = document.querySelector('{self.__JS_ELEMENT}');
                        if (!element) return false;

                        const currentState = {{
                            innerHTML: element.innerHTML,
                            attributes: Array.from(element.attributes).reduce((acc, attr) => {{
                                acc[attr.name] = attr.value;
                                return acc;
                            }}, {{}})
                        }};

                        if (JSON.stringify(window.__initial_state) === JSON.stringify(currentState)) {{
                            detailed_timing.prev_end_time = performance.now();
                            return false;
                        }}

                        const previousState = window['{self.__JS_STATE}'] || null;

                        const stability_check_start = performance.now();

                        let stateChanged = false;
                        if (previousState && JSON.stringify(previousState) !== JSON.stringify(currentState)) {{
                            stateChanged = true;
                            detailed_timing.state_change_times.push(current_time - detailed_timing.start_time);
                        }}

                        if (previousState && JSON.stringify(previousState) === JSON.stringify(currentState)) {{
                            window.__stable_check_count += 1;
                        }} else {{
                            window.__stable_check_count = 0;
                        }}

                        const stability_check_end = performance.now();
                        const stability_check_duration = stability_check_end - stability_check_start;
                        window.__stability_check_time += stability_check_duration;

                        detailed_timing.stability_check_details.push({{
                            check_count: window.__check_count,
                            stable_check_count: window.__stable_check_count,
                            state_changed: stateChanged,
                            check_duration: stability_check_duration
                        }});

                        window['{self.__JS_STATE}'] = currentState;

                        if (window.__stable_check_count >= STABLE_THRESHOLD) {{
                            const end_time = performance.now();
                            
                            const total_render_time = end_time - window.__start_time;
                            const adjusted_render_time = total_render_time - window.__stability_check_time;

                            const log = {{
                                total_render_time,
                                stability_check_time: window.__stability_check_time,
                                adjusted_render_time,
                                detailed_timing: window.__detailed_timing,
                                idle_times: detailed_timing.idle_times
                            }};

                            console.log(JSON.stringify(log, null, 2));

                            const final_render_time = 
                                adjusted_render_time > 0 ? adjusted_render_time : total_render_time;

                            if (window.__first_load) {{
                                if (stateChanged) {{
                                    window.__check_count = 0;
                                    window.__stable_check_count = 0;
                                    window.__start_time = null;
                                    window.__stability_check_time = 0;
                                    window.__detailed_timing = null;
                                }}
                                window.__first_load = false;
                            }} else if (window.__stable_check_count >= STABLE_THRESHOLD) {{
                                window.__check_count = 0;
                                window.__stable_check_count = 0;
                                window.__start_time = null;
                                window.__stability_check_time = 0;
                                window.__detailed_timing = null;
                            }}

                            return {{ final_render_time, log }};
                        }}
                        
                        detailed_timing.prev_end_time = performance.now();
                        return false;
                    }}
                    """,
                    timeout=60000,
                    polling=0.01
                )
                
                result = result_handle.json_value()
                final_render_time = result['final_render_time']
                log = result['log']
                return final_render_time, log

            def report(render_times: list) -> str:
                """Generates a report of network request and render time statistics.

                Args:
                    render_times (list): A list of render times in milliseconds.

                Returns:
                    str: A string containing the formatted report.
                """
                report_output = io.StringIO()
                with contextlib.redirect_stdout(report_output):
                    if self.__server_type == "VTK":
                        self.__REQUEST_TIMES.sort()
                        min_request_time = np.min(self.__REQUEST_TIMES)
                        q1_request_time = np.percentile(self.__REQUEST_TIMES, 25)
                        median_request_time = np.median(self.__REQUEST_TIMES)
                        q3_request_time = np.percentile(self.__REQUEST_TIMES, 75)
                        max_request_time = np.max(self.__REQUEST_TIMES)
                        mean_request_time = np.mean(self.__REQUEST_TIMES)
                        std_dev_request_time = np.std(self.__REQUEST_TIMES)

                        print("\nNetwork Request Statistics:")
                        print(f"Minimum: {min_request_time:.2f} ms")
                        print(f"First Quartile (Q1): {q1_request_time:.2f} ms")
                        print(f"Median (Q2): {median_request_time:.2f} ms")
                        print(f"Third Quartile (Q3): {q3_request_time:.2f} ms")
                        print(f"Maximum: {max_request_time:.2f} ms")
                        print(f"Mean: {mean_request_time:.2f} ms")
                        print(f"Standard Deviation: {std_dev_request_time:.2f} ms")
                        print(f"Full list: {self.__REQUEST_TIMES}")
                    
                    if self.__server_type == "Plotly" or self.__server_type == "Matplotlib" or self.__server_type == "VTK":
                        self.__WS_TIMESTAMP_DIFFERENCES.sort()
                        min_ws_time = np.min(self.__WS_TIMESTAMP_DIFFERENCES)
                        q1_ws_time = np.percentile(self.__WS_TIMESTAMP_DIFFERENCES, 25)
                        median_ws_time = np.median(self.__WS_TIMESTAMP_DIFFERENCES)
                        q3_ws_time = np.percentile(self.__WS_TIMESTAMP_DIFFERENCES, 75)
                        max_ws_time = np.max(self.__WS_TIMESTAMP_DIFFERENCES)
                        mean_ws_time = np.mean(self.__WS_TIMESTAMP_DIFFERENCES)
                        std_dev_ws_time = np.std(self.__WS_TIMESTAMP_DIFFERENCES)

                        print("\nWebSocket Statistics:")
                        print(f"Minimum: {min_ws_time:.2f} ms")
                        print(f"First Quartile (Q1): {q1_ws_time:.2f} ms")
                        print(f"Median (Q2): {median_ws_time:.2f} ms")
                        print(f"Third Quartile (Q3): {q3_ws_time:.2f} ms")
                        print(f"Maximum: {max_ws_time:.2f} ms")
                        print(f"Mean: {mean_ws_time:.2f} ms")
                        print(f"Standard Deviation: {std_dev_ws_time:.2f} ms")
                        print(f"Full list: {self.__WS_TIMESTAMP_DIFFERENCES}")
                              
                    render_times.sort()
                    min_val = np.min(render_times)
                    q1 = np.percentile(render_times, 25)
                    median = np.median(render_times)
                    q3 = np.percentile(render_times, 75)
                    max_val = np.max(render_times)
                    mean = np.mean(render_times)
                    std_dev = np.std(render_times)

                    print("\nRender Time Statistics:")
                    print(f"Minimum: {min_val:.2f} ms")
                    print(f"First Quartile (Q1): {q1:.2f} ms")
                    print(f"Median (Q2): {median:.2f} ms")
                    print(f"Third Quartile (Q3): {q3:.2f} ms")
                    print(f"Maximum: {max_val:.2f} ms")
                    print(f"Mean: {mean:.2f} ms")
                    print(f"Standard Deviation: {std_dev:.2f} ms")
                    print(f"Full list:{render_times}")

                    all_check_times = []
                    all_check_durations = []
                    state_change_times = []

                    for log in detailed_timing_logs:
                        detailed_timing = log.get('detailed_timing', {})
                        all_check_times.extend(detailed_timing.get('check_times', []))
                        state_change_times.extend(detailed_timing.get('state_change_times', []))
                        
                        check_details = [detail['check_duration'] for detail in detailed_timing.get('stability_check_details', [])]
                        all_check_durations.extend(check_details)

                    print("\nCheck Time Diagnostics:")
                    print(f"Average time between checks: {np.mean(all_check_times):.2f} ms")
                    print(f"Max time between checks: {np.max(all_check_times):.2f} ms")
                    print(f"Min time between checks: {np.min(all_check_times):.2f} ms")
                    print(f"Number of checks: {len(all_check_times)}")
                    
                    print("\nStability Check Diagnostics:")
                    print(f"Average stability check duration: {np.mean(all_check_durations):.2f} ms")
                    print(f"Max stability check duration: {np.max(all_check_durations):.2f} ms")
                    
                    print("\nState Change Times:")
                    print(f"Number of state changes: {len(state_change_times)}")
                    print(f"Avg time between state changes: {np.mean(state_change_times):.2f} ms")
                    if state_change_times:
                        print(f"State change times: {state_change_times}")

                return_content = report_output.getvalue()
                return return_content

            if self.__server_type == "VTK":
                print("Starting network benchmark requests")
                requests = get_network_requests(page)
                self.__REQUEST_TIMES = requests
                print("Network benchmark requests complete")

            if self.__server_type == "Plotly" or self.__server_type == "Matplotlib" or self.__server_type == "VTK":
                print("Starting WebSocket benchmark requests")
                websocket_messages = get_websocket_details(page)
                websocket_messages = filter_websocket_messages()  
                _, _, _, timestamps, _ = websocket_messages 
                relative_timestamps = absolute_time_to_relative_time(timestamps)
                timings  = calculate_timestamp_differences(relative_timestamps)
                self.__WS_TIMESTAMP_DIFFERENCES = timings
                average_timings = np.mean(timings)
                # print("Websocket_messages: ", websocket_messages) 
                # print("Timestamps: ", timestamps)
                # print("Relative Timestamps: ", relative_timestamps)
                # print("Timings: ", timings)
                # print("List of timings: ", self.__WS_TIMESTAMP_DIFFERENCES)
                print("Average timings: ", average_timings)
                print("WebSocket benchmark requests complete")

            queue = multiprocessing.Queue()
            interaction_process = multiprocessing.Process(
                target=run_simulations_wrapper,
                args=(queue, self.client_simulator)
            )
            interaction_process.start()
            queue.put("RUN")

            time.sleep(5)
            for i in range(self.__lock_num_benchmarks):  
                print(f"Rendering benchmark {i} of {self.__lock_num_benchmarks}")
                
                try:
                    final_render_time, log = js_function(page)

                    render_times.append(final_render_time)
                    detailed_timing_logs.append(log)
                    print(f"Histogram render time: {final_render_time:.2f} milliseconds")

                except Exception as e:
                    print(f"Error occurred during rendering benchmark {i}: {e}")
                    break
            
            queue.put("STOP")
            interaction_process.join()

            return_content = report(render_times)
            print(return_content)
            # print(log)

            browser.close()

class ClientSimulator:
    """ Simulates a client for benchmarking purposes.
    
    This class simulates a user for benchmarking purposes. It can be used to simulate user interactions.
    It is basically a mock user, but it does not have any real user data or user information. 
    And therefore, not a user, but more of a client. Hence, the name ClientSimulator.

    Args:
        url (str): The server endpoint that the client will interact with during simulations.
        ui_type (str): Specifies the type of UI element to be interacted with (e.g., "slider", "input_field").
        num_simulations (int): Defines the total number of simulation iterations to be executed.

    Methods:
        run_simulations(headless: bool = True, ignore_https_errors: bool = True) -> None:
            Executes the client simulations with the given configuration settings.
    """
    def __init__(self, url: str, ui_type: str = "slider", num_simulations: int = 100) -> None:
        """Initializes the ClientSimulator with the specified parameters.
        
        Args:
            url (str): The URL of the server for the client to interact with.
            ui_type (str, optional): The target interactor to simulate. Defaults to "slider".
            num_simulations (int, optional): The number of simulations to run. Defaults to 100.
        """

        self.url: str = url
        self.ui_type: str = ui_type
        self.num_simulations: int = num_simulations

        self.__lock_slider = None
        self.__lock_input_field = None

    def run_simulations(self, headless: bool = True, ignore_https_errors: bool = True) -> None:
        """Runs the client simulations with the specified configuration.

        Args:
            headless (bool, optional): Whether to run the browser in headless mode. Defaults to True.
            ignore_https_errors (bool, optional): Whether to ignore HTTPS errors. Defaults to True.
        """
        
        with sync_playwright() as the_browser:
            if headless:
                browser = the_browser.chromium.launch()
            else:
                browser = the_browser.chromium.launch(headless=False)
            
            if ignore_https_errors:
                client_browser = browser.new_context(ignore_https_errors=True)
            else:
                client_browser = browser.new_context(ignore_https_errors=False)
                print("\033[94mINFO: HTTPS errors are not ignored. This may cause issues depending on the server." +
                    " If you encounter issues, consider setting ignore_https_errors=True.\033[0m")
                
            client_page = client_browser.new_page()

            print("Client is going to the page")
            client_page.goto(self.url)
            print("Client has successfully loaded the page")

            print("Start running simulations")
            for i in range(self.num_simulations):
                if self.ui_type == "slider":
                    print(f"Running slider simulation {i + 1} of {self.num_simulations}")
                    self._simulate_slider(client_page, percentage=None, randomize=True)
                    time.sleep(0.5)
                elif self.ui_type == "input_field":
                    print(f"Running input field simulation {i + 1} of {self.num_simulations}")
                    self._simulate_input_field(client_page, input_value=None, randomize=True)
                    time.sleep(0.5)

    def _simulate_slider(self, client_page, percentage: int = None, randomize: bool = False) -> None:
        """Simulates the slider interaction.
        
        Args:
            client_page: The page object from Playwright.
            percentage (int): The percentage to move the slider to (0 to 100). Default is None.
            randomize (bool): If True, randomly select a percentage.

        Raises:
            AssertionError: If any of the slider elements are not found.
            Exception: If there is an error during the slider simulation.
        """
        if randomize:
            percentage = random.randint(0, 100)
            print(f"Random percentage: {percentage}")

        slider_thumb = client_page.locator(".v-slider__thumb-container")
        assert slider_thumb is not None, "Slider thumb not found"

        slider_track = client_page.locator(".v-slider__track-container")  
        assert slider_track is not None, "Slider track not found"

        slider_track_box = slider_track.bounding_box()
        assert slider_track_box is not None, "Unable to get slider track bounding box"

        slider_track_box = slider_track.bounding_box()
        assert slider_track_box is not None, "Unable to get slider track bounding box"

        new_position_x = slider_track_box["x"] + slider_track_box["width"] * (percentage / 100)
        new_position_y = slider_track_box["y"] + slider_track_box["height"] / 2

        client_page.mouse.move(new_position_x, new_position_y)

        if percentage == 0:
            client_page.mouse.down()
        elif percentage == 100:
            client_page.mouse.up()
        
    def _simulate_input_field(self, client_page, input_value: int = None, randomize: bool = False, increment_value: int = 50) -> None:
        """Simulates typing into an input field on the page.

        Args:
            client_page: The page object from Playwright.
            input_value (int): The integer value to type into the input field. Default is None.
            randomize (bool): If True, randomly select an integer value between 0 and 1000.

        Raises:
            AssertionError: If any of the input field elements are not found.
            Exception: If there is an error during the input simulation.
        """
        try:
            if randomize:
                if self.__lock_input_field is None:
                    self.__lock_input_field = random.randint(0, 50)
                else:
                    self.__lock_input_field += increment_value
                input_value = self.__lock_input_field

            input_container = client_page.locator(".v-input__slot")
            assert input_container is not None, "Input container not found"

            input_box = input_container.bounding_box()
            assert input_box is not None, "Unable to get input container bounding box"

            click_x = input_box["x"] + input_box["width"] / 2
            click_y = input_box["y"] + input_box["height"] / 2

            client_page.mouse.move(click_x, click_y)
            
            client_page.mouse.down()
            client_page.mouse.up()
            
            for _ in range(10):
                client_page.keyboard.press("Backspace")
            
            client_page.keyboard.type(str(input_value))
            
        except Exception as e:
            print(f"Error simulating number input: {e}")

class DjangoUserSimulator:
    def __init__(self) -> None:
        pass

class SimulatorUtils:
    def __init__(self, log_dir: str = 'logs', log_dir_path: str = '.') -> None:
        """
        Initializes the SimulatorUtils class with default log directory and path.

        Args:
            log_dir (str): The name of the log directory. Default is 'logs'.
            log_dir_path (str): The path to the log directory. Default is current directory.
        """
        self.log_dir = log_dir
        self.log_dir_path = log_dir_path
        self.full_log_dir_path = os.path.join(self.log_dir_path, self.log_dir)
        os.makedirs(self.full_log_dir_path, exist_ok=True)

        self.throughput: float = 0
        self.csv_generator = GenerateSyntheticDataset(dir_path='/home/huy/neurobazaar/benchmarks/playwright/logs',file_name='synthetic_dataset.csv')

    def run_iperf3_client(self, server_ip: str, port: int, duration: int, num_streams: int, log_file_path: Optional[str] = None) -> None:
        """
        Runs the iperf3 client to measure network performance and bandwidth.

        Args:
            server_ip (str): The IP address of the server to connect to.
            port (int): The port number to connect to.
            duration (int): The duration of the test in seconds.
            num_streams (int): The number of parallel streams to use.
            log_file_path (Optional[str]): The path to the log file. Default is None, which uses the class attribute.
        """
        if log_file_path is None:
            log_file_path = os.path.join(self.full_log_dir_path, 'iperf3_log.log')

        command = [
            'iperf3',
            '--client', server_ip,
            '--port', str(port),
            '--time', str(duration),
            '--parallel', str(num_streams),
            '--json'
        ]
        
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            log_output = json.loads(result.stdout)
        else:
            log_output = f"Error: {result.stderr}"
            terminal_output = f"\033[91mError: {result.stderr}\033[0m"  
            hint_and_firewall = (
                f"\033[94mHint: Make sure the server is running and accessible at {server_ip}:{port}.\n"
                f"Ensure the firewall allows incoming connections on the specified port.\033[0m"
            )

        start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with open(log_file_path, 'a') as log_file:
            log_file.write(f"Start Time: {start_time}\n")
            log_file.write(json.dumps(log_output, indent=4) if isinstance(log_output, dict) else log_output)
            log_file.write(f"\nEnd Time: {end_time}\n\n")

        if isinstance(log_output, dict):
            bits_per_second = log_output.get('end', {}).get('sum_sent', {}).get('bits_per_second', 'N/A')
            if bits_per_second != 'N/A':
                mbits_per_second = bits_per_second / 1_000_000
                print(f"\033[92mLog file path: {log_file_path}\033[0m")
                print(f"\033[92mThroughput: {mbits_per_second:.2f} Mbits/second\033[0m")
            else:
                print(f"\033[92mLog file path: {log_file_path}\033[0m")
                print("\033[91mThroughput: N/A\033[0m")
        else:
            print(terminal_output)
            print(f"{hint_and_firewall}")

    def generate_synthetic_dataset(self, throughput: float = 0, stop_benchmark: int = 300, variance: int = 1.35,) -> None:
        if throughput == 0:
            print("\033[91mThroughput was not provided.\033[0m")
            while True:
                choice = input("\033[94mDo you want to use the throughput from the last iperf3 test (\033[92my\033[94m/\033[91mn\033[94m)? \033[0m")
                if choice.lower() == 'y':
                    if self.throughput == 0:
                        print("\033[91mThe last iperf3 test throughput is 0 Mbits/s. Please provide a valid throughput value.\033[0m")
                        choice = 'n'  
                    else:
                        throughput = self.throughput
                        break
                if choice.lower() == 'n':
                    while True:
                        user_input = input("\033[94mPlease provide the throughput value (Mbits/s): \033[0m")
                        try:
                            throughput = float(user_input)
                            if throughput == 0:
                                print("\033[91m0 Mbits/s throughput is impossible. Please provide a valid throughput value.\033[0m")
                                continue
                            break
                        except ValueError:
                            print("\033[91mInvalid input. Please enter a numeric value.\033[0m")
                    break
                else:
                    print("\033[91mInvalid choice. Please enter \033[94m'\033[92my\033[94m'\033[91m or \033[94m'\033[91mn\033[94m'\033[91m.\033[0m")

        if stop_benchmark == 0:
            print("\033[91mStop benchmark cannot be 0.\033[0m")
            while True:
                user_input = input("\033[94mPlease provide a valid stop benchmark value (in seconds): \033[0m")
                try:
                    stop_benchmark = int(user_input)
                    if stop_benchmark == 0:
                        print("\033[91mStop benchmark cannot be 0. Please provide a valid integer value.\033[0m")
                        continue
                    break
                except ValueError:
                    print("\033[91mInvalid input. Please enter an integer value.\033[0m")

        if variance <= 1:
            while True:
                try:
                    variance = float(input("\033[94mRe-enter the variance value: \033[0m"))
                    if variance <= 0:
                        print("\033[91mVariance cannot be 0 or negative. Please input a valid value.\033[0m")
                        continue
                    
                    if variance < 1:
                        print("\033[91mWARNING: Variance is set to less than 1. This is not recommended.\033[0m")
                        while True:
                            confirm = input("\033[94mDo you want to change it (\033[92my\033[94m/\033[91mn\033[94m)? \033[0m")
                            if confirm.lower() == 'y':
                                break
                            elif confirm.lower() == 'n':
                                print(f"\033[94mVariance has been successfully set to {variance}.\033[0m")
                                break
                            else:
                                print("\033[91mInvalid choice. Please enter \033[94m'\033[92my\033[94m'\033[91m or \033[94m'\033[91mn\033[94m'\033[91m.\033[0m")
                        continue  
                    
                    if variance == 1:
                        print("\033[91mWARNING: Variance is set to 1. This is optimistic and may not reflect real-world conditions.\033[0m")
                        while True:
                            confirm = input("\033[94mDo you want to change it (\033[92my\033[94m/\033[91mn\033[94m)? \033[0m")
                            if confirm.lower() == 'y':
                                break
                            elif confirm.lower() == 'n':
                                print(f"\033[94mVariance has been successfully set to {variance}.\033[0m")
                                break
                            else:
                                print("\033[91mInvalid choice. Please enter \033[94m'\033[92my\033[94m'\033[91m or \033[94m'\033[91mn\033[94m'\033[91m.\033[0m")
                        continue  
                    
                    print(f"\033[94mVariance has been successfully set to {variance}.\033[0m")
                    break

                except ValueError:
                    print("\033[91mInvalid input. Please enter a numeric value.\033[0m")
        
        dataset_size = throughput * stop_benchmark * variance 

        bit_size = dataset_size * 1_000_000
        byte_size = dataset_size * 1_000_000 / 8
        
        self.csv_generator.generate(byte_size=byte_size, bit_size=bit_size)


def main():
    url = "https://localhost:8080?key=a2V5"

    plotly = "Plotly"
    vtk = "VTK"
    matplotlib = "Matplotlib"
    num_benchmarks = 20
    threshold = 10

    slider = "slider"
    input_field = "input_field"
    headless = True
    ignore_https_errors = True

    relative_path = os.path.dirname(__file__)
    dir_path = relative_path + "/results/client"

    logging_statistics = ReLogger(log_file="delete.log", create_dir=dir_path)
    logging_statistics.run()

    # client = ClientSimulator(url, ui_type=input_field, num_simulations=num_benchmarks)
    # client.run_simulations(headless=headless, ignore_https_errors=ignore_https_errors)

    runner = Runner(url, server_type=vtk, ui_type=input_field, num_benchmarks=num_benchmarks, snapshots=threshold, payload_threshold=1, all_messages=True)
    runner.deploy_runner(headless=headless, ignore_https_errors=ignore_https_errors)

    logging_statistics.stop()

if __name__ == "__main__":
    test_utils = SimulatorUtils()
    # iperf3_test = test_utils.run_iperf3_client(server_ip = "129.114.108.40", port = 5201, duration = 10, num_streams = 1)
    generator_test = test_utils.generate_synthetic_dataset(throughput = 29, stop_benchmark = 500, variance = 1)