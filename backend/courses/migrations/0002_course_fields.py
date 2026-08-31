from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="max_students",
            field=models.PositiveIntegerField(default=60, verbose_name="最大学生数"),
        ),
        migrations.AddField(
            model_name="course",
            name="college",
            field=models.CharField(blank=True, default="", max_length=100, verbose_name="学院"),
        ),
        migrations.AddField(
            model_name="course",
            name="major",
            field=models.CharField(blank=True, default="", max_length=100, verbose_name="专业"),
        ),
        migrations.AddField(
            model_name="course",
            name="grade",
            field=models.CharField(blank=True, default="", max_length=50, verbose_name="年级"),
        ),
        migrations.AddField(
            model_name="course",
            name="semester",
            field=models.CharField(blank=True, default="", max_length=50, verbose_name="学期"),
        ),
        migrations.AddField(
            model_name="course",
            name="schedule",
            field=models.CharField(blank=True, default="", max_length=200, verbose_name="上课时间"),
        ),
    ]