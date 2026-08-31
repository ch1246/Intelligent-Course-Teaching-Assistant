from rest_framework import serializers
from .models import Enrollment


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_dept = serializers.SerializerMethodField()
    course_name = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = ['id', 'student', 'student_name', 'student_dept', 'course', 'course_name',
                  'status', 'review_comment', 'enrolled_at', 'reviewed_at']
        read_only_fields = ['id', 'enrolled_at', 'reviewed_at']

    def get_student_name(self, obj):
        return obj.student.username

    def get_student_dept(self, obj):
        return obj.student.dept

    def get_course_name(self, obj):
        return obj.course.name
