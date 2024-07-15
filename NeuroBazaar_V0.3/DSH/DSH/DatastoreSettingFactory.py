from DSH.SQLite3Datastore import SQLite3Datastore
from DSH.PostgreSQLDatastore import PostgreSQLDatastore
from DSH.MongoDBDatastore import MongoDBDatastore
from DSH.RedisDatastore import RedisDatastore

class DatastoreSettingFactory:
    @staticmethod
    def instance(datastore_type):
        if datastore_type == 'sqlite3':
            return SQLite3Datastore()
        elif datastore_type == 'postgresql':
            return PostgreSQLDatastore()
        elif datastore_type == 'mongodb':
            return MongoDBDatastore()
        elif datastore_type == 'redis':
            return RedisDatastore()
        else:
            raise ValueError("Unsupported datastore type")

