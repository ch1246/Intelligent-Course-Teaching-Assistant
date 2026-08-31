import os
import uuid
from django.conf import settings
from rest_framework.decorators import api_view
from .models import UploadedFile
from .serializers import UploadedFileSerializer
from accounts.views import make_response
from accounts.models import User


@api_view(['GET', 'POST'])
def file_list(request):
    if request.method == 'GET':
        qs = UploadedFile.objects.filter(uploader=request.user).order_by('-created_at')
        course_id = request.GET.get('course_id')
        if course_id:
            qs = qs.filter(course_id=course_id)
        page = int(request.GET.get('page', 1))
        size = int(request.GET.get('pageSize', 20))
        total = qs.count()
        files = qs[(page - 1) * size: page * size]
        return make_response(data={
            'list': UploadedFileSerializer(files, many=True).data,
            'total': total, 'page': page, 'pageSize': size,
        })
    # POST: upload
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return make_response(code=400, message='请选择文件', http_status=400)
    course_id = request.data.get('course_id')
    ext = os.path.splitext(uploaded_file.name)[1]
    stored_name = f'{uuid.uuid4().hex}{ext}'
    stored_path = os.path.join(settings.MEDIA_ROOT, 'files', stored_name)
    os.makedirs(os.path.dirname(stored_path), exist_ok=True)
    with open(stored_path, 'wb+') as dest:
        for chunk in uploaded_file.chunks():
            dest.write(chunk)
    uf = UploadedFile.objects.create(
        original_name=uploaded_file.name, stored_path=stored_path,
        file_size=uploaded_file.size, mime_type=uploaded_file.content_type or '',
        course_id=course_id if course_id else None, uploader=request.user,
    )
    return make_response(data=UploadedFileSerializer(uf).data)


@api_view(['GET', 'DELETE'])
def file_detail(request, pk):
    if request.method == 'GET':
        try:
            uf = UploadedFile.objects.get(pk=pk)
        except UploadedFile.DoesNotExist:
            return make_response(code=404, message='文件不存在', http_status=404)
        return make_response(data=UploadedFileSerializer(uf).data)
    # Admin or owner can delete
    try:
        uf = UploadedFile.objects.get(pk=pk)
    except UploadedFile.DoesNotExist:
        return make_response(code=404, message='文件不存在', http_status=404)
    if request.user.role != User.Role.ADMIN and uf.uploader != request.user:
        return make_response(code=403, message='无权限', http_status=403)
    if os.path.exists(uf.stored_path):
        os.remove(uf.stored_path)
    uf.delete()
    return make_response(message='删除成功')
