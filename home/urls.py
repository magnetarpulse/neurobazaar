from django.urls import path, re_path
from django.contrib import admin                                                                                                    
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name='index'),
    path('login_register', views.login_register, name='login_register'),
    path('logout', views.logoutUser, name='logout'),
    path('workspaces/', views.workspaces, name='workspaces'),
    path('datasets/', views.datasets, name='datasets'),
    path('datasets/view_directory/<uuid:collections_uuid>/', views.view_directory, name='view_directory'),
    path('team-details/', views.team_details, name='team_details'),
    path('datastore/', views.datastore, name='datastore'),
    path('datastore/', views.datastore, name='datastore'),
    path('download_collection/<uuid:collection_uuid>/', views.download_collection, name='download_collection'),
    path('visualization_server_manager/', views.visualization_server_manager, name='visualization_server_manager'),
    
    # Server management API endpoints
    path('api/servers/<str:server_type>/start', views.start_server, name='start_server'),
    path('api/servers/<str:server_type>/stop/<int:port>', views.stop_server, name='stop_server'),
    path('api/servers/status/', views.get_server_status, name='server_status'),
    
    # Basic histogram routes
    path('histogram<int:num>/', views.new_view, name='histogram'),
    re_path(r'^histogram\d+/(?P<path>.*)$', views.new_view, name='histogram_proxy'),
    path('histogram/', views.new_view, name='default_histogram'),
    
    # General histogram routes
    path('histogramgeneral<int:num>/', views.new_view2, name='histogram_general'),
    re_path(r'^histogramgeneral\d+/(?P<path>.*)$', views.new_view2, name='histogram_general_proxy'),
    path('histogramgeneral/', views.new_view2, name='default_histogram_general'),
    
    # OOD analyzer routes
    path('oodanalyzer<int:num>/', views.new_view3, name='ood_analyzer'),
    re_path(r'^oodanalyzer\d+/(?P<path>.*)$', views.new_view3, name='ood_analyzer_proxy'),
    path('oodanalyzer/', views.new_view3, name='default_ood_analyzer'),
    
    path('new2/', views.new_view2, name='new_view2'),
    re_path(r'^new2/(?P<path>.*)$', views.new_view2, name='new_proxy2'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('new3/', views.new_view3, name='new_view3'),
    re_path(r'^new3/(?P<path>.*)$', views.new_view3, name='new_proxy3'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
