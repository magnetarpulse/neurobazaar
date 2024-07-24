from neurobazaar.services.datastorage.abstract_datastore import AbstractDatastore
from django.core.files.uploadedfile import UploadedFile
import os

class FSDatastore(AbstractDatastore):
    def __init__(self, storeDirPath: str) -> None:
        self.storeDirPath = storeDirPath
    
    def connect(self) -> None:
        # TO-DO check to see if the directory exists
        # If the directory does not exists try to create it
        # If creation fails, throw an exception
        
        # TO-DO replace print with logger
        print(f"Connecting to filesystem")

    def disconnect(self) -> None:
        # TO-DO replace print with logger
        print(f"Disconnecting from filesystem")
        
    def putDataset(self, datasetUUID : str, uploadedFile: UploadedFile):
        # TO-DO read the content of the file in binary format and in 1MiB chunks and
        # write the chunks to the corresponding file associated with the UUID
        
        destinationPath = os.path.join(self.storeDirPath, datasetUUID)
        
        with open(destinationPath, 'wb+') as fileout:
            for chunk in iter(lambda: uploadedFile.read(1024 * 1024), b''):
                fileout.write(chunk)

    def getDataset(self, datasetUUID : str) -> str:
        file_path = os.path.join(self.path, dataset_id)
        with open(file_path, 'rb') as file:
            return file.read()
    
    def delDataset(self, dataset_id):
        file_path = os.path.join(self.path, dataset_id)
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            del self.datasets[dataset_id]
            return True
        return False