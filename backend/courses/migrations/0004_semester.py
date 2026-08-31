from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0003_schedule_slot"),
    ]
    operations = [
        migrations.RemoveField(model_name="course", name="semester"),
        migrations.RemoveField(model_name="course", name="grade"),
        migrations.AddField(
            model_name="course", name="semester",
            field=models.CharField(choices=[("fall", "秋季学期 (9月-1月)"), ("spring", "春季学期 (2月-7月)")], default="fall", max_length=20, verbose_name="学期"),
        ),
        migrations.AddField(
            model_name="course", name="year",
            field=models.PositiveIntegerField(default=2025, verbose_name="学年", help_text="例如 2025 表示 2025-2026 学年"),
        ),
        migrations.AddField(
            model_name="course", name="grade",
            field=models.CharField(blank=True, default="", max_length=50, verbose_name="年级"),
        ),
    ]