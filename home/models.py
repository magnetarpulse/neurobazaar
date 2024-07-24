from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class User(models.Model):
    username = models.CharField(max_length=122,null=True)
    password = models.CharField(max_length=122,null=True)

    def __str__(self):
        return self.username

class Datasets(models.Model):
    UUID = models.CharField(max_length=100,null=True)
    Datastore_UUID = models.CharField(max_length=100, null=True)
    User = models.CharField(max_length=100, null=True)
    Name = models.CharField(max_length=255)
    Description = models.TextField(null=True)
    Repository = models.CharField(max_length=10, choices=[('public', 'Public'), ('private', 'Private')], null=True)
    Likes = models.IntegerField(default=0)
    Dislikes = models.IntegerField(default=0)
    Comments = models.CharField(max_length=255, null=True)
    Created = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.dname
    
class Datastores(models.Model):
    UUID = models.CharField(max_length=100, null=True)
    Name = models.CharField(max_length=255)
    Type = models.CharField(max_length=255)
    Created = models.DateField(auto_now_add=True)
    Accessed = models.DateField(auto_now=True)
    Modified = models.DateField(auto_now=True)
    Connected = models.BooleanField(auto_created=False)

    def __str__(self):
        return self.DataStore_Name
    
class LocalFSDatastores(Datastores):
    Directory_Path = models.TextField()
    
    def __str__(self):
        return self.Destination_Path

class MongoDBDatastores(Datastores):
    Host = models.CharField(max_length=255)
    Port = models.IntegerField()
    Username = models.CharField(max_length=255)
    Password = models.CharField(max_length=255)
    Database = models.CharField(max_length=255)
    Collection = models.CharField(max_length=255)
    
    def __str__(self):
        return self.Host