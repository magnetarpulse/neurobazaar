from django.http import FileResponse, HttpResponse, Http404
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models.deletion import ProtectedError
from home.models import Collections, Files, Datastores, LocalFSDatastores, MongoDBDatastores

from neurobazaar.services.datastorage.datastore_manager import getDataStoreManager
from neurobazaar.services.datastorage.localfs_datastore import LocalFSDatastore

import shutil
import sys
import os

cwd = os.getcwd()
index = cwd.index('neurobazaar')
neurobazaar_dir = cwd[:index + len('neurobazaar')]
sys.path.insert(0, neurobazaar_dir)

import time
import uuid
import json

import mimetypes
import base64

def index(request):
    """
    Renders the index page.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: The rendered index page with the username if the user is authenticated.
    """
    username = None
    if request.user.is_authenticated:
        username = request.user.username
    return render(request, 'index.html', {'username': username})

def team_details(request):
    """
    Renders the team details page.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: The rendered team details page.
    """
    return render(request, 'team-details.html')

def logoutUser(request):
    """
    Logs out the current user and redirects to the login/register page.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: A redirect to the login/register page.
    """
    logout(request)
    return redirect('/login_register')

def download_collection(collection_uuid):
    """
    Downloads a collection as a zip file.

    Args:
        collection_uuid (str): The UUID of the collection to download.

    Returns:
        HttpResponse: The zip file containing the collection.

    Raises:
        Http404: If the collection or datastore is not found.
    """
    try:
        collection = Collections.objects.get(Collections_UUID=collection_uuid)
        datastore_instance = collection.Datastore_UUID

        manager = getDataStoreManager()
        datastore = manager.getDatastore(str(datastore_instance.UUID))

        if not datastore:
            raise Http404("Datastore not found.")

        collection_path = datastore.getCollection(str(collection_uuid))
        if not collection_path:
            raise Http404("Collection not found.")

        zip_path = os.path.join('/tmp', f"{collection_uuid}.zip")

        shutil.make_archive(zip_path.replace('.zip', ''), 'zip', collection_path)

        with open(zip_path, 'rb') as f:
            response = HttpResponse(f, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{collection_uuid}.zip"'
            return response

    except Collections.DoesNotExist:
        raise Http404("Collection metadata not found.")
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)

