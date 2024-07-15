from abc import ABC, abstractmethod

from abc import ABC, abstractmethod
import os

class Abstract_Datastore(ABC):
    
    def setDS(self, dbchoice ="SQLite3" ):
        self._dbchoice = os.getenv('Django_DB_Choice','sqlite3')
        
    def getDS(self):
        return self._dbchoice

    @abstractmethod
    def put(self, uuid, dataset_file ):
        pass

    @abstractmethod
    def get(self, uuid):
        pass