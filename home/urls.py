from django.urls import path
from django.contrib import admin                                                                                                    
from home import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name='index'),
    path('login_register', views.login_register, name='login_register'),
    path('logout', views.logoutUser, name='logout'),
    path('workspaces/', views.workspaces, name='workspaces'),
    path('datasets/', views.datasets, name='datasets'),
    path('datasets/view_directory/<uuid:collections_uuid>/', views.view_directory, name='view_directory'),
    path('datastore/', views.datastore, name='datastore'),
    path('visualization_server_manager/', views.visualization_server_manager, name='visualization_server_manager'),
    path('trame/start_new_server', views.start_new_server, name='start_new_server'),
    path('trame/stop_server', views.stop_server, name='stop_server'),
    path('trame/get_server_list', views.get_server_list, name='get_server_list'),
    path('visualization_server_manager', views.visualization_server_manager, name='visualization_server_manager'),
    path('get-server-list/', views.get_server_list, name='get_server_list'),

]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
