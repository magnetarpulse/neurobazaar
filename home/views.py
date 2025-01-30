# Django imports
from django.http import FileResponse, HttpResponse, Http404, StreamingHttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models.deletion import ProtectedError
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.template import Template, Context
from home.models import Collections, Files, Datastores, LocalFSDatastores, MongoDBDatastores, UpstreamServer, ServerInstance

# System management
import shutil
import sys
import os
import logging
import requests
import re
import threading
import asyncio
from urllib.parse import urljoin
import time
import uuid
import json
import tempfile
from django.core.files import File
import lz4.frame
import pandas as pd
from django.core.paginator import Paginator

# Import our custom modules
from .data_analysis import DataAnalyzer  # Add this import

# Get the root directory of the project
cwd = os.getcwd()
index = cwd.index('neurobazaar')
neurobazaar_dir = cwd[:index + len('neurobazaar')]
sys.path.insert(0, neurobazaar_dir)

# Create data directory if it doesn't exist
DATA_DIR = os.path.join(neurobazaar_dir, 'data', 'datastores')
try:
    os.makedirs(DATA_DIR, mode=0o777, exist_ok=True)
except Exception as e:
    logger.error(f"Error creating data directory: {str(e)}")
    # Try creating in the current directory if neurobazaar_dir fails
    DATA_DIR = os.path.join(os.getcwd(), 'data', 'datastores')
    os.makedirs(DATA_DIR, mode=0o777, exist_ok=True)

# Import the server manager
from trame.server.example_server_manager import ServerManager
from trame.server.example_standalone_histogram import BasicHistogramApp
from trame.server.example_generic_histogram import GenericHistogramApp
from trame.server.updated_dask_working_code import BaseOoDHistogram

# Set up logging
logger = logging.getLogger(__name__)

class DataStoreManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.initialize()
        return cls._instance

    def initialize(self):
        self.datastores = {}
        # Load existing datastores from database
        self.load_existing_datastores()
        logger.info("DataStoreManager initialized with datastores: %s", self.datastores)

    def load_existing_datastores(self):
        try:
            # Load filesystem datastores
            for ds in LocalFSDatastores.objects.all():
                logger.info(f"Loading filesystem datastore: {ds.UUID} at path {ds.Directory_Path}")
                # Create a new directory path in our data directory
                new_path = os.path.join(DATA_DIR, str(ds.UUID))
                try:
                    # Create directory with proper permissions
                    os.makedirs(new_path, mode=0o777, exist_ok=True)
                    # If old path exists and is different, move contents
                    if os.path.exists(ds.Directory_Path) and ds.Directory_Path != new_path:
                        for item in os.listdir(ds.Directory_Path):
                            src = os.path.join(ds.Directory_Path, item)
                            dst = os.path.join(new_path, item)
                            if os.path.exists(dst):
                                continue
                            if os.path.isdir(src):
                                shutil.copytree(src, dst)
                            else:
                                shutil.copy2(src, dst)
                    # Update the path in the database
                    ds.Directory_Path = new_path
                    ds.save()
                    self.addLocalFSDatastore(ds.UUID, new_path)
                except Exception as e:
                    logger.error(f"Error setting up filesystem datastore {ds.UUID}: {str(e)}")
            
            # Load MongoDB datastores
            for ds in MongoDBDatastores.objects.all():
                logger.info(f"Loading MongoDB datastore: {ds.UUID}")
                self.addMongoDBDatastore(ds.UUID, ds.Username, ds.Password, 
                                       ds.Host, ds.Port, ds.Database)
        except Exception as e:
            logger.error(f"Error loading existing datastores: {str(e)}")

    def addLocalFSDatastore(self, uuid, path):
        logger.info(f"Adding local FS datastore: {uuid} at path {path}")
        try:
            # Ensure the path exists with proper permissions
            os.makedirs(path, mode=0o777, exist_ok=True)
            self.datastores[str(uuid)] = {'type': 'filesystem', 'path': path}
        except Exception as e:
            logger.error(f"Error adding local FS datastore: {str(e)}")
            raise

    def addMongoDBDatastore(self, uuid, username, password, host, port, database):
        self.datastores[str(uuid)] = {
            'type': 'mongodb',
            'username': username,
            'password': password,
            'host': host,
            'port': port,
            'database': database
        }

    def getDatastore(self, uuid):
        return self.datastores.get(str(uuid))

    def removeDatastore(self, uuid):
        if str(uuid) in self.datastores:
            del self.datastores[str(uuid)]

    def putDataset(self, datastore_uuid, file_obj):
        logger.info(f"Putting dataset in datastore {datastore_uuid}")
        datastore = self.getDatastore(datastore_uuid)
        if not datastore:
            logger.error(f"Datastore {datastore_uuid} not found in {self.datastores}")
            raise ValueError(f"Datastore {datastore_uuid} not found")

        if datastore['type'] == 'filesystem':
            try:
                # Create a unique filename
                dataset_uuid = str(uuid.uuid4())
                # Create a subdirectory for this dataset
                dataset_dir = os.path.join(datastore['path'], dataset_uuid)
                os.makedirs(dataset_dir, mode=0o777, exist_ok=True)
                
                # Save the file in the dataset directory
                file_path = os.path.join(dataset_dir, file_obj.name)
                logger.info(f"Saving file to {file_path}")
                
                # Write file in chunks to handle large files
                with open(file_path, 'wb+') as destination:
                    for chunk in file_obj.chunks():
                        destination.write(chunk)
                
                # Set proper permissions on the file
                os.chmod(file_path, 0o666)
                return dataset_uuid
            except Exception as e:
                logger.error(f"Error in putDataset: {str(e)}")
                # Clean up on error
                if os.path.exists(dataset_dir):
                    shutil.rmtree(dataset_dir)
                raise Exception(f"Failed to upload file: {str(e)}")
        else:
            raise NotImplementedError(f"Upload not implemented for {datastore['type']} datastore")

    def getDataset(self, datastore_uuid, dataset_uuid):
        datastore = self.getDatastore(datastore_uuid)
        if not datastore:
            raise ValueError("Datastore not found")

        if datastore['type'] == 'filesystem':
            file_path = os.path.join(datastore['path'], dataset_uuid)
            if os.path.exists(file_path):
                if os.path.isfile(file_path):
                    return open(file_path, 'rb')
                else:
                    # If it's a directory, create a ZIP file
                    zip_filename = f"{dataset_uuid}.zip"
                    zip_path = os.path.join('/tmp', zip_filename)
                    
                    # Create zip file
                    shutil.make_archive(zip_path[:-4], 'zip', file_path)
                    
                    # Stream the zip file
                    response = FileResponse(
                        open(zip_path, 'rb'),
                        as_attachment=True,
                        filename=zip_filename
                    )
                    response['Content-Length'] = os.path.getsize(zip_path)
                    
                    # Schedule zip file cleanup after response is sent
                    def cleanup_zip(sender, **kwargs):
                        try:
                            os.remove(zip_path)
                        except OSError:
                            pass
                    
                    request.META['cleanup_callback'] = cleanup_zip
                    return response
            else:
                raise FileNotFoundError("Dataset not found")
        else:
            raise NotImplementedError(f"Download not implemented for {datastore['type']} datastore")

def getDataStoreManager():
    return DataStoreManager()

