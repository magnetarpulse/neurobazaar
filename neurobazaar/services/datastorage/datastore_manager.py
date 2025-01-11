import sys
import os
from uuid import UUID

def get_neurobazaar_dir() -> str:
    """Returns the neurobazaar directory."""
    cwd = os.getcwd()
    index = cwd.index('neurobazaar')
    return cwd[:index + len('neurobazaar')]

neurobazaar = get_neurobazaar_dir()
sys.path.insert(0, neurobazaar)

from home.models import LocalFSDatastores, MongoDBDatastores
from neurobazaar.services.datastorage.abstract_datastore import AbstractDatastore
from neurobazaar.services.datastorage.localfs_datastore import LocalFSDatastore
from neurobazaar.services.datastorage.mongodb_datastore import MongoDBDatastore

from asgiref.sync import sync_to_async      # type: ignore
import functools
import threading
import asyncio

RED = "\033[31m"
BLUE = "\033[34m"
GREEN = "\033[32m"
RESET = "\033[0m"

datastore_manager = None
async_datastore_manager = None

def synchronized(func):
    lock = threading.Lock()
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with lock:
            return func(*args, **kwargs)
    
    return wrapper

async def getDataStoreManager():
    global async_datastore_manager
    if async_datastore_manager is None:
        async_datastore_manager = DatastoreManager()
        await async_datastore_manager.refresh()
    return async_datastore_manager

def get_datastore_manager_sync():
    global datastore_manager
    if datastore_manager is None:
        datastore_manager = DatastoreManagerSync()
        datastore_manager.refresh()
    return datastore_manager

class DatastoreManager:
    def __init__(self):
        self._datastores = {}
        self._lock = asyncio.Lock()
    
    async def refresh(self):
        print("\033[94mRefreshing datastores...\033[0m")
        await self.refreshLocalFSDatastores()
        await self.refreshMongoDBDatastores()
        print(f"{BLUE}Datastores after refresh: {self._datastores}{RESET}")
    
    async def refreshLocalFSDatastores(self):
        # Use sync_to_async to perform database query
        records = await sync_to_async(lambda: {
            str(record.UUID): record for record in LocalFSDatastores.objects.all()
        })()
        
        # Create objects that exist in the model but not in the runtime
        async with self._lock:
            for datastoreUUID, record in records.items():
                if datastoreUUID not in self._datastores:
                    self.addLocalFSDatastore(datastoreUUID, record.Directory_Path)
    
    async def refreshMongoDBDatastores(self):
        # Use sync_to_async to perform database query
        records = await sync_to_async(lambda: {
            str(record.UUID): record for record in MongoDBDatastores.objects.all()
        })()
        
        # Create objects that exist in the model but not in the runtime
        async with self._lock:
            for datastoreUUID, record in records.items():
                if datastoreUUID not in self._datastores:
                    self.addMongoDBDatastore(
                        datastoreUUID,
                        record.Username,
                        record.Password,
                        record.Host,
                        record.Port,
                        record.Database
                    )
    
    def addLocalFSDatastore(self, datastoreUUID: str, storeDirPath: str):
        try:
            print(f"\033[94mAdding LocalFSDatastore with UUID: {datastoreUUID}\033[0m")  
            datastore = LocalFSDatastore(storeDirPath)
            self._datastores[datastoreUUID] = datastore
            success_message = f"Local FS datastore added: {datastoreUUID}"
            print(f"\033[92m{success_message}\033[0m")  
        except Exception as e:
            error_message = f"Failed to add Local FS datastore: {e}"
            print(f"\033[91m{error_message}\033[0m")  
            raise

    def addMongoDBDatastore(self,
                            datastoreUUID: str,
                            username: str,
                            password: str,
                            host: str,
                            port: str,
                            database: str):
        try:
            print(f"\033[94mAdding MongoDB datastore with UUID: {datastoreUUID}\033[0m") 
            datastore = MongoDBDatastore(username, password, host, port, database)
            self._datastores[datastoreUUID] = datastore
            success_message = f"MongoDB datastore added: {datastoreUUID}"
            print(f"\033[92m{success_message}\033[0m")  
        except Exception as e:
            error_message = f"Failed to add MongoDB datastore: {e}"
            print(f"\033[91m{error_message}\033[0m")  
            raise
    
    async def getDatastore(self, dataStoreUUID: str) -> tuple[str, AbstractDatastore]:
        """
        Retrieves the datastore object and its class name for the given UUID.

        Args:
            dataStoreUUID (str): The UUID of the datastore to retrieve.

        Returns:
            tuple: A tuple containing:
                - str: The class name of the datastore object.
                - object: The datastore object itself.
        """
        try:
            dataStoreUUID = str(UUID(dataStoreUUID))
        except ValueError:
            print(f"\033[91mInvalid UUID: {dataStoreUUID}\033[0m")
            return (None, None)
        
        if dataStoreUUID not in self._datastores:
            await self.refresh()

        datastore = self._datastores.get(dataStoreUUID, None)
        datastore_class_name = datastore.__class__.__name__ if datastore else None
        
        return (datastore_class_name, datastore)
    
    async def removeDataStore(self, datastoreUUID: str):
        # Convert to string to ensure consistent key type
        datastoreUUID = str(datastoreUUID)
        
        async with self._lock:
            if datastoreUUID in self._datastores:
                del self._datastores[datastoreUUID]
                await self.refresh()
                print(f"Datastore with UUID: {datastoreUUID} removed")
            else:
                print(f"Datastore with UUID: {datastoreUUID} not found")
            print(f"Current datastores: {self._datastores}")

