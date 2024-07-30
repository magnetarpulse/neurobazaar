import time
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from home.models import User, Datasets, Datastores, LocalFSDatastores, MongoDBDatastores

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
    # Handle form submissions for adding or removing datastores
    if request.method == 'POST':
        if 'add_datastore' in request.POST:
            database_type = request.POST.get('database')
            if database_type == 'filesystem':
                path = request.POST.get('destination_path')
                manager = getDataStoreManager()
                datastore_id = manager.addFSDataStore(path)
                new_local_fs = LocalFSDatastores(
                    DataStore_ID=str(datastore_id),  
                    DataStore_Name="filesystem",
                    Destination_Path=path 
                )
                new_local_fs.save()
                # DataStores.objects.create(
                #     DataStore_ID=str(datastore_id),
                #     DataStore_Name='FileSystem',
                #     Destination_Path=path
                # )
            elif database_type == 'mongodb': 
                host = request.POST.get('host')
                port = request.POST.get('port')
                username = request.POST.get('username')
                password = request.POST.get('password')
                database = request.POST.get('database')
                collection = request.POST.get('collection') 
                datastore_name = request.POST.get('datastore_name')
                datastore_id = uuid.uuid4()
                manager = getDataStoreManager()
                manager.addMongoDBDatastore(username, password, host, port, database)
                
                new_mongodb = MongoDBDatastores(
                    UUID=str(datastore_id),
                    Name=datastore_name,
                    Type="mongodb",
                    Connected=True,
                    Host=host,
                    Port=port,
                    Username=username,
                    Password=password,
                    Database=database,
                    Collection=collection
                )
                new_mongodb.save()
                
        elif 'remove_datastore' in request.POST:
            datastore_id = request.POST.get('datastore_id')
            manager = getDataStoreManager()
            manager.removeDataStore(datastore_id)
            Datastores.objects.filter(UUID=datastore_id).delete()

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
            dname = request.FILES.get('dname')
            description = request.POST['description']
            repo = request.POST['repo']
            datastore = request.POST['datastore']
            
            start_time = time.perf_counter()
            
            metadata = Datasets(
                User=username,
                Name=dname.name,
                UUID=uuid.uuid4(),
                Datastore_UUID = datastore,
                Description=description,
                Repository=repo,
                Created=timezone.now().date(), 
            )
            metadata.save()
            
            manager = getDataStoreManager()
            datastore = manager.getDatastore(datastore)
            datasetid = str(metadata.UUID) 
            datastore.putDataset(datasetid, dname)
            
            end_time = time.perf_counter()
            upload_time = end_time - start_time
            print(f"Upload time: {upload_time}")
            
            messages.info(request, f"File uploaded in {upload_time:.2f} seconds.")
            return redirect('datasets')  # Redirect to avoid resubmission of form
            
        # Handling like action
        elif 'like_file' in request.POST:
            file_id = request.POST['like_file']
            metadata = Datasets.objects.get(id=file_id)
            metadata.likes += 1
            metadata.save()
            return redirect('datasets')

        # Handling dislike action
        elif 'dislike_file' in request.POST:
            file_id = request.POST['dislike_file']
            metadata = Datasets.objects.get(id=file_id)
            metadata.dislikes += 1
            metadata.save()
            return redirect('datasets')

        # Handling copy to favorites action
        elif 'copy_to_favorites' in request.POST:
            file_id = request.POST['copy_to_favorites']
            metadata = Datasets.objects.get(id=file_id)
            
            # Check if the file is already in favorites to prevent duplication
            if not Datasets.objects.filter(user=username, dname=metadata.dname, repo='favorites').exists():
                # Create a new metadata entry for favorites
                favorite_metadata = Datasets(
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
            metadata = Datasets.objects.get(id=file_id)
            metadata.delete()
            return redirect('datasets')

    # Query the Metadata table for different categories
    public_datasets = Datasets.objects.filter(Repository='public')
    private_datasets = Datasets.objects.filter(User=username, Repository='private')
    favorite_datasets = Datasets.objects.filter(User=username, Repository='favorites')
    datastores = Datastores.objects.all()
    print(datastores)

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

    # Query the Metadata table for different categories
    public_datasets = Datasets.objects.filter(repo='public')
    private_datasets = Datasets.objects.filter(user=username, repo='private')
    favorite_datasets = Datasets.objects.filter(user=username, repo='favorites')

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