# Initialize the visualization server manager in a separate thread
def start_server_manager():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        manager = ServerManager()
        manager.start(port=8080)
        return manager
    except Exception as e:
        logger.error(f"Error initializing visualization server manager: {e}")
        return None

server_manager_thread = threading.Thread(target=start_server_manager, daemon=True)
server_manager_thread.start()

# Create a proxy object to safely access the visualization server manager
class ServerManagerProxy:
    def __init__(self):
        self.manager = None
        self._lock = threading.Lock()

    def get_manager(self):
        if self.manager is None:
            with self._lock:
                if self.manager is None:
                    self.manager = start_server_manager()
        return self.manager

server_manager_proxy = ServerManagerProxy()

# Create your views here.
def index(request):
    username = None
    if request.user.is_authenticated:
        username = request.user.username
    return render(request, 'index.html', {'username': username})


def team_details(request):
    return render(request, 'team-details.html')

def logoutUser(request):
    logout(request)
    return redirect('/login_register')

def download_collection(request, collection_uuid):
    try:
        # Retrieve collection metadata from the database
        collection = Collections.objects.get(Collections_UUID=collection_uuid)
        datastore_instance = collection.Datastore_UUID

        # Retrieve the appropriate datastore
        manager = getDataStoreManager()
        datastore = manager.getDatastore(str(datastore_instance.UUID))

        if not datastore:
            raise Http404("Datastore not found.")

        # Get the path of the collection
        collection_path = datastore.getCollection(str(collection_uuid))
        if not collection_path:
            raise Http404("Collection not found.")

        # Temporary path for the zip file
        zip_path = os.path.join('/tmp', f"{collection_uuid}.zip")

        # Create a zip file
        shutil.make_archive(zip_path.replace('.zip', ''), 'zip', collection_path)

        # Serve the zip file
        with open(zip_path, 'rb') as f:
            response = HttpResponse(f, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{collection_uuid}.zip"'
            return response

    except Collections.DoesNotExist:
        raise Http404("Collection metadata not found.")
    finally:
        # Clean up the created zip file
        if os.path.exists(zip_path):
            os.remove(zip_path)

def datastore(request):
    username = request.user.username
    logger.info("Processing datastore request")
    
    # Handle form submissions for adding or removing datastores
    if request.method == 'POST':
        if 'add_datastore' in request.POST:
            database_type = request.POST.get('database')
            manager = getDataStoreManager()
            logger.info(f"Adding {database_type} datastore")
            
            if database_type == 'filesystem':
                datastore_name = request.POST.get('datastore_name')
                datastore_id = str(uuid.uuid4())
                path = os.path.join(DATA_DIR, datastore_id)
                logger.info(f"Creating filesystem datastore at {path}")
                
                try:
                    # Create directory with proper permissions
                    os.makedirs(path, mode=0o777, exist_ok=True)
                    
                    # Add to DataStoreManager first
                    manager.addLocalFSDatastore(datastore_id, path)
                    
                    # Create base Datastores entry first
                    base_datastore = Datastores(
                        UUID=datastore_id,
                        Name=datastore_name,
                        Type="filesystem",
                        Connected=True
                    )
                    base_datastore.save()
                    logger.info(f"Created base datastore entry: {datastore_id}")
                    
                    # Then create LocalFSDatastores entry
                    new_local_fs = LocalFSDatastores(
                        UUID=datastore_id,
                        Name=datastore_name,
                        Type="filesystem",
                        Connected=True,
                        Directory_Path=path 
                    )
                    new_local_fs.save()
                    logger.info(f"Created LocalFSDatastores entry: {datastore_id}")
                    
                    # Ensure proper permissions are set
                    os.chmod(path, 0o777)
                    messages.success(request, "Filesystem datastore added successfully.")
                except Exception as e:
                    logger.error(f"Error creating filesystem datastore: {str(e)}")
                    messages.error(request, f"Error creating filesystem datastore: {str(e)}")
                    if os.path.exists(path):
                        try:
                            shutil.rmtree(path)
                        except Exception as cleanup_error:
                            logger.error(f"Error cleaning up directory: {str(cleanup_error)}")
                    # Clean up any partial database entries
                    Datastores.objects.filter(UUID=datastore_id).delete()
                    LocalFSDatastores.objects.filter(UUID=datastore_id).delete()
                    
            elif database_type == 'mongodb':
                host = request.POST.get('host_mongo')
                port = request.POST.get('port_mongo')
                username = request.POST.get('username_mongo')
                password = request.POST.get('password_mongo')
                database = request.POST.get('database_mongo')
                datastore_name = request.POST.get('datastore_name_mongo')
                datastore_id = str(uuid.uuid4())
                
                try:
                    # Add to DataStoreManager first
                    manager.addMongoDBDatastore(datastore_id, username, password, host, port, database)
                    
                    # Create base Datastores entry first
                    base_datastore = Datastores(
                        UUID=datastore_id,
                        Name=datastore_name,
                        Type="mongodb",
                        Connected=True
                    )
                    base_datastore.save()
                    
                    # Then create MongoDBDatastores entry
                    new_mongodb = MongoDBDatastores(
                        UUID=datastore_id,
                        Name=datastore_name,
                        Type="mongodb",
                        Connected=True,
                        Host=host,
                        Port=port,
                        Username=username,
                        Password=password,
                        Database=database
                    )
                    new_mongodb.save()
                    messages.success(request, "MongoDB datastore added successfully.")
                except Exception as e:
                    messages.error(request, f"Error creating MongoDB datastore: {str(e)}")
                    # Clean up any partial database entries
                    Datastores.objects.filter(UUID=datastore_id).delete()
                    MongoDBDatastores.objects.filter(UUID=datastore_id).delete()
                
        elif 'remove_datastore' in request.POST:
            datastore_id = request.POST.get('datastore_id')
            manager = getDataStoreManager()
            
            try:
                # Get datastore type
                datastore = Datastores.objects.get(UUID=datastore_id)
                datastore_type = datastore.Type
                
                # Remove from DataStoreManager first
                manager.removeDatastore(datastore_id)
                
                # Remove the physical directory if it's a filesystem datastore
                if datastore_type == 'filesystem':
                    try:
                        local_fs = LocalFSDatastores.objects.get(UUID=datastore_id)
                        if os.path.exists(local_fs.Directory_Path):
                            shutil.rmtree(local_fs.Directory_Path)
                    except Exception as e:
                        logger.error(f"Error removing datastore directory: {str(e)}")
                
                # Remove from database
                if datastore_type == 'filesystem':
                    LocalFSDatastores.objects.filter(UUID=datastore_id).delete()
                elif datastore_type == 'mongodb':
                    MongoDBDatastores.objects.filter(UUID=datastore_id).delete()
                Datastores.objects.filter(UUID=datastore_id).delete()
                
                messages.success(request, "Datastore removed successfully.")
            except ProtectedError:
                messages.error(request, "Cannot delete this datastore because it is still referenced by other objects.")
            except Exception as e:
                messages.error(request, f"Error removing datastore: {str(e)}")

    datastores = Datastores.objects.all()
    return render(request, 'datastore.html', {'datastores': datastores, 'username': username})

def dashboard(request):
    return render(request, 'dashboard.html')
    
def login_register(request):
    login_form_visible = True
    register_form_visible = False

    if request.method == 'POST':
        if 'login_submit' in request.POST:
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password.')

        elif 'register_submit' in request.POST:
            username = request.POST.get('username')
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')

            if password1 != password2:
                messages.error(request, 'Passwords do not match.')
                register_form_visible = True
                login_form_visible = False

            elif len(password1) < 8:
                messages.error(request, 'Password must be at least 8 characters long.')
                register_form_visible = True
                login_form_visible = False

            elif password1.isdigit():
                messages.error(request, 'Password cannot be entirely numeric.')
                register_form_visible = True
                login_form_visible = False

            elif User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists.')
                register_form_visible = True
                login_form_visible = False

            else:
                # Create user if all checks pass
                user = User.objects.create_user(username=username, password=password1)
                user.save()
                messages.success(request, 'Account created successfully. You can now login.')
                return redirect('/login_register')

    # If GET request or form submission didn't succeed, render the login/register form
    return render(request, 'login_register.html', {'login_form_visible': login_form_visible, 'register_form_visible': register_form_visible})


@login_required
def datasets(request):
    username = request.user.username
    user_instance = User.objects.get(username=username) 

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        # Handling Dataset Upload Form
        if form_type == 'dataset_upload':
            try:
                start_time = float(request.session.get('uploadStartTime', time.time() * 1000)) / 1000
                
                # Handle chunked upload
                chunk = request.FILES.get('chunk')
                if chunk:
                    try:
                        chunk_number = int(request.POST.get('chunk_number'))
                        total_chunks = int(request.POST.get('total_chunks'))
                        original_filename = request.POST.get('original_filename')
                        is_compressed = request.POST.get('compressed') == 'true'
                        compression_type = request.POST.get('compression')
                        
                        # Create temp directory if it doesn't exist
                        temp_dir = os.path.join(tempfile.gettempdir(), 'neurobazaar_uploads')
                        os.makedirs(temp_dir, exist_ok=True)
                        
                        # Create or append to temporary file
                        temp_path = os.path.join(temp_dir, f"{request.session.session_key}_{original_filename}")
                        
                        # Read and decompress chunk if needed
                        chunk_data = chunk.read()
                        if is_compressed and compression_type == 'lz4':
                            try:
                                decompressed_data = lz4.frame.decompress(chunk_data)
                            except Exception as e:
                                logger.error(f"Error decompressing chunk: {str(e)}")
                                return JsonResponse({'status': 'error', 'message': 'Decompression failed'})
                        else:
                            decompressed_data = chunk_data
                        
                        # Write chunk to temporary file using buffered write
                        with open(temp_path, 'ab', buffering=8192) as destination:
                            destination.write(decompressed_data)
                            destination.flush()  # Ensure data is written to disk
                        
                        # If this is the last chunk, process the complete file
                        if chunk_number == total_chunks - 1:
                            try:
                                description = request.POST.get('description')
                                repo = request.POST.get('repo')
                                datastore_uuid = request.POST.get('datastore')
                                
                                try:
                                    datastore_instance = Datastores.objects.get(UUID=datastore_uuid)
                                except Datastores.DoesNotExist:
                                    if os.path.exists(temp_path):
                                        os.remove(temp_path)
                                    return JsonResponse({'status': 'error', 'message': 'Datastore not found'})
                                
                                try:
                                    with open(temp_path, 'rb') as f:
                                        file_obj = File(f, name=original_filename)
                                        manager = getDataStoreManager()
                                        dataset_uuid = manager.putDataset(datastore_uuid, file_obj)
                                        
                                        metadata = Files(
                                            Username=user_instance,
                                            Name=original_filename,
                                            UUID=dataset_uuid,
                                            Datastore_UUID=datastore_instance,
                                            Description=description,
                                            Repository=repo,
                                            Created=timezone.now().date()
                                        )
                                        metadata.save()
                                    
                                    if os.path.exists(temp_path):
                                        os.remove(temp_path)
                                    
                                    end_time = time.time()
                                    upload_time = end_time - start_time
                                    messages.success(request, f"File uploaded successfully in {upload_time:.2f} seconds.")
                                    return JsonResponse({'status': 'success'})
                                except Exception as e:
                                    logger.error(f"Error processing complete file: {str(e)}")
                                    if os.path.exists(temp_path):
                                        try:
                                            os.remove(temp_path)
                                        except Exception as cleanup_error:
                                            logger.error(f"Error cleaning up temporary file: {str(cleanup_error)}")
                                    return JsonResponse({'status': 'error', 'message': str(e)})
                            except Exception as e:
                                logger.error(f"Error processing complete file: {str(e)}")
                                if os.path.exists(temp_path):
                                    try:
                                        os.remove(temp_path)
                                    except Exception as cleanup_error:
                                        logger.error(f"Error cleaning up temporary file: {str(cleanup_error)}")
                                return JsonResponse({'status': 'error', 'message': str(e)})
                        
                        return JsonResponse({'status': 'success', 'chunk': chunk_number})
                    except Exception as e:
                        logger.error(f"Error processing chunk: {str(e)}")
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        return JsonResponse({'status': 'error', 'message': str(e)})
                
                return JsonResponse({'status': 'error', 'message': 'No chunk uploaded'})
            except Exception as e:
                logger.error(f"Error in dataset upload: {str(e)}")
                return JsonResponse({'status': 'error', 'message': str(e)})

        # Handling Collection Upload Form
        elif form_type == 'collection_upload':
            files = request.FILES.getlist('collection_files')
            description = request.POST.get('description', '')
            repo = request.POST.get('repo', '')
            dataset_uuid = request.POST.get('dataset_uuid')
            relative_paths = json.loads(request.POST.get('relative_paths', '[]'))

            related_dataset = Files.objects.get(UUID=dataset_uuid)
            datastore_instance = related_dataset.Datastore_UUID  # Use the datastore of the related dataset
            user_instance = User.objects.get(username=username)
            manager = getDataStoreManager()
            datastore = manager.getDatastore(str(datastore_instance.UUID))

            if files:
                start_time = time.time()
                collections_uuid = str(uuid.uuid4())
                collection_name = relative_paths[0].split('/')[0]

                datastore.putCollection(collections_uuid, files, relative_paths)

                collection_model_instance = Collections(
                    Collections_UUID=collections_uuid,
                    Datastore_UUID=datastore_instance,
                    Dataset_UUID=related_dataset,  # Associate with the selected dataset
                    Collection_Name=collection_name,
                    Repository=repo,
                    Created=timezone.now().date(),
                    Modified=timezone.now().date(),
                )
                collection_model_instance.save()
                
                # Update the Files table with the Collection_UUID and Collection_Name
                Files.objects.filter(UUID=related_dataset.UUID).update(
                    Collections_UUID=collection_model_instance,
                    Collection_Name=collection_name
                )

                end_time = time.time()
                upload_time = end_time - start_time
                messages.info(request, f"Collection uploaded in {upload_time:.4f} seconds.")
                return redirect('datasets')
          
        # Handling like action
        elif 'like_file' in request.POST:
            file_uuid = request.POST['like_file']
            metadata = Files.objects.get(UUID=file_uuid)
            metadata.likes = getattr(metadata, 'likes', 0) + 1
            metadata.save()
            return redirect('datasets')

        # Handling dislike action
        elif 'dislike_file' in request.POST:
            file_uuid = request.POST['dislike_file']
            metadata = Files.objects.get(UUID=file_uuid)
            metadata.dislikes = getattr(metadata, 'dislikes', 0) + 1
            metadata.save()
            return redirect('datasets')

        # Handling copy to favorites action
        elif 'copy_to_favorites' in request.POST:
            file_uuid = request.POST['copy_to_favorites']
            metadata = Files.objects.get(UUID=file_uuid)
            
            # Check if the file is already in favorites to prevent duplication
            if not Files.objects.filter(Username=user_instance, Name=metadata.Name, Repository='favorites').exists():
                # Create a new metadata entry for favorites
                favorite_metadata = Files(
                    Username=user_instance,
                    Name=metadata.Name,
                    Description=metadata.Description,
                    Repository='favorites',
                    Created=timezone.now().date(),
                    Datastore_UUID=metadata.Datastore_UUID,
                    UUID=str(uuid.uuid4())  # Generate new UUID for favorite
                )
                favorite_metadata.save()
                
            return redirect('datasets')

        # Handling delete action
        elif 'delete_file' in request.POST:
            file_uuid = request.POST['delete_file']
            metadata = Files.objects.get(UUID=file_uuid)
            # Delete the actual file first
            try:
                manager = getDataStoreManager()
                datastore = manager.getDatastore(str(metadata.Datastore_UUID.UUID))
                if datastore and datastore['type'] == 'filesystem':
                    file_path = os.path.join(datastore['path'], str(metadata.UUID))
                    if os.path.exists(file_path):
                        if os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                        else:
                            os.remove(file_path)
            except Exception as e:
                logger.error(f"Error deleting file: {str(e)}")
            # Then delete the database entry
            metadata.delete()
            return redirect('datasets')
        
        # Handling download action
        elif 'download_file' in request.POST:
            start_time = float(request.session.get('uploadStartTime', time.time() * 1000)) / 1000
            dataset_UUID = request.POST['download_file']
            dataset = Files.objects.get(UUID=dataset_UUID)
            manager = getDataStoreManager()
            datastore_instance = dataset.Datastore_UUID
            
            # Get the datastore info
            datastore_info = manager.getDatastore(str(datastore_instance.UUID))
            
            if datastore_info['type'] == 'filesystem':
                file_path = os.path.join(datastore_info['path'], str(dataset.UUID))
                if os.path.exists(file_path):
                    if os.path.isfile(file_path):
                        response = FileResponse(
                            open(file_path, 'rb'),
                            as_attachment=True,
                            filename=dataset.Name
                        )
                        response['Content-Length'] = os.path.getsize(file_path)
                    else:
                        # If it's a directory, create a ZIP file
                        zip_filename = f"{dataset.Name}.zip"
                        zip_path = os.path.join('/tmp', zip_filename)
                        
                        # Create zip file
                        shutil.make_archive(zip_path[:-4], 'zip', file_path)
                        
                        # Stream the zip file
                        response = FileResponse(
                            open(zip_path, 'rb'),
                            as_attachment=True,
                            filename=zip_filename
                        )
                        response['Content-Length'] = os.path.getsize(zip_path)
                        
                        # Schedule zip file cleanup after response is sent
                        def cleanup_zip(sender, **kwargs):
                            try:
                                os.remove(zip_path)
                            except OSError:
                                pass
                        
                        request.META['cleanup_callback'] = cleanup_zip
                    return response
            else:
                return HttpResponse("Unsupported datastore type for download", status=400)

    # Get all datastores for the upload form
    datastores = Datastores.objects.all()
    
    # Get all files based on repository type
    public_files = Files.objects.filter(Repository='public').order_by('-Created')
    private_files = Files.objects.filter(Repository='private', Username=user_instance).order_by('-Created')
    favorite_files = Files.objects.filter(Repository='favorites', Username=user_instance).order_by('-Created')

    # Get all collections
    public_collections = Collections.objects.filter(Repository='public').order_by('-Created')
    private_collections = Collections.objects.filter(Repository='private', Dataset_UUID__Username=user_instance).order_by('-Created')
    favorite_collections = Collections.objects.filter(Repository='favorites', Dataset_UUID__Username=user_instance).order_by('-Created')

    # Prepare file information with additional details
    def prepare_file_info(files_queryset):
        file_info = []
        for file in files_queryset:
            info = {
                'id': str(file.UUID),
                'uuid': str(file.UUID),
                'name': file.Name,
                'description': file.Description,
                'created': file.Created,
                'username': file.Username.username if file.Username else None,
                'datastore': file.Datastore_UUID.Name if file.Datastore_UUID else None,
                'datastore_type': file.Datastore_UUID.Type if file.Datastore_UUID else None,
                'collection_name': file.Collection_Name,
                'likes': getattr(file, 'likes', 0),
                'dislikes': getattr(file, 'dislikes', 0),
            }
            file_info.append(info)
        return file_info

    context = {
        'username': username,
        'datastores': datastores,
        'public_files': prepare_file_info(public_files),
        'private_files': prepare_file_info(private_files),
        'favorite_files': prepare_file_info(favorite_files),
        'public_collections': public_collections,
        'private_collections': private_collections,
        'favorite_collections': favorite_collections,
    }

    return render(request, 'datasets.html', context)

import mimetypes
import base64

@login_required
def view_directory(request, collections_uuid):
    collection = Collections.objects.get(Collections_UUID=collections_uuid)
    datastore_instance = collection.Datastore_UUID

    # Use the datastore manager to fetch the correct datastore
    manager = getDataStoreManager()
    datastore = manager.getDatastore(str(datastore_instance.UUID))

    collection_path = None
    if isinstance(datastore, LocalFSDatastore):
        collection_path = datastore.getCollection(str(collection.Collections_UUID))
    else:
        raise AttributeError("The datastore is not a LocalFSDatastore and does not have a directory path.")

    # Dictionary to hold folder structure
    folder_structure = {}

    if collection_path:
        for root, dirs, files_in_dir in os.walk(collection_path):
            # Get the relative folder path
            relative_folder = os.path.relpath(root, collection_path)
            
            # Initialize the list of images for the folder
            folder_structure[relative_folder] = []

            for file in files_in_dir:
                file_path = os.path.join(root, file)
                file_type, _ = mimetypes.guess_type(file_path)

                is_image = file_type and file_type.startswith('image')

                if is_image:
                    with open(file_path, 'rb') as image_file:
                        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

                    # Append the image and file name to the folder
                    folder_structure[relative_folder].append({
                        'file_name': file,
                        'encoded_image': encoded_image,
                        'is_image': True
                    })
                else:
                    folder_structure[relative_folder].append({
                        'file_name': file,
                        'file_path': file_path,
                        'is_image': False
                    })

    return render(request, 'view_directory.html', {
        'folder_structure': folder_structure,
        'collection_name': collection.Collection_Name,
        'username': request.user.username,
    })

@login_required
def workspaces(request):
    username = request.user.username
    user_instance = User.objects.get(username=username)
    # Query the Metadata table for different categories
    public_datasets = Files.objects.filter(Repository='public')
    private_datasets = Files.objects.filter(Username=user_instance, Repository='private')
    favorite_datasets = Files.objects.filter(Username=user_instance, Repository='favorites')

    # Create a dictionary to pass the datasets to the template
    datasets = {
        'Public': public_datasets,
        'Private': private_datasets,
        'Favorites': favorite_datasets
    }

    context = {
        'datasets': datasets,
        'username': username  # Include username in the context
    }

    return render(request, 'workspaces.html', context)

import requests
# for visualization server manager.

@login_required
def visualization_server_manager(request):
    username = request.user.username
    return render(request, 'visualization_server_manager.html', {'username': username})

@login_required
@csrf_protect
@require_http_methods(["POST"])
def start_server(request, server_type):
    manager = server_manager_proxy.get_manager()
    if manager is None:
        return JsonResponse({'error': 'Server manager not initialized'}, status=500)
    
    try:
        # Map server_type to route prefix and normalized type
        type_mapping = {
            'basic': {'route_prefix': 'histogram', 'server_type': 'basic'},
            'general': {'route_prefix': 'histogramgeneral', 'server_type': 'general'},
            'ood': {'route_prefix': 'analyzer', 'server_type': 'analyzer'},
            'analyzer': {'route_prefix': 'analyzer', 'server_type': 'analyzer'}
        }
        
        if server_type not in type_mapping:
            return JsonResponse({'error': 'Invalid server type'}, status=400)
            
        mapped_type = type_mapping[server_type]
        normalized_type = mapped_type['server_type']
        route_prefix = mapped_type['route_prefix']
            
        # Start the appropriate server
        if normalized_type == 'basic':
            manager.start_new_basic_server()
        elif normalized_type == 'general':
            manager.start_new_general_server()
        elif normalized_type == 'analyzer':
            manager.start_new_ood_server()
        
        # Get the port that was just used
        port = manager.next_port - 1
        
        # Save server instance to database
        server_instance = ServerInstance.objects.create(
            server_type=normalized_type,
            port=port,
            ip='localhost',
            is_running=True,
            started_at=timezone.now()
        )
        
        # Find the next available number for this route type
        existing_count = UpstreamServer.objects.filter(
            route__startswith=route_prefix
        ).count()
        
        route = f"{route_prefix}{existing_count + 1}"
        display_name = f"{normalized_type.title()} Server {existing_count + 1}"
        
        upstream_server = UpstreamServer.objects.create(
            ip=server_instance.ip,
            port=server_instance.port,
            route=route,
            display_name=display_name
        )
        
        return JsonResponse({
            'status': 'success',
            'port': port,
            'route': route,
            'display_name': display_name
        })
    except Exception as e:
        logger.error(f"Error starting {server_type} server: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_protect
@require_http_methods(["POST"])
def stop_server(request, server_type, port):
    manager = server_manager_proxy.get_manager()
    if manager is None:
        return JsonResponse({'error': 'Server manager not initialized'}, status=500)
    
    try:
        # Map server_type to normalized type
        type_mapping = {
            'basic': 'basic',
            'general': 'general',
            'ood': 'analyzer',
            'analyzer': 'analyzer'
        }
        
        if server_type not in type_mapping:
            return JsonResponse({'error': 'Invalid server type'}, status=400)
        
        normalized_type = type_mapping[server_type]
        
        # Stop the appropriate server
        if normalized_type == 'basic':
            manager.stop_basic_server(port)
        elif normalized_type == 'general':
            manager.stop_general_server(port)
        elif normalized_type == 'analyzer':
            manager.stop_ood_server(port)
        
        # Get the server instance before deleting it to get its IP
        server_instance = ServerInstance.objects.get(port=port, server_type=normalized_type)
        
        # Delete the corresponding UpstreamServer entry
        UpstreamServer.objects.filter(ip=server_instance.ip, port=port).delete()
        
        # Delete server instance from database
        server_instance.delete()
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.error(f"Error stopping {server_type} server: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_server_status(request):
    try:
        # Get all running server instances
        server_instances = ServerInstance.objects.filter(is_running=True)
        
        # Initialize status dictionary with empty lists for each server type
        status = {
            'basic': [],
            'general': [],
            'ood': []  # Changed from 'analyzer' to 'ood' for frontend display
        }
        
        # Map server types to display types
        type_mapping = {
            'basic': 'basic',
            'general': 'general',
            'analyzer': 'ood'  # Map 'analyzer' to 'ood' for frontend
        }
        
        # Get corresponding UpstreamServer entries for each server instance
        for instance in server_instances:
            try:
                upstream = UpstreamServer.objects.get(ip=instance.ip, port=instance.port)
                display_type = type_mapping.get(instance.server_type, instance.server_type)
                
                status[display_type].append({
                'port': instance.port,
                'ip': instance.ip,
                    'status': 'Running',
                    'started_at': instance.started_at.isoformat() if instance.started_at else None,
                    'route': upstream.route,
                    'display_name': upstream.display_name
                })
            except UpstreamServer.DoesNotExist:
                # If no upstream server entry exists, still include the server instance
                display_type = type_mapping.get(instance.server_type, instance.server_type)
                status[display_type].append({
                    'port': instance.port,
                    'ip': instance.ip,
                    'status': 'Running',
                    'started_at': instance.started_at.isoformat() if instance.started_at else None,
                    'route': None,
                    'display_name': f"{instance.server_type.title()} Server"
            })
            
        return JsonResponse(status)
    except Exception as e:
        logger.error(f"Error in get_server_status: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'status': {
                'basic': [],
                'general': [],
                'ood': []  # Changed from 'analyzer' to 'ood'
            }
        }, status=500)


# ... rest of the file ...
import logging
from django.http import HttpResponse, StreamingHttpResponse
from django.template import Template, Context
import requests
from urllib.parse import urljoin
import re


def new_view(request, path='', num=None):
    username = request.user.username
    logger.info(f"new_view called with path: '{path}', num: {num}")

    # Get all running histogram servers
    server_instances = ServerInstance.objects.filter(server_type='basic', is_running=True).order_by('port')
    
    # If num is provided directly (from URL pattern), use it
    if num is not None:
        histogram_num = num
    else:
        # Extract histogram number from path
        match = re.search(r'histogram(\d+)', path)
        histogram_num = int(match.group(1)) if match else 1

    # Get the corresponding server instance (1-based index)
    try:
        server = server_instances[0]  # Always use first server for this type
        BASE_URL = f'https://localhost:{server.port}'
    except IndexError:
        return HttpResponse(f"Basic Histogram server not found", status=404)

    AUTH_KEY = 'Zmlyc3Rfa2V5'  # First key for basic histogram
    
    try:
        session = requests.Session()
        
        # Map of file extensions to MIME types
        mime_types = {
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
            '.eot': 'application/vnd.ms-fontobject'
        }

        # Get file extension if it exists
        file_extension = os.path.splitext(path)[1].lower() if path else ''
        is_static_file = file_extension in mime_types

        # Step 1: Initial authentication request
        auth_url = f'{BASE_URL}?key={AUTH_KEY}'
        headers = {
            'Host': f'localhost:{server.port}',
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'X-Forwarded-For': '127.0.0.1',
            'X-Real-IP': '127.0.0.1'
        }

        logger.info(f"Making auth request to: {auth_url}")
        auth_response = session.get(
            auth_url,
            headers=headers,
            timeout=10,
            verify=False,
            allow_redirects=False
        )
        
        logger.info(f"Auth response status: {auth_response.status_code}")
        logger.info(f"Auth response headers: {dict(auth_response.headers)}")

        if auth_response.status_code == 302:
            auth_cookies = session.cookies.get_dict()
            logger.info(f"Received cookies: {auth_cookies}")

            # Step 2: Follow redirect with cookies
            redirect_url = auth_response.headers.get('Location', '/')
            if not redirect_url.startswith('http'):
                redirect_url = f'{BASE_URL}{redirect_url}'

            if 'csrf_token' in auth_cookies:
                headers['X-CSRF-Token'] = auth_cookies['csrf_token']
            
            cookie_header = '; '.join([f"{k}={v}" for k, v in auth_cookies.items()])
            headers['Cookie'] = cookie_header

            # Make the actual content request
            target_url = f'{BASE_URL}/{path}' if path else redirect_url
            logger.info(f"Making content request to: {target_url}")
            
            response = session.get(
                target_url,
                headers=headers,
                cookies=auth_cookies,
                timeout=30,
                verify=False,
                stream=True
            )
            
            logger.info(f"Content response status: {response.status_code}")
            
            if response.status_code == 200:
                if is_static_file:
                    return HttpResponse(
                        response.content,
                        content_type=mime_types[file_extension]
                    )

                content = response.text
                # Update WebSocket URLs to use our proxy
                content = content.replace(
                    f'ws://{BASE_URL.replace("https://", "")}',
                    f'ws://{request.get_host()}/histogram{histogram_num}'
                )
                content = content.replace(
                    BASE_URL,
                    f'https://{request.get_host()}/histogram{histogram_num}'
                )

                # Get all available histogram servers for the navigation
                histogram_servers = [
                    {'number': i+1, 'port': s.port} 
                    for i, s in enumerate(server_instances)
                ]

                django_response = render(request, 'histogram.html', {
                    'username': username,
                    'proxied_content': content,
                    'histogram_servers': histogram_servers,
                    'current_histogram': str(histogram_num)
                })

                for name, value in auth_cookies.items():
                    django_response.set_cookie(
                        name,
                        value,
                        path='/',
                        secure=False,
                        httponly=True,
                        samesite='Lax'
                    )

                return django_response
            else:
                raise Exception(f"Content request failed with status {response.status_code}")
        else:
            raise Exception(f"Authentication failed with status {auth_response.status_code}")

    except Exception as e:
        logger.exception("Proxy error")
        error_details = {
            "error": "Proxy error",
            "details": str(e),
            "path": path,
            "auth_status": getattr(auth_response, 'status_code', None) if 'auth_response' in locals() else None,
            "auth_headers": dict(auth_response.headers) if 'auth_response' in locals() else None,
            "auth_cookies": session.cookies.get_dict() if 'session' in locals() else {},
            "content_status": getattr(response, 'status_code', None) if 'response' in locals() else None
        }
        return JsonResponse(error_details, status=500)


# ... rest of the file ...
import logging
from django.http import HttpResponse, StreamingHttpResponse
from django.template import Template, Context
import requests
from urllib.parse import urljoin
import re


def new_view2(request, path='', num=None):
    username = request.user.username
    logger.info(f"new_view2 called with path: '{path}', num: {num}")

    # Get all running general histogram servers
    server_instances = ServerInstance.objects.filter(server_type='general', is_running=True).order_by('port')
    
    # If num is provided directly (from URL pattern), use it
    if num is not None:
        histogram_num = num
    else:
        # Extract histogram number from path
        match = re.search(r'histogramgeneral(\d+)', path)
        histogram_num = int(match.group(1)) if match else 1

    # Get the corresponding server instance (1-based index)
    try:
        server = server_instances[0]  # Always use first server for this type
        BASE_URL = f'https://localhost:{server.port}'
    except IndexError:
        return HttpResponse(f"General Histogram server not found", status=404)

    AUTH_KEY = 'c2Vjb25kX2tleQ=='  # Second key for general histogram
    
    try:
        session = requests.Session()
        
        # Map of file extensions to MIME types
        mime_types = {
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
            '.eot': 'application/vnd.ms-fontobject'
        }

        # Get file extension if it exists
        file_extension = os.path.splitext(path)[1].lower() if path else ''
        is_static_file = file_extension in mime_types

        # Step 1: Initial authentication request
        auth_url = f'{BASE_URL}?key={AUTH_KEY}'
        headers = {
            'Host': f'localhost:{server.port}',
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'X-Forwarded-For': '127.0.0.1',
            'X-Real-IP': '127.0.0.1'
        }

        logger.info(f"Making auth request to: {auth_url}")
        auth_response = session.get(
            auth_url,
            headers=headers,
            timeout=10,
            verify=False,
            allow_redirects=False
        )
        
        logger.info(f"Auth response status: {auth_response.status_code}")
        logger.info(f"Auth response headers: {dict(auth_response.headers)}")

        if auth_response.status_code == 302:
            auth_cookies = session.cookies.get_dict()
            logger.info(f"Received cookies: {auth_cookies}")

            # Step 2: Follow redirect with cookies
            redirect_url = auth_response.headers.get('Location', '/')
            if not redirect_url.startswith('http'):
                redirect_url = f'{BASE_URL}{redirect_url}'

            if 'csrf_token' in auth_cookies:
                headers['X-CSRF-Token'] = auth_cookies['csrf_token']
            
            cookie_header = '; '.join([f"{k}={v}" for k, v in auth_cookies.items()])
            headers['Cookie'] = cookie_header

            # Make the actual content request
            target_url = f'{BASE_URL}/{path}' if path else redirect_url
            logger.info(f"Making content request to: {target_url}")
            
            response = session.get(
                target_url,
                headers=headers,
                cookies=auth_cookies,
                timeout=30,
                verify=False,
                stream=True
            )
            
            logger.info(f"Content response status: {response.status_code}")
            
            if response.status_code == 200:
                if is_static_file:
                    return HttpResponse(
                        response.content,
                        content_type=mime_types[file_extension]
                    )

                content = response.text
                # Update WebSocket URLs to use our proxy
                content = content.replace(
                    f'ws://{BASE_URL.replace("https://", "")}',
                    f'ws://{request.get_host()}/histogramgeneral{histogram_num}'
                )
                content = content.replace(
                    BASE_URL,
                    f'https://{request.get_host()}/histogramgeneral{histogram_num}'
                )

                # Get all available histogram servers for the navigation
                histogram_servers = [
                    {'number': i+1, 'port': s.port} 
                    for i, s in enumerate(server_instances)
                ]

                django_response = render(request, 'histogramgeneral.html', {
                    'username': username,
                    'proxied_content': content,
                    'histogram_servers': histogram_servers,
                    'current_histogram': str(histogram_num)
                })

                for name, value in auth_cookies.items():
                    django_response.set_cookie(
                        name,
                        value,
                        path='/',
                        secure=False,
                        httponly=True,
                        samesite='Lax'
                    )

                return django_response
            else:
                raise Exception(f"Content request failed with status {response.status_code}")
        else:
            raise Exception(f"Authentication failed with status {auth_response.status_code}")

    except Exception as e:
        logger.exception("Proxy error")
        error_details = {
            "error": "Proxy error",
            "details": str(e),
            "path": path,
            "auth_status": getattr(auth_response, 'status_code', None) if 'auth_response' in locals() else None,
            "auth_headers": dict(auth_response.headers) if 'auth_response' in locals() else None,
            "auth_cookies": session.cookies.get_dict() if 'session' in locals() else {},
            "content_status": getattr(response, 'status_code', None) if 'response' in locals() else None
        }
        return JsonResponse(error_details, status=500)


def new_view3(request, path='', num=None):
    username = request.user.username
    logger.info(f"new_view3 called with path: '{path}', num: {num}")

    # Get all running analyzer servers
    server_instances = ServerInstance.objects.filter(server_type='analyzer').order_by('port')
    
    # If num is provided directly (from URL pattern), use it
    if num is not None:
        analyzer_num = num
    else:
        # Extract analyzer number from path
        match = re.search(r'oodanalyzer(\d+)', path)
        analyzer_num = int(match.group(1)) if match else 1

    # Get the corresponding server instance (1-based index)
    try:
        server = server_instances[0]  # Always use first server for this type
        BASE_URL = f'https://localhost:{server.port}'
    except IndexError:
        return HttpResponse(f"OOD Analyzer server not found", status=404)

    AUTH_KEY = 'a2V5'  # Third key for analyzer
    SESSION_PREFIX = 'analyzer_'  # Unique prefix for analyzer sessions
    
    try:
        session = requests.Session()
        
        # Map of file extensions to MIME types
        mime_types = {
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
            '.eot': 'application/vnd.ms-fontobject'
        }

        # Get file extension if it exists
        file_extension = os.path.splitext(path)[1].lower() if path else ''
        is_static_file = file_extension in mime_types

        # Check if we have existing analyzer cookies
        has_valid_session = False
        if request.COOKIES:
            analyzer_cookies = {k[len(SESSION_PREFIX):]: v for k, v in request.COOKIES.items() if k.startswith(SESSION_PREFIX)}
            if analyzer_cookies:
                # Try using existing session
                headers = {
                    'Host': f'localhost:{server.port}',
                    'User-Agent': 'Mozilla/5.0',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive',
                    'X-Forwarded-For': '127.0.0.1',
                    'X-Real-IP': '127.0.0.1',
                    'X-Analyzer-Request': 'true',
                    'Cookie': '; '.join([f"{k}={v}" for k, v in analyzer_cookies.items()])
                }
                
                # Try a request with existing cookies
                test_response = session.get(
                    BASE_URL,
                    headers=headers,
                    verify=False,
                    allow_redirects=False
                )
                has_valid_session = test_response.status_code in [200, 302]
                if has_valid_session:
                    session.cookies.update(analyzer_cookies)

        # If no valid session, authenticate
        if not has_valid_session:
            # Step 1: Initial authentication request with unique analyzer headers
            auth_url = f'{BASE_URL}?key={AUTH_KEY}'
            headers = {
                'Host': f'localhost:{server.port}',
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'X-Forwarded-For': '127.0.0.1',
                'X-Real-IP': '127.0.0.1',
                'X-Analyzer-Request': 'true'
            }

            logger.info(f"Making analyzer auth request to: {auth_url}")
            auth_response = session.get(
                auth_url,
                headers=headers,
                timeout=10,
                verify=False,
                allow_redirects=False
            )
            
            logger.info(f"Analyzer auth response status: {auth_response.status_code}")
            logger.info(f"Analyzer auth response headers: {dict(auth_response.headers)}")

            if auth_response.status_code not in [200, 302]:
                raise Exception(f"Analyzer authentication failed with status {auth_response.status_code}")

        # Make the content request
        target_url = f'{BASE_URL}/{path}' if path else BASE_URL
        logger.info(f"Making analyzer content request to: {target_url}")
        
        # Update headers with any new cookies and CSRF token
        if 'csrf_token' in session.cookies:
            headers['X-CSRF-Token'] = session.cookies['csrf_token']
        
        headers['Cookie'] = '; '.join([f"{k}={v}" for k, v in session.cookies.items()])
            
        response = session.get(
            target_url,
            headers=headers,
            timeout=30,
            verify=False,
            stream=True
        )
        
        logger.info(f"Analyzer content response status: {response.status_code}")
            
        if response.status_code == 200:
            if is_static_file:
                return HttpResponse(
                    response.content,
                    content_type=mime_types[file_extension]
                )

            content = response.text
            # Update WebSocket URLs to use our proxy with unique analyzer path
            content = content.replace(
                f'ws://{BASE_URL.replace("https://", "")}',
                f'ws://{request.get_host()}/oodanalyzer{analyzer_num}'
            )
            content = content.replace(
                BASE_URL,
                f'https://{request.get_host()}/oodanalyzer{analyzer_num}'
            )

            # Get all available analyzer servers for the navigation
            analyzer_servers = [
                    {'number': i+1, 'port': s.port} 
                    for i, s in enumerate(server_instances)
                ]

            django_response = render(request, 'oodanalyzer.html', {
                'username': username,
                'proxied_content': content,
                'analyzer_servers': analyzer_servers,
                'current_analyzer': str(analyzer_num)
            })

            # Set cookies with unique analyzer prefix
            for name, value in session.cookies.items():
                django_response.set_cookie(
                    f"{SESSION_PREFIX}{name}",
                    value,
                    path='/oodanalyzer',  # Scope cookies to analyzer paths only
                    secure=False,
                    httponly=True,
                    samesite='Lax'
                )

            return django_response
        else:
            raise Exception(f"Analyzer content request failed with status {response.status_code}")

    except Exception as e:
        logger.exception("Analyzer proxy error")
        error_details = {
            "error": "Analyzer proxy error",
            "details": str(e),
            "path": path,
            "auth_status": getattr(auth_response, 'status_code', None) if 'auth_response' in locals() else None,
            "auth_headers": dict(auth_response.headers) if 'auth_response' in locals() else None,
            "auth_cookies": session.cookies.get_dict() if 'session' in locals() else {},
            "content_status": getattr(response, 'status_code', None) if 'response' in locals() else None
        }
        return JsonResponse(error_details, status=500)


@login_required
def csv_data(request, file_uuid):
    try:
        # Get the file from the database
        file_obj = Files.objects.get(UUID=file_uuid)
        
        # Check if user has access to this file
        if file_obj.Repository == 'private' and file_obj.Username != request.user:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Get the datastore manager and retrieve the file
        manager = getDataStoreManager()
        datastore = manager.getDatastore(str(file_obj.Datastore_UUID.UUID))
        
        if not datastore:
            return JsonResponse({'error': 'Datastore not found'}, status=404)
        
        # Get the file path
        file_path = os.path.join(datastore['path'], str(file_uuid), file_obj.Name)
        
        # Get query parameters
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 100))
        search = request.GET.get('search', '').strip()
        
        # Calculate the number of rows to skip
        skiprows = (page - 1) * limit
        
        # First, read only the header
        headers = pd.read_csv(file_path, nrows=0).columns.tolist()
        
        # If searching, we need to load chunks and search through them
        if search:
            chunks = []
            for chunk in pd.read_csv(file_path, chunksize=10000):
                # Search across all columns
                mask = chunk.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
                filtered_chunk = chunk[mask]
                chunks.append(filtered_chunk)
                
                # If we have enough rows for this page, we can stop reading
                total_rows = sum(len(chunk) for chunk in chunks)
                if total_rows >= skiprows + limit:
                    break
            
            # Combine all chunks
            if chunks:
                df = pd.concat(chunks, ignore_index=True)
                total_rows = len(df)
                # Get the rows for current page
                page_data = df.iloc[skiprows:skiprows + limit]
            else:
                total_rows = 0
                page_data = pd.DataFrame(columns=headers)
        else:
            # If not searching, we can use more efficient skiprows and nrows parameters
            try:
                # Get total number of rows efficiently
                total_rows = sum(1 for _ in open(file_path)) - 1  # subtract 1 for header
                
                # Read only the required rows
                page_data = pd.read_csv(
                    file_path,
                    skiprows=range(1, skiprows + 1) if skiprows else None,  # skip header + previous rows
                    nrows=limit,
                    memory_map=True  # Use memory mapping for large files
                )
            except Exception as e:
                logger.error(f"Error reading CSV file: {str(e)}")
                return JsonResponse({'error': 'Error reading file'}, status=500)
        
        # Convert to dictionary format
        rows = page_data.to_dict('records')
        
        return JsonResponse({
            'headers': headers,
            'rows': rows,
            'total': total_rows
        })
        
    except Files.DoesNotExist:
        return JsonResponse({'error': 'File not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in csv_data view: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def data_explorer(request, file_uuid):
    try:
        # Get the file from the database
        file_obj = Files.objects.get(UUID=file_uuid)
        
        # Check if user has access to this file
        if file_obj.Repository == 'private' and file_obj.Username != request.user:
            messages.error(request, 'Access denied')
            return redirect('datasets')
        
        context = {
            'username': request.user.username,
            'file': {
                'uuid': str(file_uuid),
                'name': file_obj.Name,
                'description': file_obj.Description
            }
        }
        
        return render(request, 'data_explorer.html', context)
        
    except Files.DoesNotExist:
        messages.error(request, 'File not found')
        return redirect('datasets')

@login_required
def chat_with_data(request, file_uuid):
    try:
        # Get the file from the database
        file_obj = Files.objects.get(UUID=file_uuid)
        
        # Check if user has access to this file
        if file_obj.Repository == 'private' and file_obj.Username != request.user:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Get the datastore manager and retrieve the file
        manager = getDataStoreManager()
        datastore = manager.getDatastore(str(file_obj.Datastore_UUID.UUID))
        
        if not datastore:
            return JsonResponse({'error': 'Datastore not found'}, status=404)
        
        # Get the file path
        file_path = os.path.join(datastore['path'], str(file_uuid), file_obj.Name)
        
        # Get the question from the request
        data = json.loads(request.body)
        question = data.get('question', '').strip()
        
        if not question:
            return JsonResponse({'error': 'No question provided'}, status=400)
        
        try:
            # Read the CSV file
            df = pd.read_csv(file_path)
            
            # Process the question and generate a response
            # This is where you would integrate the csvGPT logic
            # For now, we'll return a simple analysis
            response = analyze_data(df, question)
            
            return JsonResponse({
                'response': response
            })
            
        except Exception as e:
            logger.error(f"Error processing chat request: {str(e)}")
            return JsonResponse({'error': 'Error processing request'}, status=500)
        
    except Files.DoesNotExist:
        return JsonResponse({'error': 'File not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in chat_with_data view: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def analyze_data(df, question):
    """
    Analyze the dataframe based on the user's question.
    This is a placeholder for the csvGPT integration.
    """
    try:
        # Basic analysis based on common questions
        question_lower = question.lower()
        
        if 'how many' in question_lower or 'count' in question_lower:
            return f"The dataset contains {len(df)} rows."
            
        if 'columns' in question_lower or 'fields' in question_lower:
            columns = ', '.join(df.columns.tolist())
            return f"The dataset contains the following columns: {columns}"
            
        if 'missing' in question_lower or 'null' in question_lower:
            missing_info = df.isnull().sum().to_dict()
            missing_str = ', '.join([f"{k}: {v}" for k, v in missing_info.items() if v > 0])
            return f"Missing values in the dataset: {missing_str if missing_str else 'No missing values found.'}"
            
        if 'summary' in question_lower or 'describe' in question_lower:
            numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
            if len(numeric_cols) > 0:
                summary = df[numeric_cols].describe().to_dict()
                return f"Statistical summary of numeric columns: {json.dumps(summary, indent=2)}"
            else:
                return "No numeric columns found in the dataset."
        
        # Default response
        return "I can help you analyze this data. Try asking about the number of rows, columns, missing values, or statistical summaries."
        
    except Exception as e:
        logger.error(f"Error analyzing data: {str(e)}")
        return "Sorry, I encountered an error while analyzing the data."

@login_required
def data_explorer_main(request):
    """Main page for the data explorer that lists available CSV files."""
    user_instance = request.user
    
    # Get all CSV files the user has access to (filter by .csv extension)
    public_files = Files.objects.filter(
        Repository='public',
        Name__iendswith='.csv'
    ).order_by('-Created')
    
    private_files = Files.objects.filter(
        Repository='private',
        Username=user_instance,
        Name__iendswith='.csv'
    ).order_by('-Created')
    
    # Prepare file information with additional details
    def prepare_file_info(files_queryset):
        file_info = []
        for file in files_queryset:
            info = {
                'uuid': str(file.UUID),
                'name': file.Name,
                'description': file.Description,
                'created': file.Created,
                'username': file.Username.username if file.Username else None,
                'datastore': file.Datastore_UUID.Name if file.Datastore_UUID else None
            }
            file_info.append(info)
        return file_info

    context = {
        'username': user_instance.username,
        'public_files': prepare_file_info(public_files),
        'private_files': prepare_file_info(private_files),
        'title': 'Data Explorer',
        'description': 'Explore and analyze your CSV files using AI'
    }
    
    return render(request, 'data_explorer.html', context)

@require_http_methods(["POST"])
def analyze_data(request, file_uuid):
    try:
        logger.info(f"Analyzing data for file UUID: {file_uuid}")
        
        # Get the file metadata
        file_obj = Files.objects.get(UUID=file_uuid)
        logger.info(f"Found file: {file_obj.Name}")
        
        # Get the datastore manager and retrieve the file path
        manager = getDataStoreManager()
        datastore = manager.getDatastore(str(file_obj.Datastore_UUID.UUID))
        
        if not datastore:
            logger.error(f"Datastore not found for UUID: {file_obj.Datastore_UUID.UUID}")
            return JsonResponse({'success': False, 'error': 'Datastore not found'}, status=404)
        
        # Construct the full file path
        file_path = os.path.join(datastore['path'], str(file_uuid), file_obj.Name)
        logger.info(f"Constructed file path: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"File not found at path: {file_path}")
            return JsonResponse({'success': False, 'error': 'File not found'}, status=404)
        
        # Load the data
        logger.info("Loading CSV file...")
        df = pd.read_csv(file_path)
        logger.info(f"Loaded CSV with {len(df)} rows and {len(df.columns)} columns")
        
        # Parse the request
        data = json.loads(request.body)
        command = data.get('command')
        params = data.get('params', {})
        logger.info(f"Processing command: {command} with params: {params}")
        
        # Initialize analyzer and process command
        analyzer = DataAnalyzer(df)
        result = analyzer.process_command(command, params)
        logger.info("Command processed successfully")
        
        return JsonResponse(result)
        
    except Files.DoesNotExist:
        logger.error(f"File not found with UUID: {file_uuid}")
        return JsonResponse({'success': False, 'error': 'File not found'}, status=404)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return JsonResponse({'success': False, 'error': 'Invalid JSON in request body'}, status=400)
    except Exception as e:
        logger.error(f"Error in analyze_data: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)










