from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_studentprofile_last_activity_date")]

    operations = [
        migrations.CreateModel(
            name="DailyMissionClaim",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("mission_key", models.CharField(max_length=40)),
                ("completed_on", models.DateField()),
                ("xp_awarded", models.PositiveIntegerField()),
                ("claimed_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="daily_mission_claims", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-completed_on", "-claimed_at"]},
        ),
        migrations.AddConstraint(
            model_name="dailymissionclaim",
            constraint=models.UniqueConstraint(fields=("user", "mission_key", "completed_on"), name="unique_daily_mission_claim"),
        ),
    ]
