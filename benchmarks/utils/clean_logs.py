import os
import sys
import re
import statistics
import inspect

def get_neurobazaar_dir() -> str:
    """Returns the neurobazaar directory."""
    cwd = os.getcwd()
    index = cwd.index('neurobazaar')
    return cwd[:index + len('neurobazaar')]

neurobazaar = get_neurobazaar_dir()
sys.path.insert(0, neurobazaar)

class ServerLogCleaner:
    def __init__(self, path, client_side_rendering=False):
        if not os.path.isfile(path):
            raise FileNotFoundError(f"The file '{path}' does not exist.")
        
        self.original_log = path
        self.client_side_rendering = client_side_rendering
        self.cleaned_log = self._create_cleaned_log()

    def _create_cleaned_log(self):
        dir_name, file_name = os.path.split(self.original_log)
        base_name, ext = os.path.splitext(file_name)
        cleaned_file_name = f"cleaned_{base_name}{ext}"
        cleaned_file_path = os.path.join(dir_name, cleaned_file_name)

        try:
            with open(self.original_log, 'r') as infile, open(cleaned_file_path, 'w') as outfile:
                outfile.write("INFO: This clean log was cleaned by using a script, since the programmer ran out of time. Use at your own caution.\n\n")
                
                parsing_section = False
                current_section_lines = []

                for line in infile:
                    if line.startswith('--- Logging started'):
                        if current_section_lines:
                            processed_section = self._process_log_section(current_section_lines)
                            outfile.writelines(processed_section)
                            outfile.write("\n")  
                        
                        parsing_section = True
                        current_section_lines = [line]
                        continue
                    
                    if line.startswith('--- Logging ended'):
                        current_section_lines.append(line)
                        processed_section = self._process_log_section(current_section_lines)
                        outfile.writelines(processed_section)
                        outfile.write("\n")  
                        
                        parsing_section = False
                        current_section_lines = []
                        continue
                    
                    if parsing_section:
                        current_section_lines.append(line)
                
                if current_section_lines:
                    processed_section = self._process_log_section(current_section_lines)
                    outfile.writelines(processed_section)
                    outfile.write("\n")  
            
            print(f"Cleaned log created at: {cleaned_file_path}")
        except Exception as e:
            print(f"Error creating cleaned log file: {e}")
            raise e
        
        return cleaned_file_path

    def _process_log_section(self, section_lines):
        processed_lines = []
        computing_times = []
        rendering_times = []
        parsing_preamble = True
        preamble_lines_count = 0
        interactor = None
        data_size = None
        logging_end_line = None

        for line in section_lines:
            if line.startswith('--- Logging started'):
                processed_lines.append(line)
                continue

            if line.startswith('--- Logging ended'):
                logging_end_line = line
                continue

            if parsing_preamble and preamble_lines_count < 2:
                if "interactor" in line:
                    interactor = "slider" if "Slider" in line else "input"
                    processed_lines.append(line)
                    preamble_lines_count += 1
                    continue
                if "Data size" in line:
                    data_size_match = re.search(r"Data size: (\d+)", line)
                    if data_size_match:
                        data_size = int(data_size_match.group(1))
                    processed_lines.append(line)
                    preamble_lines_count += 1
                    continue

            parsing_preamble = preamble_lines_count < 2

            if 'Benchmark' in line:
                benchmark_match = re.match(r"(Benchmark \d+ -> )(.+)", line)
                if benchmark_match:
                    processed_lines.append(f"{benchmark_match.group(1)}{benchmark_match.group(2).strip()}\n")

                computing_match = re.search(r"Computing Time: ([\d.e-]+)", line)
                if computing_match:
                    computing_times.append(float(computing_match.group(1)))

                time_key = 'Serializing Time' if self.client_side_rendering else 'Rendering Time'
                rendering_match = re.search(fr"{time_key}: ([\d.e-]+)", line)
                if rendering_match:
                    rendering_times.append(float(rendering_match.group(1)))

        if computing_times or rendering_times:
            stats_section = self._calculate_statistics(computing_times, rendering_times)
            processed_lines.append("\nBenchmark Results:\n")
            processed_lines.extend(stats_section)

        if interactor and data_size:
            size_label = f"{data_size // 1000000}m" if data_size < 1000000000 else "1b"
            computing_var_name = f"{interactor}_{size_label}_ds_computing"
            rendering_or_serializing = "serializing" if self.client_side_rendering else "rendering"
            rendering_var_name = f"{interactor}_{size_label}_ds_{rendering_or_serializing}"

            processed_lines.append(
                f"{computing_var_name} = [{', '.join(f'{x:.6f}' for x in computing_times)}]\n"
            )
            processed_lines.append(
                f"{rendering_var_name} = [{', '.join(f'{x:.6f}' for x in rendering_times)}]\n"
            )

        if logging_end_line:
            processed_lines.append(logging_end_line)

        return processed_lines

    def _calculate_statistics(self, computing_times, rendering_times):
        def format_statistics(times, label):
            if not times:
                return []
            return [
                f"{label}:\n",
                f"  Mean: {statistics.mean(times):.6f}s\n",
                f"  Median: {statistics.median(times):.6f}s\n",
                f"  Std Dev: {statistics.stdev(times):.6f}s\n" if len(times) > 1 else "",
                f"  Min: {min(times):.6f}s\n",
                f"  Max: {max(times):.6f}s\n\n",
            ]

        results = []
        results.extend(format_statistics(computing_times, "Computing Times"))
        time_label = "Serializing Time Times" if self.client_side_rendering else "Rendering Time Times"
        results.extend(format_statistics(rendering_times, time_label))

        return results

    def extract_benchmark_results(self):
        results = {}
        time_key = 'Serializing Time (s)' if self.client_side_rendering else 'Rendering Time (s)'

        try:
            with open(self.cleaned_log, 'r') as infile:
                current_section_results = {}

                for line in infile:
                    computing_match = re.search(r"Benchmark (\d+) -> Computing Time: ([\d.]+)", line)
                    time_match = re.search(r"Benchmark (\d+) -> Serializing Time: ([\d.]+)" if self.client_side_rendering 
                                            else r"Benchmark (\d+) -> Rendering Time: ([\d.]+)", line)

                    if computing_match:
                        benchmark_num = int(computing_match.group(1))
                        computing_time = float(computing_match.group(2))
                        current_section_results[benchmark_num] = {"Benchmark": benchmark_num}
                        current_section_results[benchmark_num]["Computing Time (s)"] = computing_time

                    if time_match:
                        benchmark_num = int(time_match.group(1))
                        time_value = float(time_match.group(2))
                        current_section_results.setdefault(benchmark_num, {"Benchmark": benchmark_num})
                        current_section_results[benchmark_num][time_key] = time_value

                    if line.startswith('--- Logging ended'):
                        results.update(current_section_results)
        
        except Exception as e:
            print(f"Error reading cleaned log file {self.cleaned_log}: {e}")
            raise e
        
        return list(results.values())
    
