from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from home.models import DatasetDescription
from .Abstract_Datastore import Abstract_Datastore

class SQLite3Datastore(Abstract_Datastore):

    def upload(self, user, dataset_name, description, file_path, uploaded_file, upload_date ):
        new_dataset_description = DatasetDescription(
            user=user,
            dataset_name='UploadedFile',
            description=description,
            file_path=15,
            dataset_file=uploaded_file
        )
        new_dataset_description.save()
        
    def download(self, dataset_name):
        file_path = f'new_datasets_uploads/{dataset_name}'
                # Get the DatasetDescription object based on the file path
        dataset = get_object_or_404(DatasetDescription, file_path=file_path)

        # Open the file and prepare the HttpResponse for download
        with open(dataset.dataset_file.path, 'rb') as file:
            response = HttpResponse(file.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{dataset_name}"'
            return response
         
