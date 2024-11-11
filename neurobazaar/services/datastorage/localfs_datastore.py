import os
import uuid
import time
import threading

from neurobazaar.services.datastorage.abstract_datastore import AbstractDatastore, DatastoreType
from django.core.files.uploadedfile import UploadedFile

from typing import Optional, Dict, List, Union

class LocalFSDatastore(AbstractDatastore):
    """
    Local filesystem datastore implementation.
    """

    def __init__(self, storeDirPath: str):
        """
        Initializes the LocalFSDatastore.

        Args:
            storeDirPath (str): Path to the directory where datasets will be stored.
        """
        super().__init__(DatastoreType.LocalFSDatastore)
        self._storeDirPath = storeDirPath
        self._original_filenames: Dict[str, str] = {}
        self._metadata_lock = threading.Lock()

        if not os.path.exists(storeDirPath):
            os.makedirs(storeDirPath)

        self._metadata_dir = os.path.join(self._storeDirPath, ".metadata")
        os.makedirs(self._metadata_dir, exist_ok=True)
        self._metadata_file_path = os.path.join(self._metadata_dir, "uuid_mappings.txt")

        self._datasets_dir = os.path.join(self._storeDirPath, ".datasets")
        os.makedirs(self._datasets_dir, exist_ok=True)

    def putDataset(self, uploadedFile: UploadedFile) -> str:
        """
        Stores the uploaded file in the datastore.

        Args:
            uploadedFile (UploadedFile): The uploaded file to store.

        Returns:
            str: The UUID of the stored dataset.
        """
        datasetUUID = str(uuid.uuid4())
        print("Storing dataset with UUID:", datasetUUID)

        destinationPath = os.path.join(self._storeDirPath, datasetUUID)
        with open(destinationPath, 'wb') as fileout:
            for chunk in iter(lambda: uploadedFile.read(1048576), b''):
                fileout.write(chunk)

        with self._metadata_lock:
            self._original_filenames[datasetUUID] = uploadedFile.name
            self.link_datasets_to_uuids(datasetUUID, uploadedFile.name)
            with open(self._metadata_file_path, 'a') as metadata_file:
                metadata_file.flush()
                os.fsync(metadata_file.fileno())

        return datasetUUID

    def getDataset(self, datasetUUID: str) -> Optional[Union[bytes, None]]:
        """
        Retrieves a dataset from the datastore.

        Args:
            datasetUUID (str): The UUID of the dataset to retrieve.

        Returns:
            Optional[Union[bytes, None]]: A Python 3 file object if the dataset exists, None otherwise.
        """
        sourcePath = os.path.join(self._storeDirPath, datasetUUID)
        if os.path.exists(sourcePath):
            return open(sourcePath, 'rb')
        else:
            return None

    def delDataset(self, datasetUUID: str) -> None:
        """
        Deletes a dataset from the datastore.

        Args:
            datasetUUID (str): The UUID of the dataset to delete.
        """
        sourcePath = os.path.join(self._storeDirPath, datasetUUID)
        if os.path.exists(sourcePath):
            os.remove(sourcePath)

    def delete_a_datastore(self, datasetUUID: str) -> None:
        """
        Deletes a file in the datastore directory. Not to be confused with delete_a_dataset, which only deletes the dataset.

        Args:
            datasetUUID (str): The UUID of the file to delete.
        """
        file_path = os.path.join(self._storeDirPath, datasetUUID)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"Deleted {file_path}")
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")

    def delete_all_datastore(self) -> None:
        """
        Deletes all files in the datastore directory. Not to be confused with delete_all_datasets, which only deletes the datasets.
        """
        for filename in os.listdir(self._storeDirPath):
            file_path = os.path.join(self._storeDirPath, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"Deleted {file_path}")
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")

    def delete_a_dataset(self, datasetUUID: Optional[str] = None, datasetName: Optional[str] = None) -> None:
        """
        Deletes a dataset in the datastore directory. Not to be confused with delete_a_datastore, which deletes a file in the datastore.

        Args:
            datasetUUID (Optional[str]): The UUID of the dataset to delete.
            datasetName (Optional[str]): The name of the dataset to delete.

        Raises:
            ValueError: If neither datasetUUID nor datasetName is provided.
            FileNotFoundError: If the dataset cannot be found.
        """
        if datasetUUID:
            file_path = os.path.join(self._datasets_dir, datasetUUID)
        elif datasetName:
            file_path = None
            for root, _, files in os.walk(self._datasets_dir):
                for file in files:
                    if file == datasetName:
                        file_path = os.path.join(root, file)
                        break
                if file_path:
                    break
        else:
            raise ValueError("Either datasetUUID or datasetName must be provided.")

        if file_path and os.path.isfile(file_path):
            try:
                os.remove(file_path)
                print(f"Deleted {file_path}")
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")
        else:
            raise FileNotFoundError(f"Dataset not found: {datasetUUID or datasetName}")

    def delete_all_datasets(self) -> None:
        """
        Deletes all datasets in the datastore directory. Not to be confused with delete_all_datastore, which deletes all files in the datastore.
        """
        for filename in os.listdir(self._datasets_dir):
            file_path = os.path.join(self._datasets_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"Deleted {file_path}")
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")

    def putCollection(self, collectionUUID: str, files: List[UploadedFile], relative_paths: List[str]) -> str:
        """
        Stores a collection of files in the datastore.

        Args:
            collectionUUID (str): The UUID of the collection.
            files (List[UploadedFile]): A list of files to store.
            relative_paths (List[str]): A list of relative paths for the files within the collection.

        Returns:
            str: The UUID of the stored collection.
        """
        collection_dir_path = os.path.join(self._storeDirPath, collectionUUID)
        os.makedirs(collection_dir_path, exist_ok=True)

        for file, rel_path in zip(files, relative_paths):
            destination_path = os.path.join(collection_dir_path, rel_path)
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            with open(destination_path, 'wb') as fileout:
                for chunk in file.chunks():
                    fileout.write(chunk)

        return collectionUUID

    def getCollection(self, collectionUUID: str) -> Optional[str]:
        """
        Retrieves the path to a collection directory.

        Args:
            collectionUUID (str): The UUID of the collection to retrieve.

        Returns:
            Optional[str]: The path to the collection directory if it exists, None otherwise.
        """
        collection_dir_path = os.path.join(self._storeDirPath, collectionUUID)
        if os.path.exists(collection_dir_path):
            return collection_dir_path
        else:
            return None

    def getOriginalFilename(self, datasetUUID: str) -> Optional[str]:
        """
        Retrieves the original filename of an uploaded dataset.

        Args:
            datasetUUID (str): The UUID of the dataset.

        Returns:
            Optional[str]: The original filename of the dataset if it exists, None otherwise.
        """
        datasetUUID_str = str(datasetUUID)
        print(self._original_filenames.get(datasetUUID_str))
        return self._original_filenames.get(datasetUUID_str)

    def link_datasets_to_uuids(self, datasetUUID: str, original_filename: str) -> None:
        """
        Links a dataset UUID to its original filename.

        Args:
            datasetUUID (str): The UUID of the dataset.
            original_filename (str): The original filename of the dataset.
        """
        creation_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

        with open(self._metadata_file_path, 'a') as metadata_file:
            metadata_file.write(f"{datasetUUID},{original_filename},{creation_time}\n")
            metadata_file.flush()
            os.fsync(metadata_file.fileno())

    def unlink_datasets_from_uuids(self, datasetUUID: str) -> None:
        """
        Unlinks a dataset UUID from its original filename.

        Args:
            datasetUUID (str): The UUID of the dataset to unlink.
        """
        with open(self._metadata_file_path, 'r') as metadata_file:
            lines = metadata_file.readlines()

        with open(self._metadata_file_path, 'w') as metadata_file:
            for line in lines:
                if line.split(',')[0] != datasetUUID:
                    metadata_file.write(line)

    def clear_metadata(self) -> None:
        """
        Clears all metadata from the metadata file.
        """
        with open(self._metadata_file_path, 'w') as metadata_file:
            metadata_file.write("")

    def get_metadata_name(self, datasetUUID: str) -> Optional[str]:
        """
        Retrieves the original filename associated with a dataset UUID from the metadata file.

        Args:
            datasetUUID (str): The UUID of the dataset.

        Returns:
            Optional[str]: The original filename if found, None otherwise.
        """
        if not os.path.exists(self._metadata_file_path):
            return None

        with self._metadata_lock:
            try:
                with open(self._metadata_file_path, 'r') as metadata_file:
                    lines = metadata_file.readlines()

                    for line in lines:
                        parts = line.strip().split(',')

                        if len(parts) != 3:
                            continue

                        uuid, filename, _ = parts
                        if uuid == datasetUUID:
                            return filename

                print(f"No match found for UUID: {datasetUUID}")
                return None

            except Exception as e:
                print(f"Error reading metadata file: {e}")
                return None