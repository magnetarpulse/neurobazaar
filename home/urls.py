from django.urls import path

from django.conf import settings
from django.conf.urls.static import static

from . import views


urlpatterns = [
    path('images/', views.image_list, name='image_list'),  # URL to get image filenames
]

