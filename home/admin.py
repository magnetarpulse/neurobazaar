from django.contrib import admin
from home.models import Files, Datastores, LocalFSDatastores, MongoDBDatastores, Collections, UpstreamServer, ServerInstance

@admin.register(UpstreamServer)
class UpstreamServerAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'ip', 'port', 'route')
    list_filter = ('route',)
    search_fields = ('display_name', 'ip', 'port', 'route')
    ordering = ('route', 'display_name')

@admin.register(ServerInstance)
class ServerInstanceAdmin(admin.ModelAdmin):
    list_display = ('server_type', 'ip', 'port', 'is_running', 'started_at')
    list_filter = ('server_type', 'is_running')
    search_fields = ('ip', 'port')
    ordering = ('-started_at',)

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



