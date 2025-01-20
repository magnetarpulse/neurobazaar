from abc import ABC, abstractmethod
import enum
import threading
import functools

from django.core.files.uploadedfile import UploadedFile
 
class DatastoreType(enum.Enum):
    LocalFSDatastore = 1
    MongoDBDatastore = 2

class AbstractDatastore(ABC):
    def __init__(self, type: DatastoreType):
        self._type = type
    
    def getDatastoreType(self) -> DatastoreType:
        return self._type

    @abstractmethod
    def putDataset(self, uploadedFile: UploadedFile) -> str:
        pass
    
    @abstractmethod
    def getDataset(self, datasetUUID: str):
        pass

    @abstractmethod
    def delDataset(self, datasetUUID : str):
        pass