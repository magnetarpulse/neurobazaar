from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from .Abstract_Datastore import Abstract_Datastore

# requirede for redis
import os
import time
import redis
import json

# Get the directory of the current script
base_directory = os.path.dirname(os.path.abspath(__file__))
# Output directory for uploaded files
upload_directory = os.path.join(base_directory, 'test_upload_files')
os.makedirs(upload_directory, exist_ok=True)

class RedisDatastore(Abstract_Datastore):
    @classmethod
    def configure(self, host, port, db):
        print(f"Connecting to Redis at {host}:{port}/{db}")
        self.r = redis.Redis(host=host, port=port, db=db)
     
    def put(self, user, dataset_name, description, file_path, uploaded_file, upload_date):
        metadata = {
            'user': user.username,  # Serialize only the username
            'description': description,
            'dataset_name': dataset_name,
            'file_path': file_path
        }
        self.r.set(f"{os.path.basename(file_path)}:metadata", json.dumps(metadata))
        
        with uploaded_file.open('rb') as file, open(os.path.join(upload_directory, uploaded_file.name), 'wb') as output_file:
            file_data = file.read()
            output_file.write(file_data)
     
        
    def get(self, dataset_name):
        file_path = f'new_datasets_uploads/{dataset_name}'
                # Get the DatasetDescription object based on the file path

        # Open the file and prepare the HttpResponse for download
        with open(file_path, 'rb') as file:
            response = HttpResponse(file.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{dataset_name}"'
            return response