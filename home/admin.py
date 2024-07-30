from django.contrib import admin
from home.models import Datasets, Datastores, LocalFSDatastores, MongoDBDatastores

# Register your models here.
admin.site.register(Datasets)
admin.site.register(Datastores)
admin.site.register(LocalFSDatastores)
admin.site.register(MongoDBDatastores)


