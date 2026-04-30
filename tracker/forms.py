from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Category, Task


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

class TaskForm(forms.ModelForm):
    due_date = forms.DateField(
        required=True,
        label="Due date",
        widget=forms.DateInput(attrs={"type": "date"}),
        error_messages={"required": "Please choose a due date."},
    )

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
        fields = [
            "title",
            "category",
            "due_date",
            "start_at",
            "end_at",
            "completed",
            "notes",
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.estimated_minutes is not None:
            self.fields["estimated_hours"].initial = self.instance.estimated_minutes // 60
            self.fields["estimated_minutes_part"].initial = self.instance.estimated_minutes % 60

        self.fields["title"].required = True
        self.fields["title"].error_messages = {"required": "Please enter a title."}

        self.fields["due_date"].required = True
        self.fields["due_date"].error_messages = {"required": "Please choose a due date."}

        if self.user is not None and "category" in self.fields:
            self.fields["category"].queryset = Category.objects.filter(user=self.user)

        if "start_at" in self.fields:
            self.fields["start_at"].widget = forms.DateTimeInput(attrs={"type": "datetime-local"})
            self.fields["start_at"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"]

        if "end_at" in self.fields:
            self.fields["end_at"].widget = forms.DateTimeInput(attrs={"type": "datetime-local"})
            self.fields["end_at"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"]

    def save(self, commit=True):
        task = super().save(commit=False)

        hours = self.cleaned_data.get("estimated_hours") or 0
        minutes = self.cleaned_data.get("estimated_minutes_part") or 0

        if hours == 0 and minutes == 0:
            task.estimated_minutes = None
        else:
            task.estimated_minutes = (hours * 60) + minutes

        if commit:
            task.save()
            self.save_m2m()

        return task