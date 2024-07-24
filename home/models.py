from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class User(models.Model):
    username = models.CharField(max_length=122,null=True)
    password = models.CharField(max_length=122,null=True)

    def __str__(self):
        return self.username

class Datasets(models.Model):
    dsid = models.CharField(max_length=100,null=True)
    did = models.CharField(max_length=100, null=True)
    user = models.CharField(max_length=100, null=True)
    dname = models.CharField(max_length=255)
    description = models.TextField(null=True)
    repo = models.CharField(max_length=10, choices=[('public', 'Public'), ('private', 'Private')], null=True)
    likes = models.IntegerField(default=0)
    dislikes = models.IntegerField(default=0)
    comments = models.CharField(max_length=255, null=True)
    date = models.DateField(auto_now_add=True)
    time = models.TimeField(auto_now_add=True)

    def __str__(self):
        return self.dname
    
class Datastores(models.Model):
    Datastore_ID = models.CharField(max_length=100, null=True)
    Datastore_Name = models.CharField(max_length=255)
    Date_Created = models.DateField(auto_now_add=True)
    Date_Accessed = models.DateField(auto_now=True)
    Date_Modified = models.DateField(auto_now=True)

    def __str__(self):
        return self.DataStore_Name
    
class LocalFSDatastores(Datastores):
    Store_Directory_Path = models.TextField()
    
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