def datastore(request):
    """
    Handles adding and removing datastores.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: The rendered datastore page with the list of datastores.

    Raises:
        ProtectedError: If attempting to remove a datastore that is still referenced by other objects.
    """
    username = request.user.username

    if request.method == 'POST':
        if 'add_datastore' in request.POST:
            database_type = request.POST.get('database')
            if database_type == 'filesystem':
                path = request.POST.get('destination_path')
                datastore_name = request.POST.get('datastore_name')
                manager = getDataStoreManager()
                datastore_id = uuid.uuid4()
                manager.addLocalFSDatastore(datastore_id, path)
                new_local_fs = LocalFSDatastores(
                    UUID=str(datastore_id),  
                    Name=datastore_name,
                    Type="filesystem",
                    Connected=True,
                    Directory_Path=path 
                )
                new_local_fs.save()

            elif database_type == 'mongodb':
                host = request.POST.get('host_mongo')
                port = request.POST.get('port_mongo')
                username = request.POST.get('username_mongo')
                password = request.POST.get('password_mongo')
                database = request.POST.get('database_mongo')
                datastore_name = request.POST.get('datastore_name_mongo')
                datastore_id = uuid.uuid4()
                manager = getDataStoreManager()
                manager.addMongoDBDatastore(str(datastore_id), username, password, host, port, database)

                new_mongodb = MongoDBDatastores(
                    UUID=str(datastore_id),
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
                
        elif 'remove_datastore' in request.POST:
            datastore_id = request.POST.get('datastore_id')
            manager = getDataStoreManager()
            
            try:
                manager.removeDataStore(datastore_id)
                Datastores.objects.filter(UUID=datastore_id).delete()
                messages.success(request, "Datastore removed successfully.")
            except ProtectedError as e:
                return render(request, 'datastore.html', {
                    'protected_error': "Cannot delete this datastore because it is still referenced by other objects.",
                    'datastores': Datastores.objects.all()
                })

    datastores = Datastores.objects.all()
    return render(request, 'datastore.html', {'datastores': datastores, 'username': username})
    
def login_register(request):
    """
    Handles the login and registration functionality.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: The rendered login/register page with appropriate form visibility.
    """
    login_form_visible = True
    register_form_visible = False

    if request.method == 'POST':
        if 'login_submit' in request.POST:
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('/')
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
                user = User.objects.create_user(username=username, password=password1)
                user.save()
                messages.success(request, 'Account created successfully. You can now login.')
                return redirect('/login_register')

    return render(request, 'login_register.html', {'login_form_visible': login_form_visible, 'register_form_visible': register_form_visible})

@login_required
def datasets(request):
    """
    Handles dataset-related actions including upload, download, and like/dislike functionality.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: The rendered datasets page with the list of datasets, collections, and user information.
    """
    username = request.user.username
    user_instance = User.objects.get(username=username) 

    upload_time = None  
    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'dataset_upload':
            start_time = float(request.session.get('uploadStartTime', time.time() * 1000)) / 1000
            dname = request.FILES.get('dataset_file')
            description = request.POST['description']
            repo = request.POST['repo']
            datastore = request.POST['datastore']
            datastore_instance = Datastores.objects.get(UUID=datastore)
                
            manager = getDataStoreManager()
            datastore = manager.getDatastore(datastore)
            datasetid = datastore.putDataset(dname)
                
            metadata = Files(
                Username=user_instance,
                Name=dname.name,
                UUID=datasetid,
                Datastore_UUID=datastore_instance,
                Description=description,
                Repository=repo,
                Created=timezone.now().date(), 
            )
            metadata.save()
            end_time = time.time()
            upload_time = end_time - start_time
                
            messages.info(request, f"File uploaded in {upload_time:.4f} seconds.")
            return redirect('datasets')

        elif form_type == 'collection_upload':
            files = request.FILES.getlist('collection_files')
            description = request.POST.get('description', '')
            repo = request.POST.get('repo', '')
            dataset_uuid = request.POST.get('dataset_uuid')
            relative_paths = json.loads(request.POST.get('relative_paths', '[]'))

            related_dataset = Files.objects.get(UUID=dataset_uuid)
            datastore_instance = related_dataset.Datastore_UUID
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
                    Dataset_UUID=related_dataset,
                    Collection_Name=collection_name,
                    Repository=repo,
                    Created=timezone.now().date(),
                    Modified=timezone.now().date(),
                )
                collection_model_instance.save()
                
                Files.objects.filter(UUID=related_dataset.UUID).update(
                    Collections_UUID=collection_model_instance,
                    Collection_Name=collection_name
                )

                end_time = time.time()
                upload_time = end_time - start_time
                messages.info(request, f"Collection uploaded in {upload_time:.4f} seconds.")
                return redirect('datasets')
          
        elif 'like_file' in request.POST:
            file_id = request.POST['like_file']
            metadata = Files.objects.get(id=file_id)
            metadata.likes += 1
            metadata.save()
            return redirect('datasets')

        elif 'dislike_file' in request.POST:
            file_id = request.POST['dislike_file']
            metadata = Files.objects.get(id=file_id)
            metadata.dislikes += 1
            metadata.save()
            return redirect('datasets')

        elif 'copy_to_favorites' in request.POST:
            file_id = request.POST['copy_to_favorites']
            metadata = Files.objects.get(id=file_id)
            
            if not Files.objects.filter(user=username, dname=metadata.dname, repo='favorites').exists():
                favorite_metadata = Files(
                    user=username,
                    dname=metadata.dname,
                    description=metadata.description,
                    repo='favorites',
                    date=timezone.now().date(),
                    time=timezone.now().time()
                )
                favorite_metadata.save()
                
            return redirect('datasets')

        elif 'delete_file' in request.POST:
            file_id = request.POST['delete_file']
            metadata = Files.objects.get(id=file_id)
            metadata.delete()
            return redirect('datasets')
        
        elif 'download_file' in request.POST:
            start_time = float(request.session.get('uploadStartTime', time.time() * 1000)) / 1000
            dataset_UUID = request.POST['download_file']
            dataset = Files.objects.get(UUID=dataset_UUID)
            manager = getDataStoreManager()
            datastore_instance = dataset.Datastore_UUID
            datastore = manager.getDatastore(str(datastore_instance.UUID))
            file_obj = datastore.getDataset(str(dataset.UUID))
            end_time = time.time()
            fetch_time = end_time - start_time
            print(f"fetch time: {fetch_time}")
            response = FileResponse(file_obj, as_attachment=True, filename=dataset.Name)
            return response

    user_instance = User.objects.get(username=username)
    public_datasets = Files.objects.filter(Repository='public')
    private_datasets = Files.objects.filter(Username=user_instance, Repository='private')
    favorite_datasets = Files.objects.filter(Username=user_instance, Repository='favorites')
    directories = Collections.objects.all()
    datastores = Datastores.objects.all()
    
    public_collections = Collections.objects.filter(Repository='public')
    private_collections = Collections.objects.filter(Dataset_UUID__Username=user_instance, Repository='private')
    favorite_collections = Collections.objects.filter(Dataset_UUID__Username=user_instance, Repository='favorites')

    context = {
        'public_datasets': public_datasets,
        'private_datasets': private_datasets,
        'favorite_datasets': favorite_datasets,
        'public_collections': public_collections,        
        'private_collections': private_collections,      
        'favorite_collections': favorite_collections,    
        'directories': directories,
        'datastores': datastores,
        'datasets': public_datasets | private_datasets,  
        'username': username,
        'upload_time': upload_time
    }

    return render(request, 'datasets.html', context)

