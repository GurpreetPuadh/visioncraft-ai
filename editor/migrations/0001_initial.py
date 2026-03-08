from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import editor.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MediaFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_file', models.FileField(upload_to=editor.models.upload_path)),
                ('processed_file', models.FileField(blank=True, null=True, upload_to=editor.models.processed_path)),
                ('file_type', models.CharField(choices=[('image', 'Image'), ('video', 'Video')], max_length=10)),
                ('original_filename', models.CharField(max_length=255)),
                ('file_size', models.PositiveBigIntegerField(default=0)),
                ('width', models.PositiveIntegerField(blank=True, null=True)),
                ('height', models.PositiveIntegerField(blank=True, null=True)),
                ('duration', models.FloatField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='media_files', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='EditOperation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('operation_type', models.CharField(choices=[
                    ('detect_objects', 'Object Detection'), ('remove_background', 'Background Removal'),
                    ('enhance', 'Image Enhancement'), ('blur_background', 'Blur Background'),
                    ('grayscale', 'Convert to Grayscale'), ('sharpen', 'Sharpen Image'),
                    ('denoise', 'Denoise'), ('brightness', 'Adjust Brightness'),
                    ('contrast', 'Adjust Contrast'), ('edge_detect', 'Edge Detection'),
                    ('cartoon', 'Cartoon Effect'), ('emboss', 'Emboss Effect'),
                    ('sepia', 'Sepia Tone'), ('prompt_edit', 'Prompt-Based Edit'),
                ], max_length=50)),
                ('prompt', models.TextField(blank=True, null=True)),
                ('parameters', models.JSONField(blank=True, default=dict)),
                ('result_file', models.FileField(blank=True, null=True, upload_to=editor.models.processed_path)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('processing_time', models.FloatField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('media_file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='operations', to='editor.mediafile')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='DetectedObject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=100)),
                ('confidence', models.FloatField()),
                ('x', models.IntegerField()),
                ('y', models.IntegerField()),
                ('width', models.IntegerField()),
                ('height', models.IntegerField()),
                ('operation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='detected_objects', to='editor.editoperation')),
            ],
        ),
    ]
