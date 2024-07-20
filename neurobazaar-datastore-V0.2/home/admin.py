from django.contrib import admin
from home.models import Datasets, LocalFileSystem, MongoDB, DataStores

# Register your models here.
admin.site.register(Datasets)
admin.site.register(DataStores)
admin.site.register(LocalFileSystem)
admin.site.register(MongoDB)


