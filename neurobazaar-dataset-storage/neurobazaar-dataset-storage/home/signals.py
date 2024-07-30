from django.db.models.signals import post_save
from django.dispatch import receiver
from neurobazaar.settings import DATASTORE
from home.models import LocalFSDatastores

from neurobazaar.services.datastorage.datastore_manager import getDataStoreManager

import uuid

@receiver(post_save, sender=LocalFSDatastores) #removed created=true becauase receiver can accept only 2 arguments
def create_default_datastore(sender, instance, created, **kwargs):
    if not LocalFSDatastores.objects.exists():
        datastoreUUID = uuid.uuid4()
        LocalFSDatastores.objects.create(UUID=datastoreUUID,
                                         Name="default",
                                         Type="localfs",
                                         Directory_Path=DATASTORE['default']['PATH'])
        manager = getDataStoreManager()
        manager.refresh()
        record = LocalFSDatastores.objects.get(UUID=datastoreUUID)
        record.Connected = True
        record.save()
    else:
        manager = getDataStoreManager()
        manager.refresh()
    # connect all records from the model