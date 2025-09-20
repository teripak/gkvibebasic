from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/save-upload-settings/', views.save_upload_settings, name='save_upload_settings'),
    path('api/get-upload-settings/', views.get_upload_settings, name='get_upload_settings'),
]
