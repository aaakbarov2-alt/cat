from decimal import Decimal

from django import forms
from django.db import transaction

from .models import StudentProfile


class StudentSettingsForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    target_band = forms.DecimalField(
        min_value=4,
        max_value=9,
        decimal_places=1,
        widget=forms.NumberInput(attrs={"min": "4", "max": "9", "step": "0.5"}),
    )
    daily_goal = forms.IntegerField(min_value=10, max_value=300)

    def __init__(self, *args, user, profile, **kwargs):
        self.user = user
        self.profile = profile
        kwargs.setdefault(
            "initial",
            {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "target_band": profile.target_band,
                "daily_goal": profile.daily_goal,
            },
        )
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "settings-input"

    def clean_target_band(self):
        target_band = self.cleaned_data["target_band"]
        if target_band % Decimal("0.5"):
            raise forms.ValidationError(
                "Choose an IELTS band score in 0.5 increments."
            )
        return target_band

    @transaction.atomic
    def save(self):
        self.user.first_name = self.cleaned_data["first_name"].strip()
        self.user.last_name = self.cleaned_data["last_name"].strip()
        self.user.save(update_fields=["first_name", "last_name"])

        self.profile.target_band = float(self.cleaned_data["target_band"])
        self.profile.daily_goal = self.cleaned_data["daily_goal"]
        self.profile.save(update_fields=["target_band", "daily_goal"])
        return self.user
