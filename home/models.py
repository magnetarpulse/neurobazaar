from django.db import models
from django.contrib.auth.models import User

import uuid

class User(models.Model):
    username = models.CharField(primary_key=True, editable=False, max_length=128)
    password = models.CharField(max_length=256)
    
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

class Datasets(models.Model):
    UUID = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    Datastore_UUID = models.ForeignKey(Datastores, on_delete=models.PROTECT, editable=False)
    Username = models.ForeignKey(User, on_delete=models.PROTECT)
    Name = models.CharField(max_length=256)
    Description = models.TextField(null=True)
    Repository = models.CharField(max_length=16, choices=[('public', 'Public'), ('private', 'Private')])
    Likes = models.IntegerField(default=0)
    Dislikes = models.IntegerField(default=0)
    Created = models.DateField(auto_now_add=True)
    Modified = models.DateField(auto_now=True)
