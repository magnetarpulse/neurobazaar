import time
from django.http import FileResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models.deletion import ProtectedError

from home.models import Collections, Files, Datastores, LocalFSDatastores, MongoDBDatastores

from neurobazaar.services.datastorage.datastore_manager import getDataStoreManager

import os
import uuid
import json

from neurobazaar.services.datastorage.localfs_datastore import LocalFSDatastore


# Create your views here.
def index(request):
    username = None
    if request.user.is_authenticated:
        username = request.user.username
    return render(request, 'index.html', {'username': username})

def logoutUser(request):
    logout(request)
    return redirect('/login_register')

def datastore(request):
    username = request.user.username
    # Handle form submissions for adding or removing datastores
    if request.method == 'POST':
        if 'add_datastore' in request.POST:
            database_type = request.POST.get('database')
            if database_type == 'filesystem':
                path = request.POST.get('destination_path')
                datastore_name = request.POST.get('datastore_name')
                manager = getDataStoreManager()
                datastore_id = uuid.uuid4()
                manager.addLocalFSDatastore(datastore_id,path)
                new_local_fs = LocalFSDatastores(
                    UUID=str(datastore_id),  
                    Name=datastore_name,
                    Type = "filesystem",
                    Connected=True,
                    Directory_Path=path 
                )
                new_local_fs.save()
                # DataStores.objects.create(
                #     DataStore_ID=str(datastore_id),
                #     DataStore_Name='FileSystem',
                #     Destination_Path=path
                # )
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
                # Here we catch and handle the protected error
                return render(request, 'datastore.html', {
                    'protected_error': "Cannot delete this datastore because it is still referenced by other objects.",
                    'datastores': Datastores.objects.all()
                })

    datastores = Datastores.objects.all()
    return render(request, 'datastore.html', {'datastores': datastores, 'username': username})
    
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

    upload_time = None  
    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        # Handling Dataset Upload Form
        if form_type == 'dataset_upload':
                # Get the start time from session or calculate it based on form submission
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
                    Datastore_UUID = datastore_instance,
                    Description=description,
                    Repository=repo,
                    Created=timezone.now().date(), 
                )
                metadata.save()
                end_time = time.time()
                upload_time = end_time - start_time
                
                messages.info(request, f"File uploaded in {upload_time:.4f} seconds.")
                return redirect('datasets')  # Redirect to avoid resubmission of form

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
            file_id = request.POST['like_file']
            metadata = Files.objects.get(id=file_id)
            metadata.likes += 1
            metadata.save()
            return redirect('datasets')

        # Handling dislike action
        elif 'dislike_file' in request.POST:
            file_id = request.POST['dislike_file']
            metadata = Files.objects.get(id=file_id)
            metadata.dislikes += 1
            metadata.save()
            return redirect('datasets')

        # Handling copy to favorites action
        elif 'copy_to_favorites' in request.POST:
            file_id = request.POST['copy_to_favorites']
            metadata = Files.objects.get(id=file_id)
            
            # Check if the file is already in favorites to prevent duplication
            if not Files.objects.filter(user=username, dname=metadata.dname, repo='favorites').exists():
                # Create a new metadata entry for favorites
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

        # Handling delete action
        elif 'delete_file' in request.POST:
            file_id = request.POST['delete_file']
            metadata = Files.objects.get(id=file_id)
            metadata.delete()
            return redirect('datasets')
        
                # Handling download action
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

    # Load datasets and directories separately
    user_instance = User.objects.get(username=username)
    public_datasets = Files.objects.filter(Repository='public')
    private_datasets = Files.objects.filter(Username=user_instance, Repository='private')
    favorite_datasets = Files.objects.filter(Username=user_instance, Repository='favorites')
    directories = Collections.objects.all()
    datastores = Datastores.objects.all()
    
     # Filter collections by repository type
    public_collections = Collections.objects.filter(Repository='public')
    private_collections = Collections.objects.filter(Dataset_UUID__Username=user_instance, Repository='private')
    favorite_collections = Collections.objects.filter(Dataset_UUID__Username=user_instance, Repository='favorites')

    context = {
        'public_datasets': public_datasets,
        'private_datasets': private_datasets,
        'favorite_datasets': favorite_datasets,
        'public_collections': public_collections,  # Pass public collections
        'private_collections': private_collections,  # Pass private collections
        'favorite_collections': favorite_collections,  # Pass favorite collections
        'directories': directories,
        'datastores': datastores,
        'datasets': public_datasets | private_datasets,  # Pass datasets to the template
        'username': username,
        'upload_time': upload_time
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


# for visualization server manager.

@login_required
def visualization_server_manager(request):
    username = request.user.username
    return render(request, 'visualization_server_manager.html', {'username': username})