class ClientLogCleaner:
    def __init__(self, path, server_side_rendering=False):
        if not os.path.isfile(path):
            raise FileNotFoundError(f"The file '{path}' does not exist.")
        
        self.original_log = path
        self.server_side_rendering = server_side_rendering

    def _create_cleaned_log(self):
        dir_name, file_name = os.path.split(self.original_log)
        base_name, ext = os.path.splitext(file_name)
        cleaned_file_name = f"cleaned_{base_name}{ext}"
        cleaned_file_path = os.path.join(dir_name, cleaned_file_name)

        try:
            with open(self.original_log, 'r') as infile, open(cleaned_file_path, 'w') as outfile:
                outfile.write("INFO: This clean log was cleaned by using a script, since the programmer ran out of time. Use at your own caution.\n\n")
                
                parsing_section = False
                current_section_lines = []

                for line in infile:
                    if line.startswith('--- Logging started'):
                        if current_section_lines:
                            processed_section = self._process_log_section(current_section_lines)
                            outfile.writelines(processed_section)
                            outfile.write("\n")  
                        
                        parsing_section = True
                        current_section_lines = [line]
                        continue
                    
                    if line.startswith('--- Logging ended'):
                        current_section_lines.append(line)
                        processed_section = self._process_log_section(current_section_lines)
                        outfile.writelines(processed_section)
                        outfile.write("\n")  
                        
                        parsing_section = False
                        current_section_lines = []
                        continue
                    
                    if parsing_section:
                        current_section_lines.append(line)
                
                if current_section_lines:
                    processed_section = self._process_log_section(current_section_lines)
                    outfile.writelines(processed_section)
                    outfile.write("\n")  
            
            print(f"Cleaned log created at: {cleaned_file_path}")
        except Exception as e:
            print(f"Error creating cleaned log file: {e}")
            raise e
        
        return cleaned_file_path

    def _process_log_section(self, section_lines):
        processed_lines = []
        logging_end_line = None
        parsing_preamble = True
        benchmark_data = {}
        render_data = {}
        valid_benchmarks_started = False
        network_statistics = {"durations": []}
        diagnostics_blocks = []

        for line in section_lines:
            if line.startswith('--- Logging started'):
                processed_lines.append(line)
                continue

            if line.startswith('--- Logging ended'):
                logging_end_line = line
                continue

            if parsing_preamble:
                if "Server type:" in line or "Number of snapshots:" in line or "Number of benchmarks:" in line:
                    processed_lines.append(line)
                    if "Number of benchmarks:" in line:
                        parsing_preamble = False
                    continue

            if self._is_diagnostics_start(line):
                diagnostics_block = [line]
                for subsequent_line in section_lines[section_lines.index(line) + 1:]:
                    if subsequent_line.strip() == "":
                        break
                    diagnostics_block.append(subsequent_line)
                diagnostics_blocks.append(diagnostics_block)
                continue

            if self.server_side_rendering:
                if "Network benchmark" in line:
                    match = re.search(r"Network benchmark (\d+) of (\d+)", line)
                    if match:
                        benchmark_id = int(match.group(1))
                        if benchmark_id == 0:  
                            continue
                        valid_benchmarks_started = True
                        benchmark_data[benchmark_id] = 0.0
                    continue

                if valid_benchmarks_started and "Request Duration" in line:
                    match = re.search(r"Request Duration: ([\d.-]+) ms", line)
                    if match:
                        duration = float(match.group(1))
                        if duration >= 0:
                            benchmark_data[benchmark_id] += duration
                            network_statistics["durations"].append(duration)
                    continue

            if "Rendering benchmark" in line:
                match = re.search(r"Rendering benchmark (\d+) of (\d+)", line)
                if match:
                    render_id = int(match.group(1))
                    total_benchmarks = int(match.group(2))
                    if render_id <= total_benchmarks:
                        render_data[render_id] = 0.0
                continue

            if "Histogram render time" in line:
                match = re.search(r"Histogram render time: ([\d.]+) milliseconds", line)
                if match:
                    render_time = float(match.group(1))
                    render_data[render_id] += render_time
                continue

        for benchmark_id, total_duration in sorted(benchmark_data.items()):
            if benchmark_id <= total_benchmarks:
                processed_lines.append(
                    f"Network benchmark {benchmark_id} of {len(benchmark_data)} -> Request Duration: {total_duration:.3f} ms\n"
                )

        for render_id, total_time in sorted(render_data.items()):
            if render_id <= total_benchmarks:
                processed_lines.append(
                    f"Rendering benchmark {render_id} of {total_benchmarks} -> Histogram render time: {total_time:.2f} ms\n"
                )

        if self.server_side_rendering:
            self._append_network_statistics(processed_lines, network_statistics["durations"])

        for block_idx, block in enumerate(diagnostics_blocks):
            parsed_block = []
            for line in block:
                if not line.startswith("State change times:"):
                    parsed_block.append(line)
            
            if block_idx > 0:  
                processed_lines.append("")
            processed_lines.append("\n")  
            processed_lines.extend(parsed_block)
            processed_lines.append("")  

        if logging_end_line:
            processed_lines.append(logging_end_line)

        return processed_lines

    def _is_diagnostics_start(self, line):
        """Check if a line starts a diagnostics block."""
        return line.startswith("Render Time Statistics:") or \
               line.startswith("Check Time Diagnostics:") or \
               line.startswith("Stability Check Diagnostics:") or \
               line.startswith("State Change Times:")

    def _parse_diagnostics_block(self, block_lines):
        """Parse and return a diagnostics block."""
        parsed_lines = []
        for line in block_lines:
            parsed_lines.append(line)  
        parsed_lines.append("\n")  
        return parsed_lines

    def _append_network_statistics(self, lines, durations):
        if not durations:
            return

        durations.sort()
        n = len(durations)
        q1 = durations[n // 4]
        median = durations[n // 2]
        q3 = durations[3 * n // 4]

        statistics = {
            "Minimum": f"{durations[0]:.2f} ms",
            "First Quartile (Q1)": f"{q1:.2f} ms",
            "Median (Q2)": f"{median:.2f} ms",
            "Third Quartile (Q3)": f"{q3:.2f} ms",
            "Maximum": f"{durations[-1]:.2f} ms",
            "Mean": f"{(sum(durations) / n):.2f} ms",
            "Standard Deviation": f"{(sum((x - sum(durations) / n) ** 2 for x in durations) / n) ** 0.5:.2f} ms",
        }

        lines.append("\nNetwork Request Statistics:\n")
        for key, value in statistics.items():
            lines.append(f"{key}: {value}\n")

if __name__ == "__main__":
    current_line = inspect.currentframe().f_lineno + 1
    print("\033[91mINFO: Uncomment the code below at line {current_line} to run the log cleaners. "
        "Use at your own caution. The programmer who wrote this cannot guarantee it will be "
        "entirely or accurate. Might fail because of RegEx not matching.\033[0m")
    # neurobazaar = get_neurobazaar_dir()
    # server_benchmarks = os.path.join(neurobazaar, "benchmarks/servers/benchmarks")

    # plotly_log = os.path.join(server_benchmarks, "plotly_server.log")
    # matplotlib_log = os.path.join(server_benchmarks, "matplotlib_server.log")
    # vtk_log = os.path.join(server_benchmarks, "vtk_server.log")
    
    # plotly_log_cleaner = ServerLogCleaner(plotly_log, client_side_rendering=True)
    # matplotlib_log_cleaner = ServerLogCleaner(matplotlib_log, client_side_rendering=True)
    # vtk_log_cleaner = ServerLogCleaner(vtk_log, client_side_rendering=False)

    # client_benchmarks = os.path.join(neurobazaar, "benchmarks/scripts/benchmarks")

    # plotly_client_log = os.path.join(client_benchmarks, "plotly_client.log")
    # matplotlib_client_log = os.path.join(client_benchmarks, "matplotlib_client.log")
    # vtk_client_log = os.path.join(client_benchmarks, "vtk_client.log")

    # plotly_client_cleaner = ClientLogCleaner(plotly_client_log, server_side_rendering=False)
    # matplotlib_client_cleaner = ClientLogCleaner(matplotlib_client_log, server_side_rendering=False)
    # vtk_client_cleaner = ClientLogCleaner(vtk_client_log, server_side_rendering=True)