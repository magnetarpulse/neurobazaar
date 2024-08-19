from uuid import UUID
from django.shortcuts import render
from home.models import LocalFSDatastores, MongoDBDatastores
from neurobazaar.services.datastorage.abstract_datastore import AbstractDatastore
from neurobazaar.services.datastorage.localfs_datastore import LocalFSDatastore
from neurobazaar.services.datastorage.mongodb_datastore import MongoDBDatastore
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

datastore_manager = None

def getDataStoreManager():
    global datastore_manager
    if datastore_manager is None:
        datastore_manager = DatastoreManager()
        datastore_manager.refresh()
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
        logging.info("Refreshing datastores...")
        self.refreshLocalFSDatastores()
        self.refreshMongoDBDatastores()
        logging.debug(f"Datastores after refresh: {self._datastores}")
    
    def refreshLocalFSDatastores(self):
        records = {record.UUID: record for record in LocalFSDatastores.objects.all()}
        logging.debug(f"LocalFSDatastores records: {records}")
        
        # Create objects that exist in the model but not in the runtime
        for datastoreUUID, record in records.items():
            if datastoreUUID not in self._datastores:
                self.addLocalFSDatastore(datastoreUUID, record.Directory_Path)
    
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
        
    def addLocalFSDatastore(self, datastoreUUID: str, storeDirPath: str):
        logging.info(f"\n\nAdding datastore with UUID: {datastoreUUID}")
        datastore = LocalFSDatastore(storeDirPath)
        self._datastores[datastoreUUID] = datastore
        logging.debug(f"Current datastores: {self._datastores}\n\n")
        
    def addMongoDBDatastore(self,
                            datastoreUUID: str,
                            username: str,
                            password: str,
                            host: str,
                            port: str,
                            database: str):
        logging.info(f"Adding MongoDB datastore with UUID: {datastoreUUID}")
        datastore = MongoDBDatastore(username, password, host, port, database)
        self._datastores[datastoreUUID] = datastore
        logging.debug(f"MongoDB datastore added: {datastoreUUID}")
    
    def getDatastore(self, dataStoreUUID : str) -> AbstractDatastore:
        uuid_obj = UUID(dataStoreUUID)
        if uuid_obj in self._datastores:
            return self._datastores[uuid_obj]
        else:
            self.refresh()
            return self._datastores.get(uuid_obj, None)
        
    def removeDataStore(self, datastoreUUID: str):
        uuid_obj = UUID(datastoreUUID)
        if uuid_obj in self._datastores:
            del self._datastores[uuid_obj]
            datastore_manager.refresh()
            logging.info(f"Datastore with UUID: {datastoreUUID} removed")
        else:
            logging.warning(f"Datastore with UUID: {datastoreUUID} not found")
        logging.debug(f"Current datastores: {self._datastores}")