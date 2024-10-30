from django.db import models
from django.conf import settings
import uuid
    
class Datastores(models.Model):
    UUID = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    Name = models.CharField(max_length=128)
    Type = models.CharField(max_length=32, choices=[('localfs', 'LocalFS'), ('mongodb', 'MongoDB')], editable=False)
    Created = models.DateField(auto_now_add=True)
    Modified = models.DateField(auto_now=True)
    Connected = models.BooleanField(default=False)
    
class LocalFSDatastores(Datastores):
    Directory_Path = models.CharField(max_length=4096)

class MongoDBDatastores(Datastores):
    Host = models.CharField(max_length=128)
    Port = models.IntegerField()
    Username = models.CharField(max_length=128)
    Password = models.CharField(max_length=128)
    Database = models.CharField(max_length=128)
    Collection = models.CharField(max_length=128)

class Files(models.Model):
    UUID = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    Datastore_UUID = models.ForeignKey('Datastores', on_delete=models.PROTECT, editable=False)
    Username = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    Name = models.CharField(max_length=256)
    Type = "Tabular Data"
    Description = models.TextField(null=True)
    Repository = models.CharField(max_length=16, choices=[('public', 'Public'), ('private', 'Private')])
    Likes = models.IntegerField(default=0)
    Dislikes = models.IntegerField(default=0)
    Created = models.DateField(auto_now_add=True)
    Modified = models.DateField(auto_now=True)
    Collections_UUID = models.ForeignKey('Collections', on_delete=models.PROTECT, editable=False, null=True)
    Collection_Name = models.CharField(max_length=256, null=True, blank=True)

class Collections(models.Model):
    Collections_UUID = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    Datastore_UUID = models.ForeignKey(Datastores, on_delete=models.PROTECT, editable=False)
    Dataset_UUID = models.ForeignKey(Files, on_delete=models.PROTECT, editable=False)
    Collection_Name = models.CharField(max_length=256)
    Repository = models.CharField(max_length=16, choices=[('public', 'Public'), ('private', 'Private')])
    Created = models.DateField(auto_now_add=True)
    Modified = models.DateField(auto_now=True)

class UpstreamServer(models.Model):
    ip = models.CharField(max_length=255)
    port = models.IntegerField()
    route = models.CharField(max_length=50, choices=[('new', 'Histogram'), ('new2', 'Server')])

    class Meta:
        unique_together = ('ip', 'port', 'route')

    def __str__(self):
        return f"{self.ip}:{self.port} ({self.route})"

# Add other models here if they exist
