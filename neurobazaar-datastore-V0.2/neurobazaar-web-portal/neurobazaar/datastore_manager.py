from abc import ABC, abstractmethod
import os
import threading
from django.core.exceptions import ObjectDoesNotExist

from home.models import LocalFileSystem
datastore_manager = None

class AbstractDatastore(ABC):
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def putDataset(self, dataset_content):
        pass

    @abstractmethod
    def delDataset(self, dataset_id):
        pass

    @abstractmethod
    def getDataset(self, dataset_id):
        pass

class FSDatastore(AbstractDatastore):
    def __init__(self, path):
        self.path = path
    
    def connect(self):
        print(f"Connecting to filesystem")

    def disconnect(self):
        print(f"Disconnecting from filesystem")
        
    def putDataset(self, dataset_id, dataset):
        file_path = f"{self.path}/{dataset_id}" 
        with open(file_path, 'wb') as file:
            file.write(dataset)
    
    def delDataset(self, dataset_id):
        file_path = f"{self.path}/{dataset_id}" 
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            del self.datasets[dataset_id]
            return True
        return False
    
    def getDataset(self, dataset_id):
        file_path = f"{self.path}/{dataset_id}"
        with open(file_path, 'rb') as file:
            return file.read()

class DatastoreManager:
    def __init__(self) -> None:
        self.datastores = {}
        self.next_id = 1
    
    def addDataStore(self, DataStoreID : str, DataStore : AbstractDatastore) -> None:
        self.datastores[DataStoreID] = DataStore
        self.next_id += 1
    
    def getDataStore(self, DataStoreID : str) -> AbstractDatastore:
        return self.datastores[DataStoreID]
        
    def removeDataStore(self, DataStoreID : str) -> None:
        self.datastores.pop(DataStoreID)
        
    def addFSDataStore(self, DataStorePath : str) -> str:
        DataStoreID = self.next_id
        fs_datastore = FSDatastore(DataStorePath)
        self.addDataStore(DataStoreID, fs_datastore)
        
        new_local_fs = LocalFileSystem(
            DataStore_ID=str(DataStoreID),  
            DataStore_Name="filesystem",
            Destination_Path=DataStorePath 
        )
        new_local_fs.save()
        
        return DataStoreID

def getDataStoreManager():
    global datastore_manager
    if datastore_manager is None:
        datastore_manager = DatastoreManager()
    return datastore_manager
