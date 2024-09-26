from neurobazaar.services.datastorage.abstract_datastore import AbstractDatastore, DatastoreType
from django.core.files.uploadedfile import UploadedFile

import os
import uuid

class LocalFSDatastore(AbstractDatastore):
    def __init__(self, storeDirPath: str):
        super().__init__(DatastoreType.LocalFSDatastore)
        self._storeDirPath = storeDirPath
        self._original_filenames = {} 
        
        if not os.path.exists(storeDirPath):
            os.makedirs(storeDirPath)
    
    def putDataset(self,uploadedFile: UploadedFile) -> str:
        datasetUUID = uuid.uuid4()
        self._original_filenames[str(datasetUUID)] = uploadedFile.name 
        destinationPath = os.path.join(self._storeDirPath, str(datasetUUID))
        with open(destinationPath, 'wb') as fileout:
            for chunk in iter(lambda: uploadedFile.read(1048576), b''):
                fileout.write(chunk)
        return datasetUUID

    def getDataset(self, datasetUUID: str):
        """ Returns a Python 3 file object."""
        sourcePath = os.path.join(self._storeDirPath, datasetUUID)
        if os.path.exists(sourcePath):
            return open(sourcePath, 'rb')
        else:
            return None
    
    def delDataset(self, datasetUUID: str):
        sourcePath = os.path.join(self._storeDirPath, datasetUUID)
        if os.path.exists(sourcePath):
            os.remove(sourcePath)
    
    def putCollection(self, collectionUUID: str, files: list, relative_paths: list) -> str:
        collection_dir_path = os.path.join(self._storeDirPath, collectionUUID)
        os.makedirs(collection_dir_path, exist_ok=True)
        
        # Save each file in the collection
        for file, rel_path in zip(files, relative_paths):
            destination_path = os.path.join(collection_dir_path, rel_path)
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            with open(destination_path, 'wb') as fileout:
                for chunk in file.chunks():
                    fileout.write(chunk)
        
        return collectionUUID

    def getCollection(self, collectionUUID: str) -> str:
        """ Returns the path to the collection directory. """
        collection_dir_path = os.path.join(self._storeDirPath, collectionUUID)
        if os.path.exists(collection_dir_path):
            return collection_dir_path
        else:
            return None
    
    def getOriginalFilename(self, datasetUUID: str) -> str:
        return self._original_filenames.get(datasetUUID)