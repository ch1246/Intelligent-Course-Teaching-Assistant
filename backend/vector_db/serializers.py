from rest_framework import serializers

from accounts.models import User
from .models import VectorCollection


class VectorCollectionSerializer(serializers.ModelSerializer):
    course_name = serializers.SerializerMethodField()
    # 真实的 Chroma 集合名（course_{course_id}），供前端区分「展示名」与「物理名」。
    # 不能写 source='collection_name' —— DRF 断言 source 与字段名不得相同。
    collection_name = serializers.CharField(read_only=True)

    class Meta:
        model = VectorCollection
        fields = ['id', 'name', 'course', 'course_name', 'collection_name', 'embedding_model',
                  'document_count', 'chunk_count', 'vector_count', 'dimension',
                  'status', 'description', 'last_indexed_at', 'created_at']
        read_only_fields = ['id', 'document_count', 'chunk_count', 'vector_count',
                            'last_indexed_at', 'created_at']

    def get_course_name(self, obj):
        return obj.course.name

    def validate(self, attrs):
        """一门课只能有一个知识库记录。

        多条记录会映射到同一个 Chroma 物理集合（course_{course_id}），
        会造成「删一条记录清空整门课向量库」的数据丢失，因此在写入前拦住。
        """
        request = self.context.get('request')
        instance = self.instance
        course = attrs.get('course', getattr(instance, 'course', None))

        if course is None:
            raise serializers.ValidationError({'course': '请选择所属课程'})

        if instance is None or course.pk != instance.course_id:
            clash = VectorCollection.objects.filter(course=course)
            if instance is not None:
                clash = clash.exclude(pk=instance.pk)
            if clash.exists():
                raise serializers.ValidationError(
                    {'course': f'课程「{course.name}」已有知识库，一门课只能有一个'}
                )

        # 教师只能为自己的课程建/改知识库
        if request is not None and hasattr(request, 'user') and request.user.role == User.Role.TEACHER:
            if getattr(course, 'teacher_id', None) != request.user.id:
                raise serializers.ValidationError({'course': '只能操作自己任教的课程'})

        return attrs
