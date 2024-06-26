from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from .Abstract_Datastore import Abstract_Datastore

# requirede for redis
import os
import time
import redis
import json

# Connect to Redis
# check 
r = redis.Redis(host='localhost', port=6379, db=0)

# Get the directory of the current script
base_directory = os.path.dirname(os.path.abspath(__file__))
# Output directory for uploaded files
upload_directory = os.path.join(base_directory, 'test_upload_files')
os.makedirs(upload_directory, exist_ok=True)

class RedisDatastore(Abstract_Datastore):
        
    def upload(self, user, dataset_name, description, file_path, uploaded_file, upload_date ):
        def store_metadata(user, file_path, description, visibility):
            metadata = {
                'user': user,
                'description': description,
                'dataset_name': dataset_name,
                'file_path': file_path
            }
            r.set(f"{os.path.basename(file_path)}:metadata", json.dumps(metadata))        

        with open(file_path, 'rb') as file, open(upload_directory, 'wb') as output_file:
            file_data = file.read()
            output_file.write(file_data)        
        
    def download(self, dataset_name):
        file_path = f'new_datasets_uploads/{dataset_name}'
                # Get the DatasetDescription object based on the file path

        # Open the file and prepare the HttpResponse for download
        with open(file_path, 'rb') as file:
            response = HttpResponse(file.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{dataset_name}"'
            return response