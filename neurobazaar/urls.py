"""
URL configuration for neurobazaar project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import include, path, re_path as url
from django.contrib import admin

admin.site.site_header = 'Neurobazaar Administration'
admin.site.site_title = 'Neurobazaar Administration Portal'
admin.site.index_title = 'Welcome to Neurobazaar Administration Portal'

urlpatterns = [
    path('', include('home.urls')),
    path('admin/', admin.site.urls)
    
]
