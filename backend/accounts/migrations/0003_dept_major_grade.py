from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_register"),
    ]
    operations = [
        migrations.AddField(model_name="user", name="major", field=models.CharField(blank=True, default="", max_length=100, verbose_name="专业")),
        migrations.AddField(model_name="user", name="grade", field=models.CharField(blank=True, default="", max_length=50, verbose_name="年级")),
        migrations.AlterField(model_name="user", name="student_id", field=models.CharField(blank=True, default="", max_length=30, unique=True, verbose_name="学号")),
    ]