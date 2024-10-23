
import os

from django.conf import settings 
from django.http import JsonResponse
from django.shortcuts import render 


def get_config():
    """Retrieve Django settings and return as JSON."""
    return JsonResponse({'debug': settings.DEBUG})




def image_list(request):
    media_folder=os.path.join(settings.MEDIA_ROOT,'lidc_pixConvImg')
    images = [f"{request.build_absolute_uri(settings.MEDIA_URL)}lidc_pixConvImg/{img}" for img in os.listdir(media_folder) if img.endswith(('.png', '.jpg', '.jpeg'))]  # Filter for image files
    #print(f"Images:{images}")  # Debug: Check the list of images
    return JsonResponse({'images': images})




