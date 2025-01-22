from django.db import models
from django.conf import settings
import uuid
from django.contrib.auth.models import User
from django.utils import timezone

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
    route = models.CharField(max_length=50)
    display_name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ('ip', 'port')
        verbose_name = 'Upstream Server'
        verbose_name_plural = 'Upstream Servers'

    def __str__(self):
        return f"{self.display_name} ({self.ip}:{self.port})"

class ServerInstance(models.Model):
    SERVER_TYPE_CHOICES = [
        ('basic', 'Basic Server'),
        ('general', 'General Server'),
        ('analyzer', 'Analyzer Server')
    ]
    
    server_type = models.CharField(max_length=20, choices=SERVER_TYPE_CHOICES)
    port = models.IntegerField()
    ip = models.CharField(max_length=255, default='localhost')
    started_at = models.DateTimeField(auto_now_add=True)
    is_running = models.BooleanField(default=True)

    class Meta:
        unique_together = ('ip', 'port')

    def __str__(self):
        return f"{self.server_type} server at {self.ip}:{self.port} ({'Running' if self.is_running else 'Stopped'})"

# Add other models here if they exist
