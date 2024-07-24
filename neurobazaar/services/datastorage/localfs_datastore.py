from neurobazaar.services.datastorage.abstract_datastore import AbstractDatastore, DatastoreType, synchronized
from django.core.files.uploadedfile import UploadedFile

import os
import uuid

class LocalFSDatastore(AbstractDatastore):
    def __init__(self, storeDirPath: str):
        super().__init__(DatastoreType.LocalFSDatastore)
        self._storeDirPath = storeDirPath
        # TO-DO check to see if the directory exists
        # If the directory does not exists try to create it
        # If creation fails, throw an exception
    
    def putDataset(self, uploadedFile: UploadedFile) -> str:
        datasetUUID = str(uuid.uuid4())
        destinationPath = os.path.join(self._storeDirPath, datasetUUID)
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
