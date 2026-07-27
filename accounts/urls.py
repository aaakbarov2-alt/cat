from django.urls import path, include
from . import views

urlpatterns = [
    path("dashboard/", views.student_dashboard, name="student_dashboard"),
    path("settings/", views.student_settings, name="student_settings"),
    path("missions/<str:mission_key>/claim/", views.claim_daily_mission, name="claim_daily_mission"),
    path("", include("allauth.urls")),
]
