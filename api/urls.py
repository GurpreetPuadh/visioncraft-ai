from django.urls import path
from . import views

urlpatterns = [
    path('stats/', views.api_stats, name='api_stats'),
    path('files/', views.api_files, name='api_files'),
    path('files/<int:file_id>/', views.api_file_detail, name='api_file_detail'),
    path('operations/', views.api_operations, name='api_operations'),
    path('operations/<int:op_id>/', views.api_operation_detail, name='api_operation_detail'),
    path('operations/meta/', views.api_operations_list_meta, name='api_operations_meta'),
    path('parse-prompt/', views.api_parse_prompt, name='api_parse_prompt'),
]
