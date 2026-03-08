from django.db import models
from django.contrib.auth.models import User
import os


def upload_path(instance, filename):
    return f'uploads/user_{instance.user.id}/{filename}'


def processed_path(instance, filename):
    return f'processed/user_{instance.user.id}/{filename}'


class MediaFile(models.Model):
    FILE_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='media_files')
    original_file = models.FileField(upload_to=upload_path)
    processed_file = models.FileField(upload_to=processed_path, null=True, blank=True)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField(default=0)  # bytes
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)  # seconds, for video
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.original_filename}"

    @property
    def file_size_display(self):
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 ** 2:
            return f"{self.file_size / 1024:.1f} KB"
        elif self.file_size < 1024 ** 3:
            return f"{self.file_size / (1024 ** 2):.1f} MB"
        return f"{self.file_size / (1024 ** 3):.1f} GB"

    @property
    def extension(self):
        return os.path.splitext(self.original_filename)[1].lower()


class EditOperation(models.Model):
    OPERATION_TYPES = [
        ('detect_objects', 'Object Detection'),
        ('remove_background', 'Background Removal'),
        ('enhance', 'Image Enhancement'),
        ('blur_background', 'Blur Background'),
        ('grayscale', 'Convert to Grayscale'),
        ('sharpen', 'Sharpen Image'),
        ('denoise', 'Denoise'),
        ('brightness', 'Adjust Brightness'),
        ('contrast', 'Adjust Contrast'),
        ('edge_detect', 'Edge Detection'),
        ('cartoon', 'Cartoon Effect'),
        ('emboss', 'Emboss Effect'),
        ('sepia', 'Sepia Tone'),
        ('change_bg_color', 'Change Background Color'),
        ('prompt_edit', 'Prompt-Based Edit'),
    ]

    media_file = models.ForeignKey(MediaFile, on_delete=models.CASCADE, related_name='operations')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    operation_type = models.CharField(max_length=50, choices=OPERATION_TYPES)
    prompt = models.TextField(blank=True, null=True)
    parameters = models.JSONField(default=dict, blank=True)
    result_file = models.FileField(upload_to=processed_path, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')],
        default='pending'
    )
    error_message = models.TextField(blank=True, null=True)
    processing_time = models.FloatField(null=True, blank=True)  # seconds
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.operation_type} on {self.media_file.original_filename}"


class DetectedObject(models.Model):
    operation = models.ForeignKey(EditOperation, on_delete=models.CASCADE, related_name='detected_objects')
    label = models.CharField(max_length=100)
    confidence = models.FloatField()
    x = models.IntegerField()
    y = models.IntegerField()
    width = models.IntegerField()
    height = models.IntegerField()

    def __str__(self):
        return f"{self.label} ({self.confidence:.2f})"
