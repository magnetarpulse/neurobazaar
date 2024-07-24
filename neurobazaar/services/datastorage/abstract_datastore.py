from abc import ABC, abstractmethod

class AbstractDatastore(ABC):
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def putDataset(self, dataset_content):
        pass
    
    @abstractmethod
    def getDataset(self, dataset_id):
        pass

    @abstractmethod
    def delDataset(self, dataset_id):
        pass