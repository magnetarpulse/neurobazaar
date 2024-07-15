from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from .Abstract_Datastore import Abstract_Datastore
import os
import time
from pymongo import MongoClient

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['newtestpymongo']
metadata_collection = db['mymongotest']

# MongoDB setup
# def mongodbConnection(client, db, table):
#     client = MongoClient(client)
#     db = client[client]
#     table = db[table]
#     return table

# Get the directory of the current script
base_directory = os.path.dirname(os.path.abspath(__file__))

# Directory to watch
directory_path = os.path.join(base_directory, 'Datasets')

# Output directory for uploaded files
upload_directory = os.path.join(base_directory, 'test_upload_files')
os.makedirs(upload_directory, exist_ok=True)  # Ensure the directory exists

class MongoDBDatastore(Abstract_Datastore):
        def __init__(self, redis_connection):
            self.r = redis_connection  
    
        def put(self, user, dataset_name, description, file_path, uploaded_file, upload_date ):
            metadata = {
                'user': user.username,
                'description': description,
                'visibility': 'public',
                'file_path': file_path,
                'file_name': dataset_name
            }
            metadata_collection.insert_one(metadata)
            
            with uploaded_file.open('rb') as file, open(os.path.join(upload_directory, uploaded_file.name), 'wb') as output_file:
                file_data = file.read()
                output_file.write(file_data)
        
        def get(self, uuid):
              return super().get(uuid)