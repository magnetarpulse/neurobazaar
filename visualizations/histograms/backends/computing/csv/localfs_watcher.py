import os
import sys
import argparse

import logging
from typing import List, Tuple, Optional

import csv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
from queue import Queue

import time

def get_neurobazaar_dir() -> str:
    """Returns the neurobazaar directory."""
    cwd = os.getcwd()
    index = cwd.index('neurobazaar')
    return cwd[:index + len('neurobazaar')]

neurobazaar = get_neurobazaar_dir()
sys.path.insert(0, neurobazaar)

from neurobazaar.services.datastorage.localfs_datastore import LocalFSDatastore

class LocalFSDataConverter:
    """
    Converts binary data from LocalFSDatastore to properly named CSV files.
    Handles file watching and conversion non-blockingly.
    """
    def __init__(self, datastore: 'LocalFSDatastore'):
        """Initialize the converter."""

        self._datastore = datastore
        self._output_directory = datastore._datasets_dir
        self._neurobazaar_dir = get_neurobazaar_dir()
        self._processing_queue = Queue()
        self._observer = Observer()
        self._is_running = False
        self._processed_files = set()
        self._max_retries = 3  # Maximum number of retries for metadata
        self._retry_delay = 0.5  # Delay between retries in seconds
            
        # Set up logging
        # logging.basicConfig(level=logging.INFO)
        # self._logger = logging.getLogger(__name__)
        
        # Start processing thread
        self._start_processing_thread()
        
    def _start_processing_thread(self):
        """Starts the background thread for processing files."""
        self._processing_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._processing_thread.start()
        
    def _process_queue(self):
        """Processes files from the queue."""
        while True:
            try:
                uuid = self._processing_queue.get()
                if uuid not in self._processed_files:
                    self._convert_file(uuid)
                    self._processed_files.add(uuid)
                self._processing_queue.task_done()
            except Exception as e:
                # self._logger.error(f"Error processing file {uuid}: {str(e)}")
                print(f"Error processing file {uuid}: {str(e)}")
                
    def _convert_file(self, uuid: str) -> Optional[Tuple[str, str]]:
        """Converts a single file from binary to CSV."""
        # Ignore special directories
        if uuid in {".metadata", ".datasets"}:
            return None
    
        try:
            # Get the dataset
            dataset_file = self._datastore.getDataset(uuid)
            if dataset_file is None:
                print(f"No dataset found with UUID {uuid}")
                return None
                
            # Try to get metadata with retries
            original_name = None
            retries = 0
            while retries < self._max_retries and original_name is None:
                original_name = self._datastore.get_metadata_name(uuid)
                if original_name is None:
                    retries += 1
                    print(f"Retry {retries}/{self._max_retries} for UUID {uuid}")
                    time.sleep(self._retry_delay)
            
            if original_name is None:
                print(f"No original filename found for UUID {uuid} after {self._max_retries} retries")
                return None
                
            # print(f"Successfully got original name: {original_name} for UUID: {uuid}")
                
            # Remove file extension if present
            base_name = os.path.splitext(original_name)[0]
            
            # Read and decode the binary data
            data = dataset_file.read()
            data_str = data.decode('utf-8')
            
            # Create CSV file path
            csv_path = os.path.join(self._output_directory, f"{base_name}.csv")
            
            # Convert to CSV
            try:
                # Split data into rows
                data_list = data_str.split('\n')
                
                # Write to CSV
                with open(csv_path, 'w', newline='') as csv_file:
                    writer = csv.writer(csv_file)
                    for row in data_list:
                        # Split row by comma and clean quotes
                        cleaned_row = [field.strip('"') for field in row.split(',')]
                        writer.writerow(cleaned_row)
                        
                # print(f"Successfully converted {uuid} to {csv_path}")
                return base_name, csv_path
                
            except Exception as e:
                print(f"Error converting file {uuid}: {str(e)}")
                if os.path.exists(csv_path):
                    os.remove(csv_path)
                return None
                
        except Exception as e:
            print(f"Error processing file {uuid}: {str(e)}")
            return None
            
    def start_watching(self):
        """Starts watching the datastore directory for new files."""
        if not self._is_running:
            # Create event handler
            event_handler = FileSystemEventHandler()
            event_handler.on_created = self._on_file_created
            
            # Set up observer
            self._observer.schedule(
                event_handler,
                self._datastore._storeDirPath,
                recursive=False
            )
            self._observer.start()
            self._is_running = True
            print(f"Started watching directory: {self._datastore._storeDirPath}")
            # self._logger.info(f"Started watching directory: {self._datastore._storeDirPath}")
            
    def _on_file_created(self, event):
        """Handles new file creation events."""
        if not event.is_directory:
            print("New file created: ", event.src_path)
            uuid = os.path.basename(event.src_path)
            # Add a small delay before processing to allow metadata write to complete
            time.sleep(0.5)  
            self._processing_queue.put(uuid)
            
    def stop_watching(self):
        """Stops watching for new files."""
        if self._is_running:
            self._observer.stop()
            self._observer.join()
            self._is_running = False
            # self._logger.info("Stopped watching directory")
            
    def convert_existing_files(self) -> Tuple[List[str], List[str]]:
        """Converts all existing files in the datastore."""
        names = []
        csv_files = []
        
        # Get all files in datastore directory
        uuids = os.listdir(self._datastore._storeDirPath)
        
        for uuid in uuids:
            if uuid not in self._processed_files:
                result = self._convert_file(uuid)
                if result:
                    name, csv_path = result
                    names.append(name)
                    csv_files.append(csv_path)
                    self._processed_files.add(uuid)
                    
        return names, csv_files

def main(test_mode):
    neurobazaar_dir = get_neurobazaar_dir()
    datastore_dir = os.path.join(neurobazaar_dir, 'datastore')
    
    # Create datastore
    datastore = LocalFSDatastore(storeDirPath=datastore_dir)
    
    # Create converter
    converter = LocalFSDataConverter(datastore)

    # Wait for 0.5 seconds to ensure datastore is ready
    time.sleep(0.5)
    
    try:
        # Convert existing files
        names, _ = converter.convert_existing_files()
        print(f"Converted files: {names}")
        
        # Start watching for new files
        converter.start_watching()
        
        if test_mode:
            # Simulate uploading a small CSV file every 5 seconds
            while True:
                print("Legacy test mode")
                pass
        else:
            # Keep the script running to watch for new files
            while True:
                time.sleep(1)
            
    except KeyboardInterrupt:
        # Stop watching and clean up
        converter.stop_watching()
        datastore.delete_all_datastore()
        datastore.delete_all_datasets()
        datastore.clear_metadata()
        print("Clean up complete")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LocalFS Datastore Watcher")
    parser.add_argument('--test', action='store_true', help="Enable test mode to upload CSV files every 5 seconds")
    args = parser.parse_args()
    
    main(args.test)