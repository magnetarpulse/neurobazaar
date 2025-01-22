from django.contrib import admin
from home.models import Files, Datastores, LocalFSDatastores, MongoDBDatastores, Collections, UpstreamServer, ServerInstance

class ServerInstanceAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Create or update corresponding UpstreamServer entry with 'new' which maps to 'Histogram' display
        UpstreamServer.objects.update_or_create(
            ip=obj.ip,
            port=obj.port,
            defaults={'route': 'new'}  # 'new' maps to display value 'Histogram' in choices
        )

# Register your models here.
admin.site.register(Files)
admin.site.register(Datastores)
admin.site.register(LocalFSDatastores)
admin.site.register(MongoDBDatastores)
admin.site.register(Collections)
admin.site.register(UpstreamServer)
admin.site.register(ServerInstance, ServerInstanceAdmin)



