import time
from django.http import FileResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models.deletion import ProtectedError
from home.models import Datasets, Datastores, LocalFSDatastores, MongoDBDatastores
from neurobazaar.services.datastorage.datastore_manager import getDataStoreManager
import os
import uuid

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
        
        elif 'connect_datastore' in request.POST:
            datastore_id = request.POST.get('connect_datastore')
            try:
                datastore = Datastores.objects.get(UUID=datastore_id)
                datastore.Connected = True
                datastore.save()
                messages.success(request, f"{datastore.Name} connected successfully.")
            except Datastores.DoesNotExist:
                messages.error(request, "Datastore not found.")

        elif 'disconnect_datastore' in request.POST:
            datastore_id = request.POST.get('disconnect_datastore')
            try:
                datastore = Datastores.objects.get(UUID=datastore_id)
                datastore.Connected = False
                datastore.save()
                messages.success(request, f"{datastore.Name} disconnected successfully.")
            except Datastores.DoesNotExist:
                messages.error(request, "Datastore not found.")


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
    upload_time = None  
    if request.method == 'POST':
        # Handling file upload and dataset creation
        if 'dname' in request.FILES and 'description' in request.POST and 'repo' in request.POST:
            # Get the start time from session or calculate it based on form submission
            start_time = float(request.session.get('uploadStartTime', time.time() * 1000)) / 1000
            dname = request.FILES.get('dname')
            description = request.POST['description']
            repo = request.POST['repo']
            datastore = request.POST['datastore']
            datastore_instance = Datastores.objects.get(UUID=datastore)
            user_instance = User.objects.get(username=username)
            
            manager = getDataStoreManager()
            datastore = manager.getDatastore(datastore)
            datasetid = datastore.putDataset(dname)
            
            metadata = Datasets(
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
            
        elif 'like_file' in request.POST or 'dislike_file' in request.POST:
            action = 'like_file' if 'like_file' in request.POST else 'dislike_file'
            file_id = request.POST[action]
            dataset = Datasets.objects.get(UUID=file_id)
            if action == 'like_file':
                dataset.Likes += 1
            else:
                dataset.Dislikes += 1
            dataset.save()
            return redirect('datasets')

        elif 'copy_to_favorites' in request.POST:
            file_id = request.POST['copy_to_favorites']
            dataset = Datasets.objects.get(UUID=file_id)
            if not Datasets.objects.filter(Username=user_instance, UUID=file_id, Repository='favorites').exists():
                dataset.pk = None
                dataset.Repository = 'favorites'
                dataset.save()
            return redirect('datasets')

        elif 'delete_file' in request.POST:
            file_id = request.POST['delete_file']
            dataset = Datasets.objects.get(UUID=file_id)
            dataset.delete()
            return redirect('datasets')
        
                # Handling download action
        elif 'download_file' in request.POST:
            start_time = float(request.session.get('uploadStartTime', time.time() * 1000)) / 1000
            dataset_UUID = request.POST['download_file']
            dataset = Datasets.objects.get(UUID=dataset_UUID)
            manager = getDataStoreManager()
            datastore_instance = dataset.Datastore_UUID
            datastore = manager.getDatastore(str(datastore_instance.UUID))
            file_obj = datastore.getDataset(str(dataset.UUID))
            end_time = time.time()
            fetch_time = end_time - start_time
            response = FileResponse(file_obj, as_attachment=True, filename=dataset.Name)
            return response

    user_instance = User.objects.get(username=username)
    # Query the Metadata table for different categories
    public_datasets = Datasets.objects.filter(Repository='public')
    private_datasets = Datasets.objects.filter(Username=user_instance, Repository='private')
    favorite_datasets = Datasets.objects.filter(Username=user_instance, Repository='favorites')
    datastores = Datastores.objects.all()

    context = {
        'public_datasets': public_datasets,
        'private_datasets': private_datasets,
        'favorite_datasets': favorite_datasets,
        'datastores': datastores,
        'username': username,  # Include username in the context
        'upload_time': upload_time
    }

    return render(request, 'datasets.html', context)

@login_required
def workspaces(request):
    username = request.user.username
    user_instance = User.objects.get(username=username)
    # Query the Metadata table for different categories
    public_datasets = Datasets.objects.filter(Repository='public')
    private_datasets = Datasets.objects.filter(Username=user_instance, Repository='private')
    favorite_datasets = Datasets.objects.filter(Username=user_instance, Repository='favorites')

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
