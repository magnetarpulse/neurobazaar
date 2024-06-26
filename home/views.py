import os
from django.http import FileResponse, HttpResponseNotFound
from django.conf import settings
from django.shortcuts import render, HttpResponse, redirect
from neurobazaar.settings import BASE_DIR
from home.models import User
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import logout, authenticate, login
from django.http import JsonResponse
import os
import csv
# import by rushi
from django.contrib.auth.decorators import login_required
import uuid
from django.core.files.storage import FileSystemStorage


# Create your views here.
def index(request):
    username = None
    if request.user.is_authenticated:
        username = request.user.username
    return render(request, 'index.html', {'username': username})

def loginUser(request):
    if request.method=='POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)
        
        if user is not None:
            # A backend authenticated the credentials
            login(request, user)
            return redirect('/')
        else:
            # No backend authenticated the credentials
            # messages.alert(request, 'Invalid username or password.')
            return render(request, 'login.html')

    return render(request, 'login.html', {'user': request.user})

def logoutUser(request):
    logout(request)
    return redirect('/login')


def register(request):
    if request.method == 'POST':
        user = UserCreationForm(request.POST)
        if user.is_valid():
            username = request.POST.get('username')
            password = request.POST.get('password1')
            
            user = User.objects.create_user(username=username,password=password)
            user.save()
            return redirect('/login')
    else:
        user = UserCreationForm()
    return render(request, 'register.html')

@login_required
def results(request):
    # Retrieve the username
    username = request.user.username

    # Define the path to the user's workspace directory
    user_workspace_dir = os.path.join(settings.MEDIA_ROOT, 'workspace', username)

    # Fetch existing workspaces for the user
    existing_workspaces = []
    if os.path.exists(user_workspace_dir):
        workspace_list = os.listdir(user_workspace_dir)
        for workspace in workspace_list:
            workspace_number = workspace.split('_')[1]
            workspace_content = {
                'workspace_number': workspace_number,
                'name': workspace,
                'pca_plot': None,  # Initialize pca_plot to None
                'table_headers': [],
                'tabular_data': []
            }
            workspace_path = os.path.join(user_workspace_dir, workspace)
            if os.path.isdir(workspace_path):
                files = os.listdir(workspace_path)
                if 'pca_plot.png' in files:
                    # Construct the path to pca_plot for the workspace
                    workspace_content['pca_plot'] = fetch_pca_plot_path(username, workspace_number)
                # Look for any CSV file in the workspace directory
                csv_files = [file for file in files if file.endswith('.csv')]
                if csv_files:
                    csv_file_path = os.path.join(workspace_path, csv_files[0])
                    with open(csv_file_path, 'r') as csv_file:
                        csv_reader = csv.reader(csv_file)
                        workspace_content['table_headers'] = next(csv_reader, [])
                        workspace_content['tabular_data'] = list(csv_reader)
            existing_workspaces.append(workspace_content)

    # Pass the list of existing workspaces to the template
    return render(request, 'results.html', {'username': username, 'existing_workspaces': existing_workspaces})


def fetch_pca_plot_path(username, workspace_number):
    # # Construct the path to the PCA plot image relative to the static directory
    return f'/static/workspace/{username}/workspace_{workspace_number}/pca_plot.png'


# Function to handle copying files to favorites
def copy_to_favorites(filename, source_folder, username, visibility):
    if visibility == 'public':
        source_path = os.path.join(settings.MEDIA_ROOT, 'datasets', 'public', filename)
    else:
        source_path = os.path.join(settings.MEDIA_ROOT, 'datasets', username, 'private', filename)
    
    destination_path = os.path.join(settings.MEDIA_ROOT, 'datasets', username, 'favorites', filename)
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)  # Create directories if not exists
    
    # Copy the file
    with open(source_path, 'rb') as source:
        with open(destination_path, 'wb') as destination:
            destination.write(source.read())

