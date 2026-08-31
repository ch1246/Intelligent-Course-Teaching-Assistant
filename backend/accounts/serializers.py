from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    course_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "phone", "avatar", "signature",
            "sex", "age", "dept", "major", "grade", "role", "student_id",
            "is_approved", "approved_at", "is_active", "course_count",
            "date_joined", "last_login",
        ]
        read_only_fields = ["id", "date_joined", "last_login", "approved_at", "course_count"]

    def get_course_count(self, obj):
        return getattr(obj, "course_count", 0)

    def validate(self, attrs):
        """学生角色必须填写专业和年级；其他角色不强制。

        仅在「创建用户」或「请求显式提交 major/grade」时校验，
        避免纯状态切换（如启用/禁用）因历史数据缺专业而误报错。
        """
        role = attrs.get("role", getattr(self.instance, "role", None))
        if role != User.Role.STUDENT:
            return attrs

        is_create = self.instance is None
        submits_major = "major" in attrs
        submits_grade = "grade" in attrs
        if not is_create and not submits_major and not submits_grade:
            return attrs

        major = attrs.get("major", getattr(self.instance, "major", ""))
        grade = attrs.get("grade", getattr(self.instance, "grade", ""))
        errors = {}
        if not major:
            errors["major"] = "学生必须填写专业"
        if not grade:
            errors["grade"] = "学生必须填写年级"
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    verify_code = serializers.CharField(required=False, allow_blank=True)


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=3, max_length=30)
    password = serializers.CharField(min_length=6)
    student_id = serializers.CharField(required=True, max_length=30, help_text="学号")
    name = serializers.CharField(required=False, max_length=30, help_text="姓名（默认同学号）")
    sex = serializers.ChoiceField(choices=[("男", "男"), ("女", "女")], required=True, help_text="性别")
    dept = serializers.CharField(required=True, max_length=100, help_text="学院")
    major = serializers.CharField(required=True, max_length=100, help_text="专业")
    grade = serializers.CharField(required=True, max_length=50, help_text="年级，如 2024级")
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=User.Role.choices, default=User.Role.STUDENT)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=6)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "phone", "avatar", "signature",
                  "sex", "age", "dept", "major", "grade", "student_id"]