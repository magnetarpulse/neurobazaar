from django.db import models
from django.conf import settings


# Create your models here.
class User(models.Model):
    username = models.CharField(max_length=122,null=True)
    password = models.CharField(max_length=122,null=True)

    def __str__(self):
        return self.username

#  store user, dataset_name, description, UUID of the dataset, upload_date
#  store the dataset_file in the datastore. send the uuid and the file itself to the datastore.
class DatasetDescription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    dataset_name = models.CharField(max_length=255)
    description = models.TextField()
    file_path = models.CharField(max_length=1024)
    dataset_file = models.FileField(upload_to='new_datasets_uploads')
    upload_date = models.DateTimeField(auto_now_add=True)

    def __str__(self): 
        return f"{self.dataset_name} by {self.user.username}"