# Function to handle deleting files
def delete_file(filename, folder, username):
    file_path = os.path.join(settings.MEDIA_ROOT, 'datasets', username, folder, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

@login_required
def datasets(request):
    username = request.user.username
    user_datasets_dir = os.path.join(settings.MEDIA_ROOT, 'datasets', username)
    os.makedirs(user_datasets_dir, exist_ok=True)  # Create user's directory if not exists

    # Create public directory if it doesn't exist
    public_dir = os.path.join(settings.MEDIA_ROOT, 'datasets', 'public')
    os.makedirs(public_dir, exist_ok=True)

    # Create user's private and favorites directories
    user_private_dir = os.path.join(user_datasets_dir, 'private')
    os.makedirs(user_private_dir, exist_ok=True)
    user_favorite_dir = os.path.join(user_datasets_dir, 'favorites')
    os.makedirs(user_favorite_dir, exist_ok=True)

    # List public files
    public_files = os.listdir(public_dir)

    # List user's private and favorite files
    private_files = os.listdir(os.path.join(user_datasets_dir, 'private'))
    favorite_files = os.listdir(os.path.join(user_datasets_dir, 'favorites'))

    datasets = {
        'public': public_files,
        'private': private_files,
        'favorites': favorite_files
    }

    if request.method == 'POST':
        # Handle copying to favorites
        if 'copy_to_favorites' in request.POST:
            filename = request.POST['copy_to_favorites']
            source_folder = request.POST['source_folder']
            visibility = request.POST['visibility']
            copy_to_favorites(filename, source_folder, username, visibility)

        # Handle file deletion
        if 'delete_file' in request.POST:
            filename = request.POST['delete_file']
            folder = request.POST['folder']
            delete_file(filename, folder, username)

        # Handle file uploads
        uploaded_file = request.FILES.get('dataFile')
        if uploaded_file:
            # Check if the visibility is set to public or private
            visibility = request.POST.get('visibility')
            if visibility == 'public':
                destination_folder = public_dir
            else:
                destination_folder = user_private_dir

            destination_path = os.path.join(destination_folder, uploaded_file.name)
            with open(destination_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # Optionally, you can save the file path to the database for later use

            # Update the datasets dictionary based on visibility
            if visibility == 'public':
                public_files.append(uploaded_file.name)
            else:
                private_files.append(uploaded_file.name)

    return render(request, 'datasets.html', {'datasets': datasets, 'username': username})


def download_file(request, file, folder, visibility):
    if request.method == 'POST':
        username = request.user.username
        if visibility == 'public':
            file_path = os.path.join(settings.MEDIA_ROOT, 'datasets', 'public', file)
        else:
            file_path = os.path.join(settings.MEDIA_ROOT, 'datasets', username, folder, file)
        
        return FileResponse(open(file_path, 'rb'), as_attachment=True)
    


def update_reaction(request):
    if request.method == 'POST':
        file = request.POST.get('file')
        reaction = request.POST.get('reaction')

        # For demonstration purposes, just returning a success message and updated counts
        num_likes = 0  # Replace with actual number of likes for the file
        num_dislikes = 0  # Replace with actual number of dislikes for the file
        if reaction == 'like':
            num_likes += 1
        elif reaction == 'dislike':
            num_dislikes += 1
        return JsonResponse({'success': True, 'message': 'Reaction updated successfully', 'num_likes': num_likes, 'num_dislikes': num_dislikes}, status=200)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)
    

@login_required
def upload(request):
    username = request.user.username
    uploaded_file_name = None  # Placeholder for uploaded file name
    column_names = None  # Placeholder for column names
    
    if request.method == 'POST':
        uploaded_file = request.FILES.get('dataFile')
        if uploaded_file:
            # Find the next available workspace number
            user_workspace_dir = os.path.join(settings.MEDIA_ROOT, 'workspace', username)

            # Check if the user's workspace directory exists
            if not os.path.exists(user_workspace_dir):
                os.makedirs(user_workspace_dir, exist_ok=True)

            existing_workspaces = os.listdir(user_workspace_dir)
            if existing_workspaces:
                # Extract the numbers from workspace names and find the maximum
                workspace_numbers = [int(workspace.split('_')[1]) for workspace in existing_workspaces if workspace.startswith('workspace_')]
                next_workspace_number = max(workspace_numbers) + 1 if workspace_numbers else 1
            else:
                next_workspace_number = 1
            
            # Create the directory for the new workspace
            new_workspace_dir = os.path.join(user_workspace_dir, f'workspace_{next_workspace_number}')
            os.makedirs(new_workspace_dir, exist_ok=True)

            # Save the uploaded file directly into the new workspace directory
            fs = FileSystemStorage(location=new_workspace_dir)
            fs.save(uploaded_file.name, uploaded_file)
            uploaded_file_name = uploaded_file.name
            
            # Read the CSV file to extract column names
            try:
                with fs.open(uploaded_file.name, 'r') as file:
                    reader = csv.reader(file)
                    column_names = next(reader)  # Get the header row
            except Exception as e:
                # Handle any errors that might occur during file reading
                print("Error reading CSV file:", e)
            # Render upload.html with uploaded file name and column names
            return render(request, 'upload.html', {'username': username,'uploaded_file_name': uploaded_file_name, 'column_names': column_names})

    return render(request, 'upload.html', {'username': username,'uploaded_file_name': None, 'column_names': None})


def serve_pca_plot(request, username, workspace_number):
    # Construct the path to the PCA plot image
    pca_plot_path = os.path.join(settings.MEDIA_ROOT, 'workspace', username, f'workspace_{workspace_number}', 'pca_plot.png')

    # Check if the file exists
    if os.path.exists(pca_plot_path):
        # Serve the file as a response
        return FileResponse(open(pca_plot_path, 'rb'), content_type='image/png')
    else:
        # Return a 404 response if the file does not exist
        return HttpResponseNotFound("PCA plot not found")
    

