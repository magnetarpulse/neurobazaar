"""neurobazaar URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.urls import include, path, re_path
from django.contrib import admin
from channels.routing import ProtocolTypeRouter, URLRouter
from home.wildcard import MultiPortWebSocketProxy

admin.site.site_header = 'Neurobazaar Administration'
admin.site.site_title = 'Neurobazaar Administration Portal'
admin.site.index_title = 'Welcome to Neurobazaar Administration Portal'

urlpatterns = [
    path('', include('home.urls')),
    path('admin/', admin.site.urls),
    re_path(r'^new/ws/?$', MultiPortWebSocketProxy.as_asgi()),
    re_path(r'^new2/ws/?$', MultiPortWebSocketProxy.as_asgi()),
]
