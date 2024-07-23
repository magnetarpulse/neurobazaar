import uuid
from django.shortcuts import render, redirect
from home.models import User
from django.contrib.auth.models import User
from django.contrib.auth import logout, authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from home.models import Datasets,DataStores,LocalFileSystem
import os

from neurobazaar.datastore_manager import getDataStoreManager


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
    if not DataStores.objects.exists():
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Join the BASE_DIR with 'DataStore' to form the path to the directory
        default_datastore_path = os.path.join(BASE_DIR, 'DataStore')

        # Check if the directory exists and create it if it doesn't
        if not os.path.exists(default_datastore_path):
            os.makedirs(default_datastore_path)

        manager = getDataStoreManager()
        default_datastore_id = manager.addFSDataStore(default_datastore_path)
        LocalFileSystem.objects.create(
            DataStore_ID=str(default_datastore_id),
            DataStore_Name='Default',
            Destination_Path=default_datastore_path
        )
    
    # Handle form submissions for adding or removing datastores
    if request.method == 'POST':
        if 'add_datastore' in request.POST:
            database_type = request.POST.get('database')
            if database_type == 'filesystem':
                path = request.POST.get('destination_path')
                manager = getDataStoreManager()
                datastore_id = manager.addFSDataStore(path)
                new_local_fs = LocalFileSystem(
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
                # Similar steps for MongoDB or other databases
                pass

        elif 'remove_datastore' in request.POST:
            datastore_id = request.POST.get('datastore_id')
            manager.removeDataStore(datastore_id)
            DataStores.objects.filter(DataStore_ID=datastore_id).delete()

    datastores = DataStores.objects.all()
    return render(request, 'datastore.html', {'datastores': datastores})
    
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
    
    if request.method == 'POST':
        # Handling file upload and dataset creation
        if 'dname' in request.FILES and 'description' in request.POST and 'repo' in request.POST:
            dname = request.FILES.get('dname')
            description = request.POST['description']
            repo = request.POST['repo']

            metadata = Datasets(
                user=username,
                dname=dname.name,
                dsid=uuid.uuid4(),
                description=description,
                repo=repo,
                date=timezone.now().date(),
                time=timezone.now().time()
            )
            metadata.save()
            
            manager = getDataStoreManager()
            datastore = manager.getDataStore(3)
            datasetid = str(metadata.dsid) 
            datastore.putDataset(datasetid, dname)
            
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
    public_datasets = Datasets.objects.filter(repo='public')
    private_datasets = Datasets.objects.filter(user=username, repo='private')
    favorite_datasets = Datasets.objects.filter(user=username, repo='favorites')
    datastores = DataStores.objects.all()
    print(datastores)

    context = {
        'public_datasets': public_datasets,
        'private_datasets': private_datasets,
        'favorite_datasets': favorite_datasets,
        'datastores': datastores,
        'username': username  # Include username in the context
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
