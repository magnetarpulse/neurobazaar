import os
import time
from pymongo import MongoClient
from gridfs import GridFS

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['newtestpymongo']
fs = GridFS(db)

# Directory to watch
directory_path = r'C:\Users\Rushikesh\Downloads\Datasets'

# Function to upload a file
def upload_file(file_path):
    with open(file_path, 'rb') as file:
        file_data = file.read()
        start_time = time.perf_counter()  # Start timing
        file_id = fs.put(file_data, filename=os.path.basename(file_path))
        end_time = time.perf_counter()  # End timing
        # print(f"Uploaded {file_path} as {file_id}")
        print(f"Uploaded {file_path} in {end_time - start_time:.2f} seconds")


# Loop through each file in the directory and upload
for filename in os.listdir(directory_path):
    file_path = os.path.join(directory_path, filename)
    if os.path.isfile(file_path):
        upload_file(file_path)

# Output directory for downloaded files
output_directory = r'C:\Users\Rushikesh\Downloads\testing_file'
os.makedirs(output_directory, exist_ok=True)

# Function to download a file
def download_file(file_id, filename):
    start_time = time.perf_counter()  # Start timing
    file_to_download = fs.get(file_id)
    output_path = os.path.join(output_directory, filename)
    with open(output_path, 'wb') as output_file:
        output_file.write(file_to_download.read())
    end_time = time.perf_counter()  # End timing
    print(f"Downloaded to {output_path} in {end_time - start_time:.2f} seconds")

# Retrieve file metadata and download files
for grid_out in fs.find({}):
    download_file(grid_out._id, grid_out.filename)