# Generated migration for UploadedFile.summary field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("files_app", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="uploadedfile",
            name="summary",
            field=models.TextField(blank=True, default="", verbose_name="AI 摘要"),
        ),
    ]
