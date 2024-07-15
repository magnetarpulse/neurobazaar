from DSH.SQLite3Datastore import SQLite3Datastore
from DSH.PostgreSQLDatastore import PostgreSQLDatastore
from DSH.MongoDBDatastore import MongoDBDatastore
from DSH.RedisDatastore import RedisDatastore
from DSH.DatastoreSettingFactory import DatastoreSettingFactory

#Setup your databse here:
Datastore_setting = {
    'DATASTORE' : 'sqlite3' 
}

p = DatastoreSettingFactory.instance(Datastore_setting['DATASTORE'])

# p = MongoDBDatastore()
