import os
import uuid
from django.conf import settings
from rest_framework.decorators import api_view
from .models import UploadedFile
from .serializers import UploadedFileSerializer
from accounts.views import make_response
from accounts.models import User
from services.pagination import parse_paging


def _can_access_file(user, uf) -> bool:
    """文件访问权限：admin / 上传者本人 / 该文件所属课程的授课教师。

    此前 GET /api/files/<pk> 只要求登录，任何用户都能读到别人的文件元数据
    （其中包含服务端绝对路径 stored_path）。
    """
    if user.role == User.Role.ADMIN:
        return True
    if uf.uploader_id == user.id:
        return True
    return bool(uf.course_id and uf.course and uf.course.teacher_id == user.id)


@api_view(['GET', 'POST'])
def file_list(request):
    if request.method == 'GET':
        qs = UploadedFile.objects.filter(uploader=request.user).order_by('-created_at')
        course_id = request.GET.get('course_id')
        if course_id:
            qs = qs.filter(course_id=course_id)
        page, size = parse_paging(request)
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
    try:
        uf = UploadedFile.objects.select_related('course').get(pk=pk)
    except UploadedFile.DoesNotExist:
        return make_response(code=404, message='文件不存在', http_status=404)
    # 归属校验：admin / 上传者 / 该课程的授课教师
    if not _can_access_file(request.user, uf):
        return make_response(code=403, message='无权访问该文件', http_status=403)

    if request.method == 'GET':
        return make_response(data=UploadedFileSerializer(uf).data)

    if os.path.exists(uf.stored_path):
        os.remove(uf.stored_path)
    uf.delete()
    return make_response(message='删除成功')
