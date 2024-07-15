import os
from django.conf import settings
from django.shortcuts import render
import os
# import by rushi
from django.contrib.auth.decorators import login_required
import uuid
from .models import DatasetDescription
import time


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
    if 'DATASETSESSIONID' not in request.session:
        # Create a new session ID (DATASETSESSIONID) if it's the user's first visit to the dataset page after logging in
        request.session['DATASETSESSIONID'] = str(uuid.uuid4())
    print("LOGINSESSIONID:", request.session.session_key)
    print("DATASETSESSIONID:", request.session.get('DATASETSESSIONID'))
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

    dataset_descriptions = DatasetDescription.objects.filter(user=request.user)
    descriptions_dict = {desc.dataset_name: desc.description for desc in dataset_descriptions}

    datasets = {
        'public': [(file, descriptions_dict.get(file, '')) for file in public_files],
        'private': [(file, descriptions_dict.get(file, '')) for file in private_files],
        'favorites': [(file, descriptions_dict.get(file, '')) for file in favorite_files]
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
        description = request.POST.get('description', '').strip()  # Use .strip() to ensure whitespace isn't causing issues
        print(description)

        if not uploaded_file:
            error_message = "Please upload a file."
        elif not description:
            error_message = "Please add a description."
        # else:
        #     # Assuming you are saving the file somewhere
        #     # Here, you should also save the description along with the user and the file info in your model
        #     DatasetDescription.objects.create(
        #         user=request.user, 
        #         dataset_name=uploaded_file.name, 
        #         description=description, 
        #         upload_date=timezone.now()
        #     )
        #     # Consider adding a success message or redirecting to a confirmation page
        # new_dataset_description = DatasetDescription(user=request.user, dataset_name=uploaded_file.name, description=description)
        # new_dataset_description.save()
            
        #         # A new way to prepare datasets with descriptions
        # dataset_descriptions = DatasetDescription.objects.filter(user=request.user)
        # descriptions_dict = {desc.dataset_name: desc.description for desc in dataset_descriptions}

        # # Modify how you prepare your datasets variable to include descriptions
        # datasets = {
        #     'public': [(file, descriptions_dict.get(file, '')) for file in public_files],
        #     'private': [(file, descriptions_dict.get(file, '')) for file in private_files],
        #     'favorites': [(file, descriptions_dict.get(file, '')) for file in favorite_files]
        # }
            
        if uploaded_file:
            start_time = time.time() #start time 
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

            # Measure the end time of the upload process
            end_time = time.time()

            # Calculate the upload time
            upload_time = end_time - start_time
            print(f"Upload Time: {upload_time} seconds")
            
            # Optionally, you can save the file path to the database for later use

            # Update the datasets dictionary based on visibility
            if visibility == 'public':
                public_files.append(uploaded_file.name)
            else:
                private_files.append(uploaded_file.name)
        
        new_dataset_description = DatasetDescription(user=request.user, dataset_name=uploaded_file.name, description=description,file_path=destination_path)
        new_dataset_description.save()
        
                
        

    return render(request, 'datasets.html', {'datasets': datasets, 'username': username})

