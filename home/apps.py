from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.db.utils import OperationalError

import uuid

class HomeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'home'
    
    def ready(self):
        def start_datastore_manager(sender, **kwargs):
            try:
                # Configure the default datastore if it there are not datastores in the database
                from home.models import LocalFSDatastores
                from neurobazaar.settings import DATASTORE
                if not LocalFSDatastores.objects.exists():
                    datastoreUUID = uuid.uuid4()
                    LocalFSDatastores.objects.create(Name="default",
                                                     Type="localfs",
                                                     Directory_Path=DATASTORE['default']['PATH'])

                # Set all of the datastores to disconnected
                from home.models import Datastores
                Datastores.objects.update(Connected=False)
                
                # Create the datastore manager and initialize the datastores from the database
                from neurobazaar.services.datastorage.datastore_manager import getDataStoreManager
                manager = getDataStoreManager()
                manager.refresh()
                
            except OperationalError:
                pass
        
        post_migrate.connect(start_datastore_manager, sender=self)
