from abc import ABC, abstractmethod
import os
from pymongo import MongoClient
import gridfs

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from home.models import LocalFileSystem, MongoDB
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
        file_path = os.path.join(self.path, dataset_id)
        with open(file_path, 'wb+') as destination:
            for chunk in dataset.chunks():
                destination.write(chunk)
    
    def delDataset(self, dataset_id):
        file_path = os.path.join(self.path, dataset_id)
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            del self.datasets[dataset_id]
            return True
        return False
    
    def getDataset(self, dataset_id):
        file_path = os.path.join(self.path, dataset_id)
        with open(file_path, 'rb') as file:
            return file.read()

class MongoDBDatastore(AbstractDatastore):
    def __init__(self, uri, database_name):
        self.client = MongoClient(uri)
        self.db = self.client[database_name]
        self.fs = gridfs.GridFS(self.db)
    
    def connect(self):
        print("Connecting to MongoDB")
    
    def disconnect(self):
        # Close the MongoDB connection
        self.client.close()
        print("Disconnected from MongoDB")
        
    def putDataset(self, dataset_id, dataset):
        # Store the dataset in GridFS; dataset should be a bytes-like object
        file_id = self.fs.put(dataset, filename=dataset_id)
        return str(file_id)  # Return the GridFS file ID as a string
    
    def delDataset(self, dataset_id):
        # Delete the dataset based on the filename
        file = self.fs.find_one({'filename': dataset_id})
        if file:
            self.fs.delete(file._id)
            return True
        return False
    
    def getDataset(self, dataset_id):
        # Retrieve the dataset from GridFS
        file = self.fs.find_one({'filename': dataset_id})
        if file:
            return file.read()
        return None

class DatastoreManager:
    def __init__(self) -> None:
        self.datastores = {}
        self.next_id = 1
    
    def addDataStore(self, DataStoreID : str, DataStore : AbstractDatastore) -> None:
        self.datastores[DataStoreID] = DataStore
        self.next_id += 1
    
    def getDataStore(self, DataStoreID : str) -> AbstractDatastore:
        print("\n\n inside get datastoretc , Datastore ID: ", DataStoreID)
        datastore_value = self.datastores[DataStoreID]
        print("\n\n datastore value:tc ", datastore_value)
        return self.datastores[DataStoreID]
        
    def removeDataStore(self, DataStoreID : str) -> None:
        self.datastores.pop(DataStoreID)
        
    def addFSDataStore(self, DataStorePath : str) -> str:
        DataStoreID = self.next_id
        fs_datastore = FSDatastore(DataStorePath)
        self.addDataStore(DataStoreID, fs_datastore)
        
        # new_local_fs = LocalFileSystem(
        #     DataStore_ID=str(DataStoreID),  
        #     DataStore_Name="filesystem",
        #     Destination_Path=DataStorePath 
        # )
        # new_local_fs.save()
        
        return DataStoreID
    
    def addMongoDBDataStore(self, host, port, username, password, database, collection) -> str:
        DataStoreID = self.next_id
        uri = f"mongodb://{username}:{password}@{host}:{port}"
        mongodb_datastore = MongoDBDatastore(uri, database)
        self.addDataStore(str(DataStoreID), mongodb_datastore)

        # Save configuration details to MongoDB model
        # new_mongo_db_config = MongoDB(
        #     DataStore_ID=str(DataStoreID),
        #     DataStore_Name=f"MongoDB at {host}",
        #     Host=host,
        #     Port=port,
        #     Username=username,
        #     Password=password,
        #     Database=database,
        #     Collection=collection
        # )
        # new_mongo_db_config.save()
 
    def load_datastores(self):
        # Load Local File Systems
        for fs in LocalFileSystem.objects.all():
            print("reached in load datastores")
            fs_datastore = FSDatastore(fs.Destination_Path)
            self.datastores[fs.DataStore_ID] = fs_datastore

        # Load MongoDB Datastores
        for mdb in MongoDB.objects.all():
            uri = f"mongodb://{mdb.Username}:{mdb.Password}@{mdb.Host}:{mdb.Port}"
            mongodb_datastore = MongoDBDatastore(uri, mdb.Database)
            self.datastores[mdb.DataStore_ID] = mongodb_datastore

def getDataStoreManager():
    global datastore_manager
    if datastore_manager is None:
        datastore_manager = DatastoreManager()
        datastore_manager.load_datastores()
        print("\n",datastore_manager.datastores)

    return datastore_manager
