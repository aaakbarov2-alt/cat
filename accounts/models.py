from django.db import models
from django.contrib.auth.models import User


class StudentProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    xp = models.IntegerField(default=0)
    streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    daily_goal = models.IntegerField(default=60)

    target_band = models.FloatField(default=7.5)

    def __str__(self):
        return self.user.username


class DailyMissionClaim(models.Model):
    """Records one XP reward per student, mission, and calendar day."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="daily_mission_claims")
    mission_key = models.CharField(max_length=40)
    completed_on = models.DateField()
    xp_awarded = models.PositiveIntegerField()
    claimed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "mission_key", "completed_on"],
                name="unique_daily_mission_claim",
            ),
        ]
        ordering = ["-completed_on", "-claimed_at"]

    def __str__(self):
        return f"{self.user} · {self.mission_key} · {self.completed_on}"
