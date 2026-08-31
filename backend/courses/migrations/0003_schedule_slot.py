from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0002_course_fields"),
    ]

    operations = [
        # Remove flat schedule field (replaced by ScheduleSlot)
        migrations.RemoveField(model_name="course", name="schedule"),
        # Add ScheduleSlot model
        migrations.CreateModel(
            name="ScheduleSlot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("weekday", models.PositiveSmallIntegerField(choices=[(1, "周一"), (2, "周二"), (3, "周三"), (4, "周四"), (5, "周五"), (6, "周六"), (7, "周日")], verbose_name="星期")),
                ("start_time", models.TimeField(verbose_name="开始时间")),
                ("end_time", models.TimeField(verbose_name="结束时间")),
                ("week_start", models.PositiveSmallIntegerField(default=1, verbose_name="起始周")),
                ("week_end", models.PositiveSmallIntegerField(default=18, verbose_name="结束周")),
                ("location", models.CharField(blank=True, default="", max_length=100, verbose_name="上课地点")),
                ("course", models.ForeignKey(on_delete=models.CASCADE, related_name="schedule_slots", to="courses.course", verbose_name="课程")),
            ],
            options={
                "db_table": "schedule_slot",
                "verbose_name": "上课时段",
                "verbose_name_plural": "上课时段",
                "ordering": ["week_start", "weekday", "start_time"],
            },
        ),
    ]