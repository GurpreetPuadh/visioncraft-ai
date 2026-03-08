from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('register/', views.register_view, name='register'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('gallery/', views.gallery, name='gallery'),
    path('upload/', views.upload_file, name='upload'),
    path('editor/<int:file_id>/', views.editor_view, name='editor'),
    path('editor/<int:file_id>/apply/', views.apply_edit, name='apply_edit'),
    path('editor/<int:file_id>/delete/', views.delete_file, name='delete_file'),
    path('history/', views.operation_history, name='history'),
    path('download/<int:op_id>/', views.download_result, name='download_result'),
]
