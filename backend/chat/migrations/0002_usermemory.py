from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0001_initial"),
        ("courses", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserMemory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("topic", models.CharField(max_length=200, verbose_name="知识点")),
                ("mastery", models.FloatField(default=0.5, verbose_name="掌握程度 (0-1)")),
                ("question_count", models.PositiveIntegerField(default=1, verbose_name="提问次数")),
                ("last_asked_at", models.DateTimeField(auto_now=True, verbose_name="最近提问")),
                ("notes", models.TextField(blank=True, default="", verbose_name="AI 备注")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("user", models.ForeignKey(on_delete=models.CASCADE, related_name="memories", to="accounts.user", verbose_name="用户")),
                ("course", models.ForeignKey(on_delete=models.CASCADE, related_name="user_memories", to="courses.course", verbose_name="课程")),
            ],
            options={
                "db_table": "user_memory",
                "verbose_name": "用户记忆",
                "verbose_name_plural": "用户记忆",
                "ordering": ["-last_asked_at"],
                "unique_together": {("user", "course", "topic")},
            },
        ),
    ]
