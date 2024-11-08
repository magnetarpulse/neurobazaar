
import os

from django.conf import settings 
from django.http import JsonResponse
from django.shortcuts import render 


def get_config():
    """Retrieve Django settings and return as JSON."""
    return JsonResponse({'debug': settings.DEBUG})



'''def image_list(request):
    media_folder=os.path.join(settings.MEDIA_ROOT,'lidc_pixConvImg')
    images = [f"{request.build_absolute_uri(settings.MEDIA_URL)}lidc_pixConvImg/{img}" for img in os.listdir(media_folder) if img.endswith(('.png', '.jpg', '.jpeg'))]  # Filter for image files
    #print(f"Images:{images}")  # Debug: Check the list of images
    return JsonResponse({'images': images})


def dicom_list(request):
    dicom_folder=os.path.join(settings.MEDIA_ROOT,'dicom_images')
    dicom_images = [f"{request.build_absolute_uri(settings.MEDIA_URL)}dicom_images/{di_img}" for di_img in os.listdir(dicom_folder) if di_img.endswith(('.png', '.jpg', '.jpeg'))]  # Filter for dicom files
    #print(f"Images:{dicom_images}")  # Debug: Check the list of images
    return JsonResponse({'dicom_images': dicom_images})'''




