from django.contrib import admin
from home.models import Files, Datastores, LocalFSDatastores, MongoDBDatastores, Collections, UpstreamServer

# Register your models here.
admin.site.register(Files)
admin.site.register(Datastores)
admin.site.register(LocalFSDatastores)
admin.site.register(MongoDBDatastores)
admin.site.register(Collections)
admin.site.register(UpstreamServer)



