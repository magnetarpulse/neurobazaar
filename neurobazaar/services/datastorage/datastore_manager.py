from home.models import LocalFSDatastores, MongoDBDatastores

datastore_manager = None

def getDataStoreManager():
    global datastore_manager
    if datastore_manager is None:
        datastore_manager = DatastoreManager()
        datastore_manager.refresh()

    return datastore_manager

class DatastoreManager:
    def __init__(self):
        self._datastores = {}
        
    def refresh(self):
        self.refreshLocalFSDatastores()
        self.refreshMongoDBDatastores()
    
    def refreshLocalFSDatastores(self):
        records = LocalFSDatastores.objects.all()
        
        # Create objects that exist in the model but not in the runtime
        for record in records:
            if record.Datastore_ID not in self._datastores:
                self.addLocalFSDatastore(record.Store_Directory_Path)

        records = {(record.Datastore_ID, record) for record in records}
        # Remove objects that exist in the runtime but not in the model
        for datastoreID in self._datastores:
            
    
    def refreshMongoDBDatastores(self):
        pass
    
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
        
    def addLocalFSDatastore(self, DataStorePath : str) -> str:
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