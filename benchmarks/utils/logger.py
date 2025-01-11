import os
import sys
from datetime import datetime
import traceback
from typing import Optional
import re

class ReLogger:
    """A class to duplicate print statements to both the terminal and a log file."""

    def __init__(self, log_file: str = 're_logger.log', use_dir: Optional[str] = None, create_dir: Optional[str] = None) -> None:
        """
        Initialize the ReLogger instance.

        Args:
            log_file (str): Name of the log file.
            use_dir (Optional[str]): Path to an existing directory where the log file should be stored.
            create_dir (Optional[str]): Name of a directory to create for storing the log file.
        """
        self.original_log_file = log_file
        self.log_file: str = log_file
        self.original_stdout: Optional[object] = sys.stdout
        self.log_file_handle: Optional[object] = None

        if use_dir and create_dir:
            raise ValueError("Only one of 'use_dir' or 'create_dir' can be specified.")

        if use_dir:
            self._set_directory(use_dir)
        elif create_dir:
            self._create_and_set_directory(create_dir)

    def _set_directory(self, directory: str) -> None:
        """
        Set the directory where the log file will be stored.

        Args:
            directory (str): The path to the existing directory.
        """
        if not os.path.isdir(directory):
            raise FileNotFoundError(f"The directory '{directory}' does not exist.")
        self.log_file = os.path.join(directory, self.original_log_file)

    def _create_and_set_directory(self, directory: str) -> None:
        """
        Create a directory for storing the log file.

        Args:
            directory (str): The name of the directory to create.
        """
        if os.path.exists(directory):
            if os.path.isdir(directory):
                print(f"\033[91mWARNING: The directory '{directory}' already exists. Do you want to use it? (\033[92my\033[91m/\033[91mn\033[91m)\033[0m")
                response = input().strip().lower()
                if response != 'y':
                    raise ValueError("Directory creation aborted by user.")
            else:
                raise FileExistsError(f"'{directory}' exists but is not a directory.")
        else:
            os.makedirs(directory)

        self.log_file = os.path.join(directory, self.original_log_file)

    def _remove_ansi_escape_sequences(self, message: str) -> str:
        """Remove ANSI escape sequences from the given message."""
        ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
        return ansi_escape.sub('', message)

    def _write_to_file(self, message: str) -> None:
        """Write the given message to the log file."""
        if self.log_file_handle:
            clean_message = self._remove_ansi_escape_sequences(message)
            self.log_file_handle.write(clean_message)
            self.log_file_handle.flush()

    def _write_to_terminal(self, message: str) -> None:
        """Write the given message to the terminal."""
        if self.original_stdout:
            self.original_stdout.write(message)
            self.original_stdout.flush()

    def _duplicate_output(self, message: str) -> None:
        """Write the given message to both the terminal and the log file."""
        self._write_to_terminal(message)
        self._write_to_file(message)

    def run(self) -> None:
        """Start redirecting print statements to the log file."""
        self.log_file_handle = open(self.log_file, 'a')
        self.log_file_handle.write(f"\n--- Logging started on {datetime.now()} ---\n")
        sys.stdout = self

    def stop(self) -> None:
        """Stop redirecting print statements and restore original stdout."""
        if self.log_file_handle:
            self.log_file_handle.write(f"\n--- Logging ended on {datetime.now()} ---\n")
            self.log_file_handle.close()
        sys.stdout = self.original_stdout

    def write(self, message: str) -> None:
        """Intercept print statements and duplicate their output."""
        self._duplicate_output(message)

    def flush(self) -> None:
        """Flush output streams to ensure all data is written."""
        if self.original_stdout:
            self.original_stdout.flush()
        if self.log_file_handle:
            self.log_file_handle.flush()

    def __enter__(self) -> "ReLogger":
        """Enter the runtime context related to this object."""
        self.run()
        return self

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Optional[object]) -> bool:
        """Exit the runtime context related to this object."""
        self.stop()

        if exc_type is not None:
            with open(self.log_file, 'a') as f:
                f.write(f"\n--- Exception occurred on {datetime.now()} ---\n")
                f.write(f"Exception Type: {exc_type.__name__}\n")
                f.write(f"Exception Message: {exc_val}\n")
                f.write("Traceback:\n")
                traceback.print_tb(exc_tb, file=f)
            return False 
        return True