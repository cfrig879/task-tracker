from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)

    def __str__(self) -> str:
        return str(self.name)


class Task(models.Model):
    title = models.CharField(max_length=120)
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="task",
    )
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    estimated_minutes = models.PositiveIntegerField(null=True, blank=True)

    def format_minutes(self, total_minutes: int | None) -> str:
        if total_minutes is None:
            return "None"

        total = int(total_minutes)
        hours = total // 60
        minutes = total % 60

        if hours and minutes:
            return f"{hours}h {minutes}m"
        if hours:
            return f"{hours}h"
        return f"{minutes}m"

    @property
    def estimated_minutes_value(self) -> int | None:
        raw_estimated = self.estimated_minutes
        return raw_estimated if isinstance(raw_estimated, int) else None

    @property
    def start_at_value(self) -> datetime | None:
        raw_start = self.start_at
        return raw_start if isinstance(raw_start, datetime) else None

    @property
    def end_at_value(self) -> datetime | None:
        raw_end = self.end_at
        return raw_end if isinstance(raw_end, datetime) else None

    @property
    def estimated_display(self) -> str:
        estimated = self.estimated_minutes_value
        if estimated is None:
            return "None"
        return self.format_minutes(estimated)

    def clean(self) -> None:
        start = self.start_at_value
        end = self.end_at_value

        if start is not None and end is not None and end < start:
            raise ValidationError({"end_at": "End time must be after start time."})

    @property
    def duration_minutes(self) -> int | None:
        start = self.start_at_value
        end = self.end_at_value

        if start is not None and end is not None:
            delta: timedelta = end - start
            return max(0, int(delta.total_seconds() // 60))

        return None

    @property
    def actual_display(self) -> str:
        actual = self.duration_minutes
        if actual is None:
            return "None"
        return self.format_minutes(actual)

    @property
    def planning_difference_minutes(self) -> int | None:
        estimated = self.estimated_minutes_value
        actual = self.duration_minutes

        if estimated is None or actual is None:
            return None

        return actual - estimated

    @property
    def planning_difference_display(self) -> str:
        difference = self.planning_difference_minutes

        if difference is None:
            return "None"
        if difference == 0:
            return "On track"

        label = "over" if difference > 0 else "under"
        return f"{self.format_minutes(abs(difference))} {label}"

    @property
    def insight_text(self) -> str:
        estimated = self.estimated_minutes_value
        actual = self.duration_minutes

        if estimated is None and actual is None:
            return "Add an estimate and track start and end times to unlock insight."

        if estimated is None:
            return (
                "You tracked actual time, but there is no estimate yet. "
                "Adding one will make planning patterns easier to spot."
            )

        if actual is None:
            return (
                "You set an estimate, but actual time is not available yet. "
                "Track start and end times to compare plan versus reality."
            )

        difference = actual - estimated

        if difference == 0:
            return "Your estimate matched the actual time closely. This task looks well calibrated."

        if difference > 0:
            return "This task took longer than planned. That may point to underestimation or hidden complexity."

        return "This task took less time than expected. You may be leaving extra buffer in this type of work."

    def __str__(self) -> str:
        return str(self.title)

    def get_absolute_url(self) -> str:
        return reverse("task_detail", kwargs={"pk": self.pk})