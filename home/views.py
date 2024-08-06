import os
import csv
from django.conf import settings
from django.shortcuts import render, HttpResponse, redirect
from home.models import User
from django.contrib.auth.models import User
from django.contrib.auth import logout, authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from home.models import Metadata


# Create your views here.
def index(request):
    username = None
    if request.user.is_authenticated:
        username = request.user.username
    return render(request, 'index.html', {'username': username})

def logoutUser(request):
    logout(request)
    return redirect('/login_register')


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
            dname = request.FILES['dname']
            description = request.POST['description']
            repo = request.POST['repo']

            metadata = Metadata(
                user=username,
                dname=dname.name,
                description=description,
                repo=repo,
                date=timezone.now().date(),
                time=timezone.now().time()
            )
            metadata.save()
            return redirect('datasets')  # Redirect to avoid resubmission of form

        # Handling like action
        elif 'like_file' in request.POST:
            file_id = request.POST['like_file']
            metadata = Metadata.objects.get(id=file_id)
            metadata.likes += 1
            metadata.save()
            return redirect('datasets')

        # Handling dislike action
        elif 'dislike_file' in request.POST:
            file_id = request.POST['dislike_file']
            metadata = Metadata.objects.get(id=file_id)
            metadata.dislikes += 1
            metadata.save()
            return redirect('datasets')

        # Handling copy to favorites action
        elif 'copy_to_favorites' in request.POST:
            file_id = request.POST['copy_to_favorites']
            metadata = Metadata.objects.get(id=file_id)
            
            # Check if the file is already in favorites to prevent duplication
            if not Metadata.objects.filter(user=username, dname=metadata.dname, repo='favorites').exists():
                # Create a new metadata entry for favorites
                favorite_metadata = Metadata(
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
            metadata = Metadata.objects.get(id=file_id)
            metadata.delete()
            return redirect('datasets')

    # Query the Metadata table for different categories
    public_datasets = Metadata.objects.filter(repo='public')
    private_datasets = Metadata.objects.filter(user=username, repo='private')
    favorite_datasets = Metadata.objects.filter(user=username, repo='favorites')

    context = {
        'public_datasets': public_datasets,
        'private_datasets': private_datasets,
        'favorite_datasets': favorite_datasets,
        'username': username  # Include username in the context
    }

    return render(request, 'datasets.html', context)


@login_required
def workspaces(request):
    username = request.user.username

    # Query the Metadata table for different categories
    public_datasets = Metadata.objects.filter(repo='public')
    private_datasets = Metadata.objects.filter(user=username, repo='private')
    favorite_datasets = Metadata.objects.filter(user=username, repo='favorites')

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
