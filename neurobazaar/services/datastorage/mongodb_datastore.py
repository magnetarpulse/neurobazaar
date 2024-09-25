from uuid import UUID
import uuid
from neurobazaar.services.datastorage.abstract_datastore import AbstractDatastore, DatastoreType
from django.core.files.uploadedfile import UploadedFile
from bson.binary import Binary
import uuid

from pymongo import MongoClient
from gridfs import GridFS
import logging

class MongoDBDatastore(AbstractDatastore):
    def __init__(self, username: str, password: str, host: str, port: str, database: str):
        super().__init__(DatastoreType.MongoDBDatastore)
        self.__username = username
        self.__password = password
        self.__host = host
        self.__port = port
        self.__database = database
        uri = f"mongodb://{username}:{password}@{host}:{port}/"
        try:
            self._client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self._client.server_info()  # Force connection on a request as the MongoClient's connect is lazy.
            self._db = self._client[database]
            self._fs = GridFS(self._db)
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {e}")
            raise ConnectionError(f"Failed to connect to MongoDB: {e}")

    def putDataset(self, uploadedFile: UploadedFile) -> str:
        """Uploads a dataset to GridFS and returns the unique dataset UUID as a string."""
        try:
            datasetUUID =uuid.uuid4()
            uuid_bin = Binary.from_uuid(datasetUUID)
            self._fs.put(uploadedFile, _id=uuid_bin)
            return datasetUUID
        except Exception as e:
            logging.error(f"Failed to upload dataset: {e}")
            raise

    def getDataset(self, datasetUUID: str):
        """Returns a GridFSFile object if the dataset exists, otherwise returns None."""
        try:
            uuid_obj = uuid.UUID(datasetUUID)
            uuid_bin = Binary(uuid_obj.bytes, 4)
            if self._fs.exists({"_id": uuid_bin}):
                return self._fs.get(uuid_bin)
            else:
                return None
        except Exception as e:
            logging.error(f"Failed to retrieve dataset: {e}")
            raise

    def delDataset(self, datasetUUID: str):
        """Deletes a dataset from GridFS if it exists, raises an error otherwise."""
        try:
            if self._fs.exists({"_id": datasetUUID}):
                self._fs.delete(datasetUUID)
            else:
                raise FileNotFoundError(f"No dataset found with UUID: {datasetUUID}")
        except Exception as e:
            logging.error(f"Failed to delete dataset: {e}")
            raise