@login_required
def view_directory(request, collections_uuid):
    """
    View function to display the directory structure of a collection.

    Args:
        request: The HTTP request object.
        collections_uuid: The UUID of the collection to be viewed.

    Returns:
        HttpResponse: Rendered HTML page displaying the directory structure of the collection.
    """
    collection = Collections.objects.get(Collections_UUID=collections_uuid)
    datastore_instance = collection.Datastore_UUID

    manager = getDataStoreManager()
    datastore = manager.getDatastore(str(datastore_instance.UUID))

    collection_path = None
    if isinstance(datastore, LocalFSDatastore):
        collection_path = datastore.getCollection(str(collection.Collections_UUID))
    else:
        raise AttributeError("The datastore is not a LocalFSDatastore and does not have a directory path.")

    folder_structure = {}

    if collection_path:
        for root, _, files_in_dir in os.walk(collection_path):
            relative_folder = os.path.relpath(root, collection_path)
            folder_structure[relative_folder] = []
            for file in files_in_dir:
                file_path = os.path.join(root, file)
                file_type, _ = mimetypes.guess_type(file_path)

                is_image = file_type and file_type.startswith('image')

                if is_image:
                    with open(file_path, 'rb') as image_file:
                        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

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
    """
    View function to display different workspaces for a user.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Rendered HTML page displaying the user's workspaces.
    """
    username = request.user.username
    user_instance = User.objects.get(username=username)

    public_datasets = Files.objects.filter(Repository='public')
    private_datasets = Files.objects.filter(Username=user_instance, Repository='private')
    favorite_datasets = Files.objects.filter(Username=user_instance, Repository='favorites')

    datasets = {
        'Public': public_datasets,
        'Private': private_datasets,
        'Favorites': favorite_datasets
    }

    context = {
        'datasets': datasets,
        'username': username 
    }

    return render(request, 'workspaces.html', context)

@login_required
def visualization_server_manager(request):
    """
    View function to manage visualization servers for a user.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Rendered HTML page for visualization server management.
    """
    username = request.user.username
    return render(request, 'visualization_server_manager.html', {'username': username})