class DatastoreManagerSync:
    def __init__(self):
        self._datastores = {}
    
    @synchronized
    def refresh(self):
        print("\033[94mRefreshing datastores...\033[0m")
        self.refreshLocalFSDatastores()
        self.refreshMongoDBDatastores()
        print(f"{BLUE}Datastores after refresh: {self._datastores}{RESET}")
    
    def refreshLocalFSDatastores(self):
        records = {record.UUID: record for record in LocalFSDatastores.objects.all()}
        
        # Create objects that exist in the model but not in the runtime
        for datastoreUUID, record in records.items():
            if datastoreUUID not in self._datastores:
                self.addLocalFSDatastore(datastoreUUID, record.Directory_Path)

        # # Remove objects that exist in the runtime but not in the model
        # for datastoreUUID in list(self._datastores.keys()):
        #     if datastoreUUID not in records:
        #         del self._datastores[datastoreUUID]
    
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

        # # Remove objects that exist in the runtime but not in the model
        # for datastoreUUID in list(self._datastores.keys()):
        #     if datastoreUUID not in records:
        #         del self._datastores[datastoreUUID]
        
    def addLocalFSDatastore(self, datastoreUUID: str, storeDirPath: str):
        try:
            print(f"\033[94mAdding datastore with UUID: {datastoreUUID}\033[0m")  
            datastore = LocalFSDatastore(storeDirPath)
            self._datastores[datastoreUUID] = datastore
            success_message = f"Local FS datastore added: {datastoreUUID}"
            print(f"\033[92m{success_message}\033[0m")  
        except Exception as e:
            error_message = f"Failed to add Local FS datastore: {e}"
            print(f"\033[91m{error_message}\033[0m")  
            raise
        
    def addMongoDBDatastore(self,
                            datastoreUUID: str,
                            username: str,
                            password: str,
                            host: str,
                            port: str,
                            database: str):
        try:
            print(f"\033[94mAdding MongoDB datastore with UUID: {datastoreUUID}\033[0m") 
            datastore = MongoDBDatastore(username, password, host, port, database)
            self._datastores[datastoreUUID] = datastore
            success_message = f"MongoDB datastore added: {datastoreUUID}"
            print(f"\033[92m{success_message}\033[0m")  
        except Exception as e:
            error_message = f"Failed to add MongoDB datastore: {e}"
            print(f"\033[91m{error_message}\033[0m")  
            raise

    def get_datastore_sync(self, dataStoreUUID: str) -> tuple[str, AbstractDatastore]:
        """
        Retrieves the datastore object and its class name for the given UUID.

        Args:
            dataStoreUUID (str): The UUID of the datastore to retrieve.

        Returns:
            tuple: A tuple containing:
                - str: The class name of the datastore object.
                - object: The datastore object itself.
        """
        try:
            dataStoreUUID = UUID(dataStoreUUID)
        except ValueError:
            print(f"\033[91mInvalid UUID: {dataStoreUUID}\033[0m")
            return (None, None)
        
        if dataStoreUUID not in self._datastores:
            self.refresh()
        
        datastore = self._datastores.get(dataStoreUUID, None)
        datastore_class_name = datastore.__class__.__name__ if datastore else None
        
        return (datastore_class_name, datastore)
        
    def removeDataStore(self, datastoreUUID: str):
        uuid_obj = UUID(datastoreUUID)
        if uuid_obj in self._datastores:
            del self._datastores[uuid_obj]
            datastore_manager.refresh()
            print(f"Datastore with UUID: {datastoreUUID} removed")
        else:
            print(f"Datastore with UUID: {datastoreUUID} not found")
        print(f"Current datastores: {self._datastores}")