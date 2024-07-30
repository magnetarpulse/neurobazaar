from neurobazaar.services.datastorage.abstract_datastore import AbstractDatastore, DatastoreType
from django.core.files.uploadedfile import UploadedFile

import os
import uuid

class LocalFSDatastore(AbstractDatastore):
    def __init__(self, storeDirPath: str):
        super().__init__(DatastoreType.LocalFSDatastore)
        self._storeDirPath = storeDirPath
        
        if not os.path.exists(storeDirPath):
            os.makedirs(storeDirPath)
    
    def putDataset(self, datasetUUID,uploadedFile: UploadedFile) -> str:
        datasetUUID = str(datasetUUID)
        original_name = uploadedFile.name # get the original name of the file for extension
        _, ext = os.path.splitext(original_name) # get the extension of the file
        destinationPath = os.path.join(self._storeDirPath, datasetUUID+ext)
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
