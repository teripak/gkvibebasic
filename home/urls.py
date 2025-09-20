from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/save-upload-settings/', views.save_upload_settings, name='save_upload_settings'),
    path('api/get-upload-settings/', views.get_upload_settings, name='get_upload_settings'),
    path('api/send-chat-message/', views.send_chat_message, name='send_chat_message'),
    path('api/get-chat-history/', views.get_chat_history, name='get_chat_history'),
    path('api/get-current-llm/', views.get_current_llm, name='get_current_llm'),
]
