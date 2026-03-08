import os
import time
import json
import uuid
from pathlib import Path

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.conf import settings
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta

from .models import MediaFile, EditOperation, DetectedObject
from .ai_engine import process_image, process_video, parse_prompt


# ─── Public Views ─────────────────────────────────────────────────────────────

def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'editor/landing.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to VisionCraft, {user.username}!')
            return redirect('dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserCreationForm()
    return render(request, 'auth/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('landing')


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    user = request.user
    media_files = MediaFile.objects.filter(user=user)

    stats = {
        'total_files': media_files.count(),
        'images': media_files.filter(file_type='image').count(),
        'videos': media_files.filter(file_type='video').count(),
        'total_operations': EditOperation.objects.filter(user=user).count(),
        'storage_used': media_files.aggregate(total=Sum('file_size'))['total'] or 0,
    }

    recent_files = media_files[:6]
    recent_ops = EditOperation.objects.filter(user=user).select_related('media_file')[:5]

    return render(request, 'editor/dashboard.html', {
        'stats': stats,
        'recent_files': recent_files,
        'recent_ops': recent_ops,
    })


# ─── Gallery ──────────────────────────────────────────────────────────────────

@login_required
def gallery(request):
    file_type = request.GET.get('type', 'all')
    files = MediaFile.objects.filter(user=request.user)

    if file_type == 'image':
        files = files.filter(file_type='image')
    elif file_type == 'video':
        files = files.filter(file_type='video')

    return render(request, 'editor/gallery.html', {
        'files': files,
        'active_filter': file_type,
    })


# ─── Upload ───────────────────────────────────────────────────────────────────

@login_required
def upload_file(request):
    if request.method == 'POST':
        uploaded = request.FILES.get('file')
        if not uploaded:
            return JsonResponse({'error': 'No file provided'}, status=400)

        ext = Path(uploaded.name).suffix.lower()
        if ext in settings.SUPPORTED_IMAGE_FORMATS:
            file_type = 'image'
        elif ext in settings.SUPPORTED_VIDEO_FORMATS:
            file_type = 'video'
        else:
            return JsonResponse({'error': f'Unsupported file format: {ext}'}, status=400)

        media = MediaFile(
            user=request.user,
            original_filename=uploaded.name,
            file_size=uploaded.size,
            file_type=file_type,
            status='completed',
        )
        media.original_file = uploaded
        media.save()

        # Get image dimensions
        if file_type == 'image':
            try:
                import cv2
                import numpy as np
                data = np.frombuffer(uploaded.read(), np.uint8) if uploaded.tell() == 0 else None
                img_path = media.original_file.path
                img = cv2.imread(img_path)
                if img is not None:
                    media.height, media.width = img.shape[:2]
                    media.save()
            except Exception:
                pass
        elif file_type == 'video':
            try:
                import cv2
                cap = cv2.VideoCapture(media.original_file.path)
                media.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                media.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS) or 25
                frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                media.duration = frames / fps if fps else 0
                cap.release()
                media.save()
            except Exception:
                pass

        return JsonResponse({
            'id': media.id,
            'filename': media.original_filename,
            'file_type': media.file_type,
            'file_size': media.file_size_display,
            'url': media.original_file.url,
            'redirect': f'/editor/{media.id}/',
        })

    return render(request, 'editor/upload.html')


# ─── Editor ───────────────────────────────────────────────────────────────────

@login_required
def editor_view(request, file_id):
    media = get_object_or_404(MediaFile, id=file_id, user=request.user)
    operations = media.operations.all()

    OPERATION_CHOICES = EditOperation.OPERATION_TYPES

    return render(request, 'editor/editor.html', {
        'media': media,
        'operations': operations,
        'operation_choices': OPERATION_CHOICES,
    })


@login_required
@require_POST
def apply_edit(request, file_id):
    media = get_object_or_404(MediaFile, id=file_id, user=request.user)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    operation_type = body.get('operation')
    prompt = body.get('prompt', '')
    params = body.get('params', {})

    # If prompt-based, parse it
    if operation_type == 'prompt_edit' or (not operation_type and prompt):
        operation_type, parsed_params = parse_prompt(prompt)
        params = {**parsed_params, **params}

    if not operation_type:
        return JsonResponse({'error': 'No operation specified'}, status=400)

    # Build output path
    out_dir = Path(settings.MEDIA_ROOT) / 'processed' / f'user_{request.user.id}'
    out_dir.mkdir(parents=True, exist_ok=True)
    uid = uuid.uuid4().hex[:8]
    ext = Path(media.original_filename).suffix.lower()
    out_filename = f'{operation_type}_{uid}{ext}'
    out_path = str(out_dir / out_filename)
    in_path = media.original_file.path

    # Create operation record
    op = EditOperation.objects.create(
        media_file=media,
        user=request.user,
        operation_type=operation_type,
        prompt=prompt,
        parameters=params,
        status='pending',
    )

    try:
        if media.file_type == 'image':
            result = process_image(in_path, out_path, operation_type, params)
        else:
            result = process_video(
                in_path, out_path, operation_type, params,
                max_frames=settings.MAX_VIDEO_FRAMES
            )

        # Save result file
        rel_path = os.path.relpath(out_path, settings.MEDIA_ROOT)
        op.result_file.name = rel_path
        op.status = 'completed'
        op.processing_time = result.get('processing_time')
        op.save()

        # Save detected objects if any
        for det in result.get('detections', []):
            DetectedObject.objects.create(
                operation=op,
                label=det['label'],
                confidence=det['confidence'],
                x=det['x'], y=det['y'],
                width=det['width'], height=det['height'],
            )

        response_data = {
            'status': 'completed',
            'operation_id': op.id,
            'operation_type': operation_type,
            'result_url': request.build_absolute_uri(settings.MEDIA_URL + rel_path),
            'processing_time': result.get('processing_time'),
        }

        if operation_type == 'detect_objects':
            response_data['detections'] = result.get('detections', [])
            response_data['count'] = result.get('count', 0)

        return JsonResponse(response_data)

    except Exception as e:
        op.status = 'failed'
        op.error_message = str(e)
        op.save()
        return JsonResponse({'error': str(e), 'status': 'failed'}, status=500)


@login_required
def delete_file(request, file_id):
    media = get_object_or_404(MediaFile, id=file_id, user=request.user)
    if request.method == 'POST':
        # Clean up physical files
        try:
            if media.original_file and os.path.exists(media.original_file.path):
                os.remove(media.original_file.path)
        except Exception:
            pass
        media.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'deleted'})
        messages.success(request, 'File deleted successfully.')
        return redirect('gallery')
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def operation_history(request):
    ops = EditOperation.objects.filter(user=request.user).select_related('media_file')
    return render(request, 'editor/history.html', {'operations': ops})


@login_required
def download_result(request, op_id):
    op = get_object_or_404(EditOperation, id=op_id, user=request.user)
    if not op.result_file:
        messages.error(request, 'No result file available.')
        return redirect('dashboard')

    file_path = op.result_file.path
    if not os.path.exists(file_path):
        messages.error(request, 'File not found.')
        return redirect('dashboard')

    ext = Path(file_path).suffix.lower()
    content_types = {
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
        '.bmp': 'image/bmp', '.webp': 'image/webp',
        '.mp4': 'video/mp4', '.avi': 'video/avi', '.mov': 'video/quicktime',
    }
    ct = content_types.get(ext, 'application/octet-stream')

    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type=ct)
        response['Content-Disposition'] = f'attachment; filename="visioncraft_{op.operation_type}{ext}"'
        return response
