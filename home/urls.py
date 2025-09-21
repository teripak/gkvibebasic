from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('api/save-upload-settings/', views.save_upload_settings, name='save_upload_settings'),
    path('api/get-upload-settings/', views.get_upload_settings, name='get_upload_settings'),
    path('api/send-chat-message/', views.send_chat_message, name='send_chat_message'),
    path('api/get-chat-history/', views.get_chat_history, name='get_chat_history'),
    path('api/get-current-llm/', views.get_current_llm, name='get_current_llm'),
    path('api/upload-document/', views.upload_document, name='upload_document'),
    path('api/get-user-documents/', views.get_user_documents, name='get_user_documents'),
    path('api/delete-documents/', views.delete_documents, name='delete_documents'),
    # RAG 관련 API들
    path('api/process-document-for-rag/', views.process_document_for_rag, name='process_document_for_rag'),
    path('api/document/<int:document_id>/processing-status/', views.get_document_processing_status, name='get_document_processing_status'),
    path('api/document/<int:document_id>/chunks/', views.get_document_chunks, name='get_document_chunks'),
    path('api/update-document-selection/', views.update_document_selection, name='update_document_selection'),
    path('api/get-selected-documents/', views.get_selected_documents, name='get_selected_documents'),
    path('api/delete-document-rag-data/', views.delete_document_rag_data, name='delete_document_rag_data'),
]
