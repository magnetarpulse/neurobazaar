import os
import time
from django.core.management.base import BaseCommand
from django.http import FileResponse
from home.models import DatasetDescription, User
from datetime import datetime
from django.contrib.auth.models import User
from django.core.files import File


# Check if the user exists, and if not, create it
try:
    user = User.objects.get(username='admin')
except User.DoesNotExist:
    user = User.objects.create_user('admin', password='admin')

class Command(BaseCommand):
    help = 'Uploads a file'
    

    def handle(self, *args, **options):
        uploadtimelist = []
        fetchtimelist = []
        def simulate_file_upload(uploaded_file, description, visibility, user):
            uploaded_file = File(uploaded_file)
            uploaded_file.name = os.path.basename(uploaded_file.name)
           
            # Simulate file upload and store upload time
            start_time = time.perf_counter()
            
            # Simulate saving the file path to the database
            new_dataset_description = DatasetDescription(
                user=user,
                dataset_name='UploadedFile',
                description=description,
                file_path=15,
                dataset_file=uploaded_file
            )
            new_dataset_description.save()

            # Measure the end time of the upload process
            end_time = time.perf_counter()

            # Calculate the upload time
            upload_time = end_time - start_time
            print(f"Upload Time: {upload_time} seconds")
            uploadtimelist.append(upload_time)
            
            # Simulate file fetch and store fetch time
            start_time = time.perf_counter()

            # Fetch the file using Django's FileResponse
            response = FileResponse(open(new_dataset_description.dataset_file.path, 'rb'))

            # Measure the end time of the fetch process
            end_time = time.perf_counter()

            # Calculate the fetch time
            fetch_time = end_time - start_time
            print(f"Fetch Time: {fetch_time} seconds")
            fetchtimelist.append(fetch_time)

            return upload_time,fetch_time

        # Get the directory of the current script
        base_directory = os.path.dirname(os.path.abspath(__file__))
        file_path_1 = os.path.join(base_directory, '817mb.csv')
        file_path_2 = os.path.join(base_directory, '178mb.csv')
        file_path_3 = os.path.join(base_directory, '139mb.csv')
        file_path_4 = os.path.join(base_directory, 'LIDC.tcia')
       
        description = 'Test upload'
        visibility = 'public'
        user = User.objects.get(username='admin')
    
        for x in range(10):
            # Open the file and pass it to the upload function
            with open(file_path_4, 'rb') as uploaded_file:
                response = simulate_file_upload(uploaded_file, description, visibility, user)
        
        print("this is uplaod time")        
        for x in uploadtimelist:
            print(x)
        avg=sum(uploadtimelist)/len(uploadtimelist)
        print("Average upload Time: ", avg )
        uploadtimelist.clear()

        print("this is fetch time")
        for x in fetchtimelist:
            print(x)
        avg=sum(fetchtimelist)/len(fetchtimelist)
        print("Average fetch Time: ", avg )
        fetchtimelist.clear()
         
        for x in range(10):
            # Open the file and pass it to the upload function
            with open(file_path_3, 'rb') as uploaded_file:
                response = simulate_file_upload(uploaded_file, description, visibility, user)
 
        for x in uploadtimelist:
            print(x)
        avg=sum(uploadtimelist)/len(uploadtimelist)
        print("Average upload Time: ", avg )
        uploadtimelist.clear()
        
        print("this is fetch time")
        for x in fetchtimelist:
            print(x)
        avg=sum(fetchtimelist)/len(fetchtimelist)
        print("Average fetch Time: ", avg )
        fetchtimelist.clear()
               
        for x in range(10):
            # Open the file and pass it to the upload function
            with open(file_path_2, 'rb') as uploaded_file:
                response = simulate_file_upload(uploaded_file, description, visibility, user)
        
        for x in uploadtimelist:
            print(x)
        avg=sum(uploadtimelist)/len(uploadtimelist)
        print("Average upload Time: ", avg )
        uploadtimelist.clear()
        
        print("this is fetch time")
        for x in fetchtimelist:
            print(x)
        avg=sum(fetchtimelist)/len(fetchtimelist)
        print("Average fetch Time: ", avg )
        fetchtimelist.clear()
                     
        for x in range(10):
            # Open the file and pass it to the upload function
            with open(file_path_1, 'rb') as uploaded_file:
                response = simulate_file_upload(uploaded_file, description, visibility, user)
                
        for x in uploadtimelist:
            print(x)
        avg=sum(uploadtimelist)/len(uploadtimelist)
        print("Average upload Time: ", avg )
        uploadtimelist.clear()

        print("this is fetch time")
        for x in fetchtimelist:
            print(x)
        avg=sum(fetchtimelist)/len(fetchtimelist)
        print("Average fetch Time: ", avg )
        fetchtimelist.clear()