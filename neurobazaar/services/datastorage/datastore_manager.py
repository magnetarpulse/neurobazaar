from home.models import LocalFSDatastores, MongoDBDatastores
from neurobazaar.services.datastorage.abstract_datastore import AbstractDatastore
from neurobazaar.services.datastorage.localfs_datastore import LocalFSDatastore
from neurobazaar.services.datastorage.mongodb_datastore import MongoDBDatastore

import threading
import functools

datastore_manager = None

def getDataStoreManager():
    global datastore_manager
    if datastore_manager is None:
        datastore_manager = DatastoreManager()

    return datastore_manager

def synchronized(func):
    lock = threading.Lock()
    
    def wrapper(*args, **kwargs):
        with lock:
            return func(*args, **kwargs)
    
    return wrapper

class DatastoreManager:
    def __init__(self):
        self._datastores = {}
    
    @synchronized
    def refresh(self):
        self.refreshLocalFSDatastores()
        self.refreshMongoDBDatastores()
    
    def refreshLocalFSDatastores(self):
        records = {record.UUID: record for record in LocalFSDatastores.objects.all()}
        
        # Create objects that exist in the model but not in the runtime
        for datastoreUUID, record in records.items():
            if datastoreUUID not in self._datastores:
                self.addLocalFSDatastore(datastoreUUID, record.Directory_Path)

        # Remove objects that exist in the runtime but not in the model
        for datastoreUUID, datastore in self._datastores:
            if datastoreUUID not in records:
                del self._datastores[datastoreUUID]
    
    def refreshMongoDBDatastores(self):
        records = {record.UUID: record for record in MongoDBDatastores.objects.all()}
        
        # Create objects that exist in the model but not in the runtime
        for datastoreUUID, record in records.items():
            if datastoreUUID not in self._datastores:
                self.addMongoDBDatastore(datastoreUUID,
                                         record.Username,
                                         record.Password,
                                         record.Host,
                                         record.Port,
                                         record.Database)

        # Remove objects that exist in the runtime but not in the model
        for datastoreUUID, datastore in self._datastores:
            if datastoreUUID not in records:
                del self._datastores[datastoreUUID]
        
    def addLocalFSDatastore(self, datastoreUUID: str, storeDirPath: str):
        datastore = LocalFSDatastore(storeDirPath)
        self._datastores[datastoreUUID] = datastore
    
    def addMongoDBDatastore(self,
                            datastoreUUID: str,
                            username: str,
                            password: str,
                            host: str,
                            port: str,
                            database: str):
        datastore = MongoDBDatastore(username, password, host, port, database)
        self._datastores[datastoreUUID] = datastore
    
    def getDatastore(self, dataStoreUUID : str) -> AbstractDatastore:
        if dataStoreUUID in self._datastores:
            return self._datastores[dataStoreUUID]
        else:
            return None
