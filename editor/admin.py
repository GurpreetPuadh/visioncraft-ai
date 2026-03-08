from django.contrib import admin
from .models import MediaFile, EditOperation, DetectedObject


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'user', 'file_type', 'file_size_display', 'status', 'created_at']
    list_filter = ['file_type', 'status', 'created_at']
    search_fields = ['original_filename', 'user__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(EditOperation)
class EditOperationAdmin(admin.ModelAdmin):
    list_display = ['operation_type', 'media_file', 'user', 'status', 'processing_time', 'created_at']
    list_filter = ['operation_type', 'status', 'created_at']
    search_fields = ['prompt', 'user__username']
    readonly_fields = ['created_at']


@admin.register(DetectedObject)
class DetectedObjectAdmin(admin.ModelAdmin):
    list_display = ['label', 'confidence', 'operation', 'x', 'y', 'width', 'height']
    list_filter = ['label']
