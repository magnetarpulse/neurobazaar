from neurobazaar.services.datastorage.abstract_datastore import AbstractDatastore, DatastoreType
from django.core.files.uploadedfile import UploadedFile

from pymongo import MongoClient
from gridfs import GridFS

class MongoDBDatastore(AbstractDatastore):
    def __init__(self, username: str, password: str, host: str, port: str, database : str):
        super().__init__(DatastoreType.MongoDBDatastore)
        self.__username = username
        self.__password = password
        self.__host = host
        self.__port = port
        self.__database = database
        uri = f"mongodb://{username}:{password}@{host}:{port}"
        self._client = MongoClient(uri)
        self._db = self._client[database]
        self._fs = GridFS(self._db)
        
    def putDataset(self, uploadedFile: UploadedFile) -> str:
        datasetUUID = self._fs.put(uploadedFile)
        return str(datasetUUID)
    
    def getDataset(self, datasetUUID: str):
        """ Returns a MongoDB GridFSFile object."""
        if self._fs.exists(datasetUUID):
            return self._fs.get(datasetUUID)
        else:
            return None
    
    def delDataset(self, datasetUUID: str):
        if self._fs.exists(datasetUUID):
            return self._fs.delete(datasetUUID)
