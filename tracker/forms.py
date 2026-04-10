from django import forms
from .models import Task


class TaskForm(forms.ModelForm):
    estimated_hours = forms.IntegerField(
        required=False,
        min_value=0,
        label="Estimated hours (optional)",
    )
    estimated_minutes_part = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=59,
        label="Estimated minutes (optional)",
    )

    class Meta:
        model = Task
        # IMPORTANT: exclude estimated_minutes from the visible fields
        fields = ["title", "category", "due_date",
                  "start_at", "end_at", "notes", "completed"]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "start_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If editing an existing task, prefill hours/minutes from estimated_minutes
        if self.instance and self.instance.pk and self.instance.estimated_minutes is not None:
            total = int(self.instance.estimated_minutes)
            self.fields["estimated_hours"].initial = total // 60
            self.fields["estimated_minutes_part"].initial = total % 60

    def clean(self):
        cleaned = super().clean()

        hours = cleaned.get("estimated_hours")
        minutes = cleaned.get("estimated_minutes_part")

        # Treat blank as 0
        hours = 0 if hours in (None, "") else int(hours)
        minutes = 0 if minutes in (None, "") else int(minutes)

        total = hours * 60 + minutes

        # If both left blank/0, store NULL (keeps DB tidy)
        cleaned["estimated_minutes_total"] = total if total > 0 else None
        return cleaned

    def save(self, commit=True):
        obj: Task = super().save(commit=False)
        obj.estimated_minutes = self.cleaned_data.get("estimated_minutes_total")
        if commit:
            obj.save()
            self.save_m2m()
        return obj