from django.urls import path, re_path as url
from django.contrib import admin
from home import views, ml , dt

urlpatterns = [
    path('', views.index, name='index'),
    path('login', views.loginUser, name='login'),
    path('logout', views.logoutUser, name='logout'),
    path('register', views.register, name='register'),
    path('upload/', views.upload, name='upload'),
    path('results/', views.results, name='results'),
    path('datasets/', views.datasets, name='datasets'),
    path('datastore/', views.datastore, name='datastore'),
    path('download/<str:file>/<str:folder>/<str:visibility>/', views.download_file, name='download_file'),
    path('update_reaction/', views.update_reaction, name='update_reaction'),
    path('process_pca/', ml.process_pca, name='process_pca'),
    path('serve_pca_plot/<str:username>/<int:workspace_number>/', views.serve_pca_plot, name='serve_pca_plot'),


]