from django.db import models
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError

class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)

    def __str__(self) -> str:
        return self.name

class Task(models.Model):
    title = models.CharField(max_length=120)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL,related_name="task")
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    estimated_minutes = models.PositiveIntegerField(null=True, blank=True)

    @property
    def estimated_display(self) -> str:
        if not self.estimated_minutes:
            return "None"
        total = int(self.estimated_minutes)
        hours = total // 60
        minutes = total % 60
        if hours and minutes:
            return f"{hours}h {minutes}m"
        if hours:
            return f"{hours}h"
        return f"{minutes}m"

    def clean(self):
        # If both are set, enforce end >= start
        if self.start_at and self.end_at and self.end_at < self.start_at:
            raise ValidationError({"end_at": "End time must be after start time."})

    @property
    def duration_minutes(self) -> int | None:
        if self.start_at and self.end_at:
            delta: timedelta = self.end_at - self.start_at
            return max(0, int(delta.total_seconds() // 60))
        return None

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("task_detail", kwargs={"pk": self.pk})