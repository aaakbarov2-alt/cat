from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import DailyMissionClaim, StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(ModelAdmin):
    list_display = ("user", "target_band", "daily_goal", "xp", "streak")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")
    list_filter = ("target_band", "daily_goal")


@admin.register(DailyMissionClaim)
class DailyMissionClaimAdmin(ModelAdmin):
    list_display = ("user", "mission_key", "completed_on", "xp_awarded", "claimed_at")
    list_filter = ("mission_key", "completed_on")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("claimed_at",)
