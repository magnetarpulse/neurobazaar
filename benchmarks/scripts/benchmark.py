import os
import sys
import asyncio
import threading
import traceback

def get_neurobazaar_dir() -> str:
    """Returns the neurobazaar directory."""
    cwd = os.getcwd()
    index = cwd.index('neurobazaar')
    return cwd[:index + len('neurobazaar')]

neurobazaar = get_neurobazaar_dir()
sys.path.insert(0, neurobazaar)

from benchmarks.playwright.use_playwright import Runner
from benchmarks.servers.trame_vtk_server import VtkApp
from benchmarks.servers.trame_plotly_server import PlotlyApp
from benchmarks.servers.trame_matplotlib_server import MatplotlibApp

class Benchmark:
    def __init__(self, server : str = "trame_vtk", port: int = 8080, ui_type: str = "slider", 
                 data_size: int = 1_000, number_of_benchmarks: int = 100, benchmark_snaphot: int = 10):
        if data_size < 1:
            raise ValueError("data_size must be greater than 0")
        
        if server not in ["trame_vtk", "trame_plotly", "trame_matplotlib"]:
            raise ValueError("Invalid server. Currently supported servers are: trame_vtk, trame_plotly, and trame_matplotlib"
                             + "Hint: Case sensitive")
        
        if ui_type not in ["slider", "input"]:
            raise ValueError("Invalid ui_type. Currently supported ui_types are: slider, and input"
                             + "Hint: Case sensitive")
        
        self.__server = server
        self.__port = port  

        if self.__server == "trame_vtk":
            self.__data_size = data_size
            self.__ui_type = ui_type 
            self.__run_server = "VTK"
            self.app = VtkApp(data_size=self.__data_size, ui_type=self.__ui_type, port=self.__port)
        elif self.__server == "trame_plotly":
            self.__data_size = data_size
            self.__ui_type = ui_type
            self.__run_server = "Plotly"
            self.app = PlotlyApp(data_size=self.__data_size, ui_type=self.__ui_type, port=self.__port)
        elif self.__server == "trame_matplotlib":
            self.__data_size = data_size
            self.__ui_type = ui_type
            self.__run_server = "Matplotlib"
            self.app = MatplotlibApp(data_size=self.__data_size, ui_type=self.__ui_type, port=self.__port)
        else:
            raise ValueError("Invalid server. Currently supported servers are: trame_vtk, trame_plotly, and trame_matplotlib"
                             + "Hint: Case sensitive")

        # self.__url = f"http://localhost:{self.__port}"
        self.__url = f"https://localhost:{self.__port}?key=a2V5"
        self.__number_of_benchmarks = number_of_benchmarks
        self.__benchmark_snaphot = benchmark_snaphot
        
        divider = "=" * 100
        print(f"\033[1;34m{divider}\033[0m")
        print(f"\033[1;32mInitializing benchmark with:\033[0m")
        print(f"\033[1;33mServer              : {self.__server}\033[0m")
        print(f"\033[1;33mPort                : {self.__port}\033[0m")
        print(f"\033[1;33mURL                 : {self.__url}\033[0m")
        print(f"\033[1;33mNumber of benchmarks: {self.__number_of_benchmarks}\033[0m")
        print(f"\033[1;33mNumber of snapshots : {self.__benchmark_snaphot}\033[0m")
        print(f"\033[1;34m{divider}\033[0m")

        self.runner = Runner(url = self.__url, 
                             server_type = self.__run_server,
                             num_benchmarks = self.__number_of_benchmarks, 
                             snapshots = self.__benchmark_snaphot)
        
        self.server_ready = threading.Event()
        self.benchmark_complete = threading.Event()

    def run_benchmark_thread(self):
        """
        Run the benchmark in a separate thread
        """
        try:
            self.server_ready.wait(timeout=30)
            
            print("\033[1;34mStarting benchmark...\033[0m")  
            self.runner.deploy_runner(ui_type=self.__ui_type)
            print("\033[1;32mBenchmark completed successfully\033[0m")  
        except Exception as e:
            print(f"\033[1;31mBenchmark thread error: {e}\033[0m")  
            traceback.print_exc()
        finally:
            self.benchmark_complete.set()

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def start_server():
                try:
                    await self.app.start_later()
                    print("\033[1;32mServer started successfully\033[0m")  
                    self.server_ready.set()
                except Exception as e:
                    print(f"\033[1;31mServer start error: {e}\033[0m")  
                    traceback.print_exc()

            benchmark_thread = threading.Thread(target=self.run_benchmark_thread)
            benchmark_thread.start()
            loop.run_until_complete(start_server())
            self.benchmark_complete.wait(timeout=300)  

        except Exception as e:
            print(f"\033[1;31mOverall run error: {e}\033[0m")
            traceback.print_exc()
        finally:
            try:
                print("\033[1;34mStopping app server..\033[0m.")
                self.app.stop()
                print("\033[1;32mApp server stopped\033[0m")
            except Exception as e:
                print(f"\033[1;31mApp stop error: {e}\033[0m")
                traceback.print_exc()
            
            print("\033[1;32mBenchmarking process completed\033[0m")

def main():
    benchmark = Benchmark(
        server="trame_plotly", 
        port=8080, 
        ui_type="slider", 
        data_size=1_000_000_000, 
        number_of_benchmarks=100, 
        benchmark_snaphot=10
    )
    benchmark.run()

if __name__ == "__main__":
    main()