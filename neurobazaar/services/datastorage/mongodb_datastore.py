import sys
import os

def get_neurobazaar_dir() -> str:
    """Returns the neurobazaar directory."""
    cwd = os.getcwd()
    index = cwd.index('neurobazaar')
    return cwd[:index + len('neurobazaar')]

neurobazaar = get_neurobazaar_dir()
sys.path.insert(0, neurobazaar)

from neurobazaar.services.datastorage.abstract_datastore import AbstractDatastore, DatastoreType
from django.core.files.uploadedfile import UploadedFile                                         # type: ignore
from bson.binary import Binary                                                                  # type: ignore
import uuid

from pymongo import MongoClient                                                                 # type: ignore    
from gridfs import GridFS                                                                       # type: ignore
import logging

class MongoDBDatastore(AbstractDatastore):
    def __init__(self, username: str, password: str, host: str, port: str, database: str):
        super().__init__(DatastoreType.MongoDBDatastore)
        self.__username = username
        self.__password = password
        self.__host = host
        self.__port = port
        self.__database = database
        uri = f"mongodb://{self.__username}:{self.__password}@{self.__host}:{self.__port}/"
        try:
            self._client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self._client.server_info()  # Force connection on a request as the MongoClient's connect is lazy.
            self._db = self._client[self.__database]
            self._fs = GridFS(self._db)
            success_message = "Connected to MongoDB successfully."
            logging.info(success_message)
            print(f"\033[92m{success_message}\033[0m")  
        except Exception as e:
            error_message = f"Failed to connect to MongoDB: {e}"
            logging.error(error_message)
            print(f"\033[91m{error_message}\033[0m")  
            raise ConnectionError(error_message)

    def putDataset(self, uploadedFile: UploadedFile) -> str:
        try:
            print("\033[94mStarting dataset upload process to MongoDB...\033[0m")
            datasetUUID = uuid.uuid4()
            print(f"\033[94mGenerated UUID: {datasetUUID}\033[0m")
            uuid_bin = Binary.from_uuid(datasetUUID)
            print(f"\033[94mConverted UUID to Binary: {uuid_bin}\033[0m")
            self._fs.put(uploadedFile, _id=uuid_bin)
            print(f"\033[92mDataset uploaded successfully with UUID: {datasetUUID}\033[0m")
            return str(datasetUUID)
        except Exception as e:
            print(f"\033[91mFailed to upload dataset: {e}\033[0m")
            logging.error(f"Failed to upload dataset: {e}")
            raise

    def getDataset(self, datasetUUID: str):
        """Returns a GridFSFile object if the dataset exists, otherwise returns None."""
        try:
            uuid_obj = uuid.UUID(datasetUUID)
            uuid_bin = Binary(uuid_obj.bytes, 4)
            print("\033[94mRetrieving dataset from MongoDB...\033[0m")
            print(f"\033[94mUUID: {uuid_obj}\033[0m")
            print(f"\033[94mUUID Binary: {uuid_bin}\033[0m")
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

if __name__ == "__main__":
    try:
        datastore = MongoDBDatastore(
            username="huy_admin",
            password="huy_admin",
            host="localhost",
            port="27017",
            database="admin"
        )
    except ConnectionError as e:
        print(e)