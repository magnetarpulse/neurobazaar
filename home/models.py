from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class User(models.Model):
    username = models.CharField(max_length=122,null=True)
    password = models.CharField(max_length=122,null=True)

    def __str__(self):
        return self.username

class Metadata(models.Model):
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
