from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count
from django.contrib.auth.models import User

from editor.models import MediaFile, EditOperation, DetectedObject
from editor.ai_engine import parse_prompt


# ─── Media File Serializers (manual, no extra deps) ──────────────────────────

def serialize_media(m, request=None):
    return {
        'id': m.id,
        'filename': m.original_filename,
        'file_type': m.file_type,
        'file_size': m.file_size,
        'file_size_display': m.file_size_display,
        'width': m.width,
        'height': m.height,
        'duration': m.duration,
        'status': m.status,
        'created_at': m.created_at.isoformat(),
        'original_url': request.build_absolute_uri(m.original_file.url) if request and m.original_file else None,
        'processed_url': request.build_absolute_uri(m.processed_file.url) if request and m.processed_file else None,
    }


def serialize_operation(op, request=None):
    result_url = None
    if op.result_file:
        try:
            result_url = request.build_absolute_uri(op.result_file.url) if request else op.result_file.url
        except Exception:
            pass
    return {
        'id': op.id,
        'media_file_id': op.media_file_id,
        'media_filename': op.media_file.original_filename,
        'operation_type': op.operation_type,
        'prompt': op.prompt,
        'parameters': op.parameters,
        'status': op.status,
        'processing_time': op.processing_time,
        'error_message': op.error_message,
        'result_url': result_url,
        'created_at': op.created_at.isoformat(),
        'detected_objects': [
            {'label': d.label, 'confidence': d.confidence,
             'x': d.x, 'y': d.y, 'width': d.width, 'height': d.height}
            for d in op.detected_objects.all()
        ] if op.operation_type == 'detect_objects' else [],
    }


# ─── API Endpoints ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_stats(request):
    """User statistics overview."""
    user = request.user
    files = MediaFile.objects.filter(user=user)
    ops = EditOperation.objects.filter(user=user)

    op_breakdown = {}
    for op in ops.values('operation_type').annotate(count=Count('id')):
        op_breakdown[op['operation_type']] = op['count']

    return Response({
        'user': user.username,
        'total_files': files.count(),
        'images': files.filter(file_type='image').count(),
        'videos': files.filter(file_type='video').count(),
        'total_operations': ops.count(),
        'completed_operations': ops.filter(status='completed').count(),
        'failed_operations': ops.filter(status='failed').count(),
        'storage_bytes': files.aggregate(total=Sum('file_size'))['total'] or 0,
        'operation_breakdown': op_breakdown,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_files(request):
    """List all media files for authenticated user."""
    file_type = request.query_params.get('type')
    files = MediaFile.objects.filter(user=request.user)
    if file_type in ('image', 'video'):
        files = files.filter(file_type=file_type)

    return Response({
        'count': files.count(),
        'results': [serialize_media(f, request) for f in files],
    })


@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def api_file_detail(request, file_id):
    """Get or delete a single media file."""
    try:
        media = MediaFile.objects.get(id=file_id, user=request.user)
    except MediaFile.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if request.method == 'DELETE':
        import os
        try:
            if media.original_file and os.path.exists(media.original_file.path):
                os.remove(media.original_file.path)
        except Exception:
            pass
        media.delete()
        return Response({'status': 'deleted'})

    return Response(serialize_media(media, request))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_operations(request):
    """List all edit operations for authenticated user."""
    file_id = request.query_params.get('file_id')
    ops = EditOperation.objects.filter(user=request.user).select_related('media_file')
    if file_id:
        ops = ops.filter(media_file_id=file_id)

    return Response({
        'count': ops.count(),
        'results': [serialize_operation(op, request) for op in ops],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_operation_detail(request, op_id):
    """Get a single operation detail."""
    try:
        op = EditOperation.objects.get(id=op_id, user=request.user)
    except EditOperation.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    return Response(serialize_operation(op, request))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_parse_prompt(request):
    """Parse a natural language prompt into an operation."""
    prompt = request.data.get('prompt', '')
    if not prompt:
        return Response({'error': 'Prompt is required'}, status=400)

    operation, params = parse_prompt(prompt)
    return Response({
        'prompt': prompt,
        'detected_operation': operation,
        'parameters': params,
        'description': dict(EditOperation.OPERATION_TYPES).get(operation, operation),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_operations_list_meta(request):
    """List all available operations with descriptions."""
    return Response({
        'operations': [
            {'key': k, 'label': v}
            for k, v in EditOperation.OPERATION_TYPES
        ]
    })
