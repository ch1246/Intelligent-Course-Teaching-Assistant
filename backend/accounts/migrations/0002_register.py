from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]
    operations = [
        migrations.AddField(model_name="user", name="student_id", field=models.CharField(blank=True, default="", max_length=30, verbose_name="学号")),
        migrations.AddField(model_name="user", name="is_approved", field=models.BooleanField(default=False, verbose_name="审核通过")),
        migrations.AddField(model_name="user", name="approved_at", field=models.DateTimeField(blank=True, null=True, verbose_name="审核时间")),
        migrations.AddField(model_name="user", name="approved_by", field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="approved_users", to="accounts.user", verbose_name="审核人")),
        migrations.AlterModelOptions(name="user", options={"verbose_name": "用户", "verbose_name_plural": "用户"}),
    ]