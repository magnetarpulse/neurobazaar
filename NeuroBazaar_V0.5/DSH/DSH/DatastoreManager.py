from DSH.SQLite3Datastore import SQLite3Datastore
from DSH.PostgreSQLDatastore import PostgreSQLDatastore
from DSH.MongoDBDatastore import MongoDBDatastore
from DSH.RedisDatastore import RedisDatastore

global Datastore_setting
Datastore_setting = {
    'DATASTORE' : '3'
}

Datastore_List = {
'1' : 'SQLite3',
'2' : 'PostgreSQL',
'3' : 'MongoDB',
'4' : 'Redis'
}

def getInstance():
    manager = DatastoreManager()
    print("\n Datastore before intiating p: ", Datastore_setting['DATASTORE'])
    p = manager.getDS(Datastore_setting['DATASTORE'])
    return p

class DatastoreManager:
    
    def menuDS(self):
        return Datastore_List
    
    def setDS(self, DSSID):
        DSSID_str = str(DSSID)  # Convert DSSID to string
        global Datastore_setting
        Datastore_setting['DATASTORE'] = DSSID_str
        print("\n setDS Datastore_setting:",Datastore_setting['DATASTORE'])
        # print("Datastore set to: ", Datastore_List[DSSID_str])
        self.update_p()
    
    def getDS(self, DSSID):
        if DSSID == '1':
            return SQLite3Datastore()
        elif DSSID == '2':
            return PostgreSQLDatastore()
        elif DSSID == '3':
            return MongoDBDatastore()
        elif DSSID == '4':
            return RedisDatastore()
        else:
            print("Invalid choice")
            return None
        
    def update_p(self):
        global p
        p = self.getDS(Datastore_setting['DATASTORE'])
        print("\n \nDatastore updated to: ", Datastore_List[Datastore_setting['DATASTORE']])
        
manager = DatastoreManager()