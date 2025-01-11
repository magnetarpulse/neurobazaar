import os
import sys
from dataclasses import dataclass

def get_neurobazaar_dir() -> str:
    """Returns the neurobazaar directory."""
    cwd = os.getcwd()
    index = cwd.index('neurobazaar')
    return cwd[:index + len('neurobazaar')]

neurobazaar = get_neurobazaar_dir()
sys.path.insert(0, neurobazaar)

import io
import mmap
import fcntl

import time
from time import time
import shutil
import ctypes
import psutil                                                                                                                      # type: ignore
import resource
import mimetypes

import asyncio
from queue import PriorityQueue   
from threading import Timer, Thread
from asgiref.sync import sync_to_async                                                                                             # type: ignore 
from concurrent.futures import ThreadPoolExecutor

import uuid
import json
import base64

from typing import Any, AsyncGenerator, Generator

from nacl.secret import Aead                                                                                                       # type: ignore
from nacl.utils import random                                                                                                      # type: ignore
from nacl.exceptions import CryptoError                                                                                            # type: ignore  

import zlib 
import brotli                                                                                                                      # type: ignore  
import zstandard as zstd                                                                                                           # type: ignore                                                                                             

from django.conf import settings                                                                                                   # type: ignore
from django.http import HttpRequest, HttpResponse, Http404, HttpResponseBadRequest, StreamingHttpResponse, JsonResponse            # type: ignore
from django.shortcuts import render, redirect                                                                                      # type: ignore
from django.contrib import messages                                                                                                # type: ignore
from django.contrib.auth.models import User                                                                                        # type: ignore
from django.contrib.auth import logout, authenticate, login                                                                        # type: ignore
from django.contrib.auth.decorators import login_required                                                                          # type: ignore
from django.utils import timezone                                                                                                  # type: ignore
from django.db.models.deletion import ProtectedError                                                                               # type: ignore
from django.core.exceptions import PermissionDenied                                                                                # type: ignore
from django.views.decorators.http import require_GET, require_POST                                                                 # type: ignore
from django.core.cache import cache                                                                                                # type: ignore 
from home.models import Collections, Files, Datastores, LocalFSDatastores, MongoDBDatastores

from neurobazaar.services.datastorage.datastore_manager import getDataStoreManager, get_datastore_manager_sync     
from neurobazaar.services.datastorage.localfs_datastore import LocalFSDatastore
from neurobazaar.services.core.downloader import Distributor
from benchmarks.utils.logger import ReLogger

RED = "\033[31m"
BLUE = "\033[34m"
GREEN = "\033[32m"
RESET = "\033[0m"

CHUNK_SIZE = 256 * 1024  
BUFFER_SIZE = 32  
MAX_WORKERS = min(os.cpu_count() or 4, 8)  
PAGE_SIZE = resource.getpagesize()

def rotate_secret_key():
    print(f"{BLUE}Event: rotating secret key.{RESET}")
    new_key = random(Aead.KEY_SIZE)
    os.environ['PYNACL_SECRET_KEY'] = new_key.hex()
    print(f"{GREEN}Secret key rotated.{RESET}")

def schedule_key_rotation(interval_seconds):
    rotate_secret_key()  
    Timer(interval_seconds, schedule_key_rotation, [interval_seconds]).start()

schedule_key_rotation(86400)

PYNACL_SECRET_KEY = bytes.fromhex(os.environ['PYNACL_SECRET_KEY'])
settings.SESSION_COOKIE_SECURE = True
settings.SESSION_COOKIE_HTTPONLY = True
settings.SESSION_COOKIE_SAMESITE = 'Strict'

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
                # manager = getDataStoreManager()
                manager = get_datastore_manager_sync()
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
                # manager = getDataStoreManager()
                manager = get_datastore_manager_sync()
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
    Handles dataset-related actions including batch file upload.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: The rendered datasets page or upload response.
    """
    print(f"{BLUE}Request method: {request.method}{RESET}")
    print(f"{BLUE}Request POST data: {request.POST}{RESET}")
    print(f"{BLUE}Request FILES data: {request.FILES}{RESET}")

    username = request.user.username
    user_instance = User.objects.get(username=username)
    upload_time = None

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'dataset_upload':
            batch_index = int(request.POST.get('batch_index'))
            batch_size = int(request.POST.get('batch_size'))
            total_chunks = int(request.POST.get('total_chunks'))
            original_filename = request.POST.get('original_filename')
            is_compressed = request.POST.get('is_compressed') == 'true'
            upload_session_id = request.POST.get('upload_session_id')
            remainder = int(request.POST.get('remainder'))

            if not upload_session_id:
                return HttpResponseBadRequest("Upload session ID not found.")

            generated_uuid = str(uuid.uuid4())
            uuid_original_filename = generated_uuid + '_' + original_filename
            temp_upload_dir = os.path.join(neurobazaar, 'datastore', '.chunked_files', )
            os.makedirs(temp_upload_dir, exist_ok=True)
            
            generated_uuid = str(uuid.uuid4())
            uuid_original_filename = generated_uuid + '_' + original_filename
            temp_upload_dir = os.path.join(neurobazaar, 'datastore', '.chunked_files')
            os.makedirs(temp_upload_dir, exist_ok=True)

            for i in range(batch_size):
                file_key = f'dataset_file_{batch_index}_{i}'
                uploaded_chunk = request.FILES.get(file_key)
                print(f"{BLUE}Uploaded chunk: {uploaded_chunk} {RESET}")
                print(f"{BLUE}Uploaded chunk size: {uploaded_chunk.size} {RESET}")

                if not uploaded_chunk:
                    return HttpResponseBadRequest(f"Missing file: {file_key}")
                
                if batch_size == remainder:
                    chunk_number = i
                else:
                    chunk_number = remainder + (batch_index * batch_size + i)

                if chunk_number >= total_chunks:
                    continue

                chunk_filename = os.path.join(
                    temp_upload_dir,
                    f"{upload_session_id}_chunk_{chunk_number}"
                )

                print(f"{GREEN}Chunk filename: {chunk_filename}{RESET}")

                try:
                    if is_compressed:
                        try:
                            compressed_data = uploaded_chunk.read()
                            decompressed_chunk = zlib.decompress(compressed_data, zlib.MAX_WBITS | 16)
                            with open(chunk_filename, 'wb') as chunk_file:
                                chunk_file.write(decompressed_chunk)
                            print(f"{GREEN}Decompressed chunk written to file.{RESET}")
                        except zlib.error as e:
                            print(f"{RED}Decompression failed: {str(e)}{RESET}")
                            return HttpResponseBadRequest(f"Decompression failed: {str(e)}")
                    else:
                        with open(chunk_filename, 'wb') as chunk_file:
                            for chunk in uploaded_chunk.chunks():
                                chunk_file.write(chunk)
                            print(f"{GREEN}Chunk written to file.{RESET}")

                    if not os.path.exists(chunk_filename):
                        raise ValueError(f"Chunk {chunk_number} failed to save")

                except Exception as e:
                    return HttpResponseBadRequest(f"Failed to process chunk {file_key}: {str(e)}")

            chunk_files = [
                f for f in os.listdir(temp_upload_dir)
                if f.startswith(f"{upload_session_id}_chunk_")
            ]

            print(f"{BLUE}Chunk files found: {chunk_files}{RESET}")

            if len(chunk_files) == total_chunks:
                final_file_path = os.path.join(
                    neurobazaar,
                    'datastore',
                    '.datasets',
                    uuid_original_filename
                )
                print(f"{BLUE}Final file path: {final_file_path}{RESET}")

                os.makedirs(os.path.dirname(final_file_path), exist_ok=True)
                print(f"{GREEN}Directory created: {os.path.dirname(final_file_path)}{RESET}")

                with open(final_file_path, 'wb') as final_file:
                    for i in range(remainder, total_chunks):
                        chunk_path = os.path.join(
                            temp_upload_dir,
                            f"{upload_session_id}_chunk_{i}"
                        )
                        print(f"{BLUE}Reading chunk: {chunk_path}{RESET}")
                        if not os.path.exists(chunk_path):
                            raise FileNotFoundError(f"Missing chunk: {chunk_path}")
                    

                        with open(chunk_path, 'rb') as chunk_file:
                            final_file.write(chunk_file.read())
                    
                    for i in range(remainder):
                        chunk_path = os.path.join(
                            temp_upload_dir,
                            f"{upload_session_id}_chunk_{i}"
                        )
                        print(f"{BLUE}Reading chunk: {chunk_path}{RESET}")
                        if not os.path.exists(chunk_path):
                            raise FileNotFoundError(f"Missing chunk: {chunk_path}")

                        with open(chunk_path, 'rb') as chunk_file:
                            final_file.write(chunk_file.read())

                print(f"{GREEN}Final file written: {final_file_path}{RESET}")

                for chunk_file in os.listdir(temp_upload_dir):
                    if chunk_file.startswith(f"{upload_session_id}_chunk_"):
                        os.remove(os.path.join(temp_upload_dir, chunk_file))
                        print(f"{BLUE}Removed chunk file: {chunk_file}{RESET}")

                description = request.POST['description']
                repo = request.POST['repo']
                datastore = request.POST['datastore']
                datastore_instance = Datastores.objects.get(UUID=datastore)

                with open(final_file_path, 'rb') as dataset_file:
                    manager = get_datastore_manager_sync()
                    datastore_type, datastore_obj = manager.get_datastore_sync(datastore)
                    print(f"{GREEN}Successfully retrieved datastore object with UUID: {datastore}{RESET}")
                    print(f"{GREEN}Datastore type: {datastore_type}{RESET}")
                    dataset_id = datastore_obj.putDataset(dataset_file)
                    print(f"{GREEN}Binary Dataset Universally Unique Identifier (UUID): {dataset_id} {RESET}")

                    metadata = Files(
                        Username=user_instance,
                        Name=original_filename,
                        UUID=generated_uuid,
                        _UUID=dataset_id,
                        Datastore_UUID=datastore_instance,
                        Description=description,
                        Repository=repo,
                        Created=timezone.now().date(),
                    )
                    metadata.save()

                messages.info(request, f"File {original_filename} uploaded successfully.")
                return redirect('datasets')

            return JsonResponse({"message": f"Batch {batch_index} received. Waiting for remaining batches."}, status=202)
        
        # Default render for GET requests
        # datastores = Datastores.objects.all()
        # return render(request, 'datasets.html', {'datastores': datastores})
        
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
            
            if not Files.objects.filter(user=username, data_name=metadata.data_name, repo='favorites').exists():
                favorite_metadata = Files(
                    user=username,
                    data_name=metadata.data_name,
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

class RateLimitExceeded(PermissionDenied):
    """Exception raised when the rate limit is exceeded."""
    pass

class TokenExpired(Exception):
    """Exception raised when a token has expired."""
    pass

def _encrypt_token(data: dict, key: bytes) -> str:
    """

    Args:
        data (dict): The data to be encrypted, typically a dictionary containing token information.
        key (bytes): The encryption key, which must be a 32-byte (256-bit) key.

    Returns:
        str: The encrypted token, encoded in base64.

    Raises:
        ValueError: If the data cannot be serialized to JSON.
    """
    aead = Aead(key)
    nonce = random(Aead.NONCE_SIZE)
    plaintext = json.dumps(data).encode()
    encrypted = aead.encrypt(plaintext, nonce)
    combined = nonce + encrypted
    return base64.b64encode(combined).decode()

def _decrypt_token(encrypted: str, key: bytes) -> dict:
    """

    Args:
        encrypted (str): The encrypted token, encoded in base64.
        key (bytes): The decryption key, which must be the same 32-byte (256-bit) key used for encryption.

    Returns:
        dict: The decrypted data as a dictionary.

    Raises:
        PermissionDenied: If decryption fails due to invalid token, incorrect key, or corrupted data.
        ValueError: If the base64 decoding fails.
        json.JSONDecodeError: If the decrypted data cannot be parsed as JSON.
    """
    aead = Aead(key)
    try:
        combined = base64.b64decode(encrypted)
        nonce = combined[:Aead.NONCE_SIZE]
        encrypted_bytes = combined[Aead.NONCE_SIZE:]
        plaintext = aead.decrypt(encrypted_bytes, nonce)
        return json.loads(plaintext.decode())
    except (CryptoError, ValueError, json.JSONDecodeError) as e:
        raise PermissionDenied("Invalid token") from e

@require_GET
async def get_download_token(request: HttpRequest) -> JsonResponse:
    """Generates and stores a secure download token in Redis with rate limiting.

    Args:
        request: The HTTP request object containing headers and session.

    Returns:
        JsonResponse containing the generated token.

    Raises:
        JsonResponse: With 400 status if not an AJAX request.
        RateLimitExceeded: If rate limit is exceeded.
    """
    print(f"{BLUE}Event: Received request to generate download token{RESET}")
    
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        print(f"{RED}Unsuccessful: Request is not AJAX{RESET}")
        return JsonResponse({'error': 'AJAX requests only'}, status=400)
    
    @sync_to_async
    def get_user_id():
        if request.user.is_authenticated:
            return str(request.user.id)
        else:
            return request.session.session_key

    user_id = await get_user_id()
    rate_key = f'download_rate_{user_id}'
    
    @sync_to_async
    def check_rate_limit() -> tuple[bool, int, int]:
        rate_data = cache.get(rate_key)
        current_time = int(time())
        
        if not rate_data:
            rate_data = {
                'count': 0,
                'reset_time': current_time + 10800  
            }
        
        if current_time > rate_data['reset_time']:
            rate_data = {
                'count': 0,
                'reset_time': current_time + 10800
            }
        
        if rate_data['count'] >= 100:
            remaining_time = rate_data['reset_time'] - current_time
            return False, remaining_time, rate_data['count']
        
        rate_data['count'] += 1
        cache.set(rate_key, rate_data, 10800)  
        return True, 0, rate_data['count']

    is_allowed, wait_time, request_count = await check_rate_limit()
    if not is_allowed:
        print(f"{RED}Unsuccessful: Rate limit exceeded, wait time: {wait_time} seconds{RESET}")
        return JsonResponse({
            'error': 'Rate limit exceeded',
            'wait_time': wait_time
        }, status=429)

    current_time = int(time())
    token_data = {
        'created': current_time,
        'expires': current_time + 300, 
        'ip': request.META.get('REMOTE_ADDR'),
        'used': False
    }

    encrypted_token = _encrypt_token(token_data, PYNACL_SECRET_KEY)
    await sync_to_async(cache.set)(encrypted_token, json.dumps(token_data), 300)
    print(f"{GREEN}Successful: Download token generated and stored in Redis. Total tokens requested in the last 3 hours: {request_count}{RESET}")
    return JsonResponse({'token': encrypted_token})

@require_POST
async def wrapper_download_file(request: HttpRequest) -> HttpResponse:
    """Handles secure file download with token verification and expiration check.

    Args:
        request (HttpRequest): The HTTP request object containing POST data and session.

    Returns:
        HttpResponse containing the file data.

    Raises:
        PermissionDenied: If request is not AJAX or token is invalid.
        TokenExpired: If the token has expired.
    """
    print(f"{BLUE}Event: Received request to download file{RESET}")
    
    is_ajax = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
        request.POST.get('X-Requested-With') == 'XMLHttpRequest'
    )
    if not is_ajax:
        print(f"{RED}Unsuccessful: Request is not AJAX{RESET}")
        raise PermissionDenied("AJAX requests only")
    
    token = request.POST.get('token')
    if not token:
        print(f"{RED}Unsuccessful: No token provided{RESET}")
        raise PermissionDenied("Invalid token")
    
    token_data = await sync_to_async(cache.get)(token)
    if not token_data:
        print(f"{RED}Unsuccessful: Invalid token{RESET}")
        raise PermissionDenied("Invalid token")
    
    token_metadata = json.loads(token_data)
    
    if token_metadata.get('used'):
        print(f"{RED}Unsuccessful: Token has already been used{RESET}")
        raise PermissionDenied("Token has already been used")
    
    current_time = int(time())
    if current_time > token_metadata['expires']:
        await sync_to_async(cache.delete)(token)
        print(f"{RED}Unsuccessful: Token has expired{RESET}")
        raise TokenExpired("Token has expired")
    
    if token_metadata.get('ip') != request.META.get('REMOTE_ADDR'):
        print(f"{RED}Unsuccessful: Token IP mismatch{RESET}")
        raise PermissionDenied("Token IP mismatch")
    
    token_metadata['used'] = True
    await sync_to_async(cache.set)(token, json.dumps(token_metadata))
    print(f"{GREEN}Successful: Token verified, proceeding with file download{RESET}")
    
    compressor = request.GET.get('compressor', 'gzip')
    if compressor not in ('none', 'gzip', 'zstandard', 'brotli'):
        print(f"{RED}Unsuccessful: Unsupported/Invalid compressor type{RESET}")
        return JsonResponse({'error': 'Unsupported/Invalid compressor type'}, status=400)
    
    return await _download_file(request, compressor)

async def _stream_compressed_file(file_path: str, chunk_size: int = 10 * 1024 * 1024, compressor: str = 'gzip') -> AsyncGenerator[bytes, None]:
    """
    Asynchronously stream and compress a file.
    
    Args:
        file_path (str): Path to the file to be streamed
        chunk_size (int): Size of chunks to read and compress
        compressor (str): Compression algorithm to use ('gzip', 'zstandard', 'brotli')
    
    Yields:
        Compressed file chunks
    """
    if compressor == 'gzip':
        print(f"{GREEN}92mUsing gzip compressor.{RESET}")
        compressor_obj = zlib.compressobj(level=9, wbits=zlib.MAX_WBITS | 16)
    elif compressor == 'zstandard':
        print(f"{GREEN}Using zstandard compressor.{RESET}")
        compressor_obj = zstd.ZstdCompressor(level=19).compressobj()
    elif compressor == 'brotli':
        print(f"{GREEN}Using brotli compressor.{RESET}")
        compressor_obj = brotli.Compressor(quality=11)
    else:
        raise ValueError(f"Unsupported compressor: {compressor}")

    try:
        async with aiofiles.open(file_path, 'rb') as f:
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                if compressor == 'brotli':
                    compressed_chunk = compressor_obj.process(chunk)
                else:
                    compressed_chunk = compressor_obj.compress(chunk)
                if compressed_chunk:
                    yield compressed_chunk
            if compressor == 'brotli':
                yield compressor_obj.finish()
            else:
                yield compressor_obj.flush()
    
    except Exception as e:
        print(f"{RED}Error streaming file: {e}{RESET}")

def _chunk_file(file_obj: Any, chunk_size: int = 10 * 1024 * 1024) -> Generator[bytes, None, None]:
    """
    Generator to chunk a file from MongoDB without compression.
    
    Args:
        file_obj (Any): The file object to chunk
        chunk_size (int): Size of chunks to read at a time
        
    Yields:
        Chunks of the file
    """
    while True:
        chunk = file_obj.read(chunk_size)
        if not chunk:
            break
        yield chunk

def _async_to_sync_generator(async_gen: Any) -> Generator[Any, None, None]:
    """
    Wrap an asynchronous generator to make it synchronous.
    
    Args:
        async_gen (Any): The asynchronous generator to wrap.
    
    Yields:
        Any: Synchronous generator items.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async_gen = async_gen.__aiter__()
    
    while True:
        try:
            item = loop.run_until_complete(async_gen.__anext__())
            yield item
        except StopAsyncIteration:
            break

@dataclass(order=True)
class OrderedChunk:
    sequence: int
    data: bytes = None  # field won't be used for ordering

    def __post_init__(self):
        # Make data field not participate in comparison
        object.__setattr__(self, 'data', self.data)

def optimize_system():
    """Configure system-level optimizations with fallbacks."""
    
    try:
        libc = ctypes.CDLL('libc.so.6')
        PR_SET_IO_PRIORITY = 40
        IOPRIO_CLASS_RT = 1
        ioprio = (IOPRIO_CLASS_RT << 13) | 7  
        libc.syscall(PR_SET_IO_PRIORITY, 0, ioprio)
        print(f"{GREEN}I/O priority optimization successful.{RESET}")
    except Exception as e:
        print(f"{RED}I/O priority optimization not available: {e}{RESET}")

    try:
        process = psutil.Process()
        cpu_count = os.cpu_count() or 4
        cpu_list = list(range(cpu_count // 2))
        process.cpu_affinity(cpu_list)
        print(f"{GREEN}CPU affinity successfully set.{RESET}")
    except Exception as e:
        print(f"{RED}CPU affinity setting not available: {e}{RESET}")

    try:
        libc = ctypes.CDLL('libc.so.6')
        MCL_CURRENT = 1
        MCL_FUTURE = 2
        libc.mlockall(MCL_CURRENT | MCL_FUTURE)
        print(f"{GREEN}Memory locking successful.{RESET}")
    except Exception as e:
        print(f"{RED}Memory locking not available: {e}{RESET}")

def file_producer(file_path: str, chunk_size: int, buffer: PriorityQueue) -> None:
    file_size = os.path.getsize(file_path)
    aligned_chunk_size = (chunk_size + PAGE_SIZE - 1) & ~(PAGE_SIZE - 1)

    with open(file_path, "rb") as f:
        try:
            fcntl.fcntl(f.fileno(), fcntl.F_SETFL, os.O_DIRECT)
        except Exception:
            pass  

        try:
            if hasattr(os, 'posix_fadvise'):
                os.posix_fadvise(f.fileno(), 0, 0, os.POSIX_FADV_SEQUENTIAL)
        except Exception:
            pass

        try:
            import subprocess
            subprocess.run(['ionice', '-c2', '-n0', str(os.getpid())], 
                         stderr=subprocess.DEVNULL, 
                         stdout=subprocess.DEVNULL)
            print(f"{GREEN}ionice set to real-time priority.{RESET}")
        except Exception as e:
            print(f"{RED}ionice setting not available: {e}{RESET}")

        try:
            mmapped_file = mmap.mmap(
                f.fileno(), 0,
                access=mmap.ACCESS_READ
            )

            if hasattr(mmapped_file, 'madvise'):
                mmapped_file.madvise(mmap.MADV_SEQUENTIAL)
                mmapped_file.madvise(mmap.MADV_WILLNEED)

            chunks = [(i, min(i + aligned_chunk_size, file_size))
                        for i in range(0, file_size, aligned_chunk_size)]

            for sequence, (start, end) in enumerate(chunks):
                chunk = mmapped_file[start:end]
                ordered_chunk = OrderedChunk(sequence=sequence, data=chunk)
                buffer.put(ordered_chunk)

            mmapped_file.close()
        except Exception as e:
            for sequence, start in enumerate(range(0, file_size, aligned_chunk_size)):
                f.seek(start)
                chunk = f.read(min(aligned_chunk_size, file_size - start))
                ordered_chunk = OrderedChunk(sequence=sequence, data=chunk)
                buffer.put(ordered_chunk)

    buffer.put(OrderedChunk(sequence=float('inf'), data=None))

async def file_consumer(buffer: PriorityQueue) -> AsyncGenerator[bytes, None]:
    executor = ThreadPoolExecutor(
        max_workers=MAX_WORKERS,
        thread_name_prefix='download_worker'
    )
    
    next_sequence = 0  

    while True:
        try:
            chunk = await asyncio.get_event_loop().run_in_executor(
                executor,
                lambda: buffer.get(timeout=10)
            )
            
            if chunk.sequence == float('inf'):
                break
                
            if chunk.sequence != next_sequence:
                raise ValueError(f"Chunk out of sequence. Expected {next_sequence}, got {chunk.sequence}")
                
            next_sequence += 1
            yield chunk.data
            
        except Exception as e:
            print(f"{RED}Consumer error: {e}{RESET}")
            break

    executor.shutdown(wait=False)

async def _stream_large_file(file_path: str) -> AsyncGenerator[bytes, None]:
    """Optimized streaming with robust resource management."""
    optimize_system()
    
    buffer = PriorityQueue(maxsize=BUFFER_SIZE)
    
    import threading
    threading.stack_size(262144)  

    producer_thread = Thread(
        target=file_producer,
        args=(file_path, CHUNK_SIZE, buffer),
        daemon=True
    )
    producer_thread.start()

    try:
        async for chunk in file_consumer(buffer):
            yield chunk
    finally:
        if producer_thread.is_alive():
            producer_thread.join(timeout=1.0)

async def _download_file(request: HttpRequest, compressor: str = 'gzip') -> StreamingHttpResponse:
    """Optimized download handler with robust socket configuration."""
    try:
        logger = ReLogger()
        logger.run()
        streamer = Distributor()
        
        if 'download_file' not in request.POST:
            raise ValueError("Missing download_file parameter")

        dataset_UUID = request.POST['download_file']
        
        dataset_future = asyncio.create_task(sync_to_async(
            lambda: Files.objects.select_related('Datastore_UUID').get(UUID=dataset_UUID)
        )())
        manager_future = asyncio.create_task(getDataStoreManager())
        
        dataset, manager = await asyncio.gather(dataset_future, manager_future)
        
        datastore_uuid = str(dataset.Datastore_UUID.UUID)
        datastore_type, datastore = await manager.getDatastore(datastore_uuid)
        
        if str(datastore_type) != 'LocalFSDatastore':
            raise ValueError(f"Unsupported datastore type: {datastore_type}")

        file_obj = datastore.get_dataset_object(str(dataset.UUID), dataset.Name, object=True)
        
        response = StreamingHttpResponse(
            # _async_to_sync_generator(_stream_large_file(file_obj)),
            streamer.stream_file(compressed=False, file_path = file_obj, io_method="mmap"),
            content_type='application/octet-stream'
        )
        
        # Enhanced headers
        response['Content-Disposition'] = f'attachment; filename="{dataset.Name}"'
        response['Cache-Control'] = 'no-transform'
        response['X-Accel-Buffering'] = 'no'
        
        return response
        
    except Exception as e:
        print(f"{RED}Download error: {e}{RESET}")
        raise Http404("File not found or access denied") from e

async def download_file(request: HttpRequest, compressor: str = 'gzip') -> StreamingHttpResponse:
    """
    Asynchronously download and optionally compress a file.

    Args:
        request (HttpRequest): The HTTP request object.
        compressor (str): The compression algorithm to use ('none', 'gzip', 'zstandard', 'brotli'). Defaults to 'gzip'.

    Returns:
        StreamingHttpResponse: The HTTP response with the file (compressed or uncompressed).

    Raises:
        ValueError: If an unsupported compressor is specified.
    """
    if 'download_file' in request.POST:
        dataset_UUID = request.POST['download_file']
        
        dataset = await sync_to_async(
            lambda: Files.objects.select_related('Datastore_UUID').get(UUID=dataset_UUID)
        )()
        
        datastore_uuid = str(dataset.Datastore_UUID.UUID)
        manager = await getDataStoreManager()
        datastore_type, datastore = await manager.getDatastore(datastore_uuid)
        
        datastore_type = str(datastore_type)
        print(f"{BLUE}[94mDatastore type: ", datastore_type, "{RESET}")

        import time

        if datastore_type == 'LocalFSDatastore':
            start_time = time.perf_counter()
            file_obj = datastore.get_dataset_object(str(dataset.UUID), dataset.Name, object=True)
            print(f"{GREEN}Time to retrieve file: {time.perf_counter() - start_time:.6f} seconds{RESET}")

            if compressor == 'none':
                content_type = 'application/octet-stream'
                file_extension = ''
                response = StreamingHttpResponse(
                    _async_to_sync_generator(_stream_large_file(file_obj)), 
                    content_type=content_type
                )
            else:
                if compressor == 'gzip':
                    content_type = 'application/gzip'
                    file_extension = '.gz'
                elif compressor == 'zstandard':
                    content_type = 'application/zstd'
                    file_extension = '.zst'
                elif compressor == 'brotli':
                    content_type = 'application/x-brotli'
                    file_extension = '.br'
                else:
                    raise ValueError(f"Unsupported compressor: {compressor}")

                start_time = time.perf_counter()
                response = StreamingHttpResponse(
                    _async_to_sync_generator(_stream_compressed_file(file_obj, compressor=compressor)), 
                    content_type=content_type
                )
                print(f"{GREEN}Time to zip and prepare response: {time.perf_counter() - start_time:.6f} seconds{RESET}")

            filename = f'{dataset.Name}{file_extension}' if file_extension else dataset.Name
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        elif datastore_type == "MongoDBDatastore":
            start_time = time.perf_counter()
            file_obj = datastore.getDataset(str(dataset._UUID))
            print(f"{GREEN}94mFile object retrieved from MongoDB.{RESET}")
            print(f"{GREEN}Time to retrieve file: {time.perf_counter() - start_time:.6f} seconds{RESET}")

            if compressor == 'none':
                content_type = 'application/octet-stream'
                file_extension = ''
                response = StreamingHttpResponse(
                    _chunk_file(file_obj),
                    content_type=content_type
                )
            else:
                start_time = time.perf_counter()
                compressed_file = io.BytesIO()

                if compressor == 'gzip':
                    print(f"{BLUE}Using gzip compressor{RESET}")
                    compressor_obj = zlib.compressobj(level=9, wbits=zlib.MAX_WBITS | 16)
                    content_type = 'application/gzip'
                    file_extension = '.gz'
                elif compressor == 'zstandard':
                    print(f"{BLUE}Using zstandard compressor{RESET}")
                    compressor_obj = zstd.ZstdCompressor(level=19).compressobj()
                    content_type = 'application/zstd'
                    file_extension = '.zst'
                elif compressor == 'brotli':
                    print(f"{BLUE}Using brotli compressor{RESET}")
                    compressor_obj = brotli.Compressor(quality=11)
                    content_type = 'application/x-brotli'
                    file_extension = '.br'
                else:
                    raise ValueError(f"Unsupported compressor: {compressor}")

                if compressor == 'brotli':
                    compressed_data = compressor_obj.process(file_obj.read())
                    compressed_data += compressor_obj.finish()
                else:
                    compressed_data = compressor_obj.compress(file_obj.read())
                    compressed_data += compressor_obj.flush()

                compressed_file.write(compressed_data)
                compressed_file.seek(0)
                print(f"{GREEN}Time to compress file: {time.perf_counter() - start_time:.6f} seconds{RESET}")

                start_time = time.perf_counter()
                response = StreamingHttpResponse(compressed_file)
                print(f"{GREEN}Time to prepare response: {time.perf_counter() - start_time:.6f} seconds{RESET}")
                
            filename = f'{dataset.Name}{file_extension}' if file_extension else dataset.Name
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Type'] = content_type
            return response
        else:
            raise ValueError("Unsupported datastore type.")