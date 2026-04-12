# tracker/views.py
from pathlib import Path
import calendar
import csv
import io
from datetime import date, datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .category_forms import CategoryForm
from .forms import TaskForm
from .import_forms import TaskImportForm
from .models import Category, Task

def landing(request):
    return render(request, "tracker/landing.html")

def login_coming_soon(request):
    context = {
        "title": "Sign in is coming soon",
        "message": (
            "Cadence will eventually support personal accounts so users can save "
            "their routines, view long-term patterns, and receive individualized insights."
        ),
    }
    return render(request, "tracker/coming_soon.html", context)

def signup_coming_soon(request):
    context = {
        "title": "Account creation is coming soon",
        "message": (
            "Cadence will eventually support personal accounts so users can build "
            "their own history, routines, and personalized planning insights over time."
        ),
    }
    return render(request, "tracker/coming_soon.html", context)

def download_import_template(request):
    file_path = Path(settings.BASE_DIR) / "tracker" / "static" / "tracker" / "task_import_template.xlsx"

    if not file_path.exists():
        raise Http404("Import template not found.")

    return FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename="task_import_template.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _format_minutes(total_minutes: int | None) -> str:
    if not total_minutes:
        return "0m"
    hours = total_minutes // 60
    minutes = total_minutes % 60
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def _parse_bool(value: str) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y", "t"}


def _parse_csv_date(value: str) -> date | None:
    raw = (value or "").strip()
    if not raw:
        return None
    return datetime.strptime(raw, "%Y-%m-%d").date()


def _parse_csv_datetime(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None

    formats = (
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    )

    parsed: datetime | None = None
    for fmt in formats:
        try:
            parsed = datetime.strptime(raw, fmt)
            break
        except ValueError:
            continue

    if parsed is None:
        raise ValueError(
            f"invalid datetime '{raw}' "
            f"(use YYYY-MM-DD HH:MM or YYYY-MM-DDTHH:MM)"
        )

    if settings.USE_TZ and timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())

    return parsed


def _parse_estimated_minutes(row: dict[str, str]) -> int | None:
    hours_raw = (row.get("estimated_hours") or "").strip()
    minutes_raw = (row.get("estimated_minutes_part") or "").strip()
    total_raw = (row.get("estimated_minutes") or "").strip()

    if total_raw:
        total = int(total_raw)
        return total if total > 0 else None

    hours = int(hours_raw) if hours_raw else 0
    minutes = int(minutes_raw) if minutes_raw else 0
    total = hours * 60 + minutes
    return total if total > 0 else None


def dashboard(request):
    now = timezone.localtime()
    today = now.date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    base_qs = Task.objects.select_related("category")

    overdue_tasks = list(
        base_qs.filter(
            completed=False,
            due_date__lt=today,
        ).order_by("due_date", "title")[:5]
    )

    today_tasks = list(
        base_qs.filter(completed=False)
        .filter(Q(due_date=today) | Q(start_at__date=today))
        .order_by("start_at", "due_date", "title")[:5]
    )

    next_up_tasks = list(
        base_qs.filter(completed=False)
        .filter(Q(start_at__date__gt=today) | Q(due_date__gt=today))
        .order_by("start_at", "due_date", "title")[:5]
    )

    upcoming_tasks = list(
        base_qs.filter(completed=False)
        .filter(Q(start_at__isnull=False) | Q(due_date__isnull=False))
        .order_by("start_at", "due_date", "title")[:5]
    )

    recent_activity_tasks = list(base_qs.order_by("-updated_at", "-created_at")[:5])

    overdue_count = base_qs.filter(completed=False, due_date__lt=today).count()
    due_today_count = base_qs.filter(completed=False, due_date=today).count()
    missing_estimate_count = base_qs.filter(
        completed=False,
        estimated_minutes__isnull=True,
    ).count()
    missing_actual_duration_count = (
        base_qs.filter(completed=True, start_at__isnull=True).count()
        + base_qs.filter(
            completed=True,
            start_at__isnull=False,
            end_at__isnull=True,
        ).count()
    )
    uncategorized_count = base_qs.filter(category__isnull=True).count()

    week_tasks = base_qs.filter(updated_at__date__range=(week_start, week_end))
    completed_this_week_count = week_tasks.filter(completed=True).count()

    planned_this_week_minutes = sum(task.estimated_minutes or 0 for task in week_tasks)
    actual_this_week_minutes = sum(
        task.duration_minutes or 0
        for task in week_tasks
        if task.duration_minutes is not None
    )

    planned_this_week_display = _format_minutes(planned_this_week_minutes)
    actual_this_week_display = _format_minutes(actual_this_week_minutes)

    largest_overrun_category_name = "None yet"
    category_overruns: dict[str, int] = {}

    for task in week_tasks:
        if task.estimated_minutes and task.duration_minutes is not None:
            diff = task.duration_minutes - task.estimated_minutes
            if diff > 0:
                category_name = task.category.name if task.category else "Uncategorized"
                category_overruns[category_name] = (
                    category_overruns.get(category_name, 0) + diff
                )

    if category_overruns:
        largest_overrun_category_name = max(
            category_overruns,
            key=category_overruns.get,
        )

    recent_detailed_tasks = list(
        base_qs.filter(updated_at__date__range=(week_start, week_end))[:25]
    )

    total_recent_entries = len(recent_detailed_tasks)
    sufficiently_detailed_entries = sum(
        1
        for task in recent_detailed_tasks
        if task.category_id
        and task.estimated_minutes
        and task.duration_minutes is not None
    )
    insight_completion_percent = (
        round((sufficiently_detailed_entries / total_recent_entries) * 100)
        if total_recent_entries
        else 0
    )

    underestimated_count = 0
    overrun_by_category: dict[str, int] = {}
    completed_without_duration_count = 0

    for task in week_tasks:
        duration = task.duration_minutes

        if task.completed and duration is None:
            completed_without_duration_count += 1

        if (
            task.estimated_minutes
            and duration is not None
            and duration > task.estimated_minutes
        ):
            underestimated_count += 1
            category_name = task.category.name if task.category else "Uncategorized"
            overrun_by_category[category_name] = (
                overrun_by_category.get(category_name, 0)
                + (duration - task.estimated_minutes)
            )

    weekly_signals: list[str] = []

    if underestimated_count:
        weekly_signals.append(
            f"You underestimated {underestimated_count} "
            f"task{'s' if underestimated_count != 1 else ''} this week."
        )

    if overrun_by_category:
        top_category = max(overrun_by_category, key=overrun_by_category.get)
        weekly_signals.append(
            f"{top_category} took longer than planned more than any other "
            f"category this week."
        )

    if completed_without_duration_count:
        weekly_signals.append(
            f"{completed_without_duration_count} completed "
            f"task{'s' if completed_without_duration_count != 1 else ''} "
            f"still need actual timing data."
        )

    if not weekly_signals and total_recent_entries:
        weekly_signals.append(
            "Your recent data looks consistent enough to start surfacing "
            "stronger patterns soon."
        )

    context = {
        "today_tasks": today_tasks,
        "next_up_tasks": next_up_tasks,
        "overdue_tasks": overdue_tasks,
        "upcoming_tasks": upcoming_tasks,
        "recent_activity_tasks": recent_activity_tasks,
        "overdue_count": overdue_count,
        "due_today_count": due_today_count,
        "missing_estimate_count": missing_estimate_count,
        "missing_actual_duration_count": missing_actual_duration_count,
        "uncategorized_count": uncategorized_count,
        "completed_this_week_count": completed_this_week_count,
        "planned_this_week_display": planned_this_week_display,
        "actual_this_week_display": actual_this_week_display,
        "largest_overrun_category_name": largest_overrun_category_name,
        "weekly_signals": weekly_signals,
        "insight_completion_percent": insight_completion_percent,
    }
    return render(request, "tracker/dashboard.html", context)


def add_task(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save()
            return redirect(task)
    else:
        form = TaskForm()

    return render(request, "tracker/add_task.html", {"form": form})


def task_detail(request, pk: int):
    task = get_object_or_404(Task.objects.select_related("category"), pk=pk)
    return render(request, "tracker/task_detail.html", {"task": task})


def edit_task(request, pk: int):
    task = get_object_or_404(Task, pk=pk)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            task = form.save()
            return redirect(task)
    else:
        form = TaskForm(instance=task)

    return render(request, "tracker/edit_task.html", {"form": form, "task": task})


@require_POST
def toggle_task_complete(request, pk: int):
    task = get_object_or_404(Task, pk=pk)
    task.completed = not task.completed
    task.save(update_fields=["completed"])
    return redirect(task)


def categories(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("categories")
    else:
        form = CategoryForm()

    categories_qs = Category.objects.annotate(task_count=Count("task")).order_by("name")
    uncategorized_count = Task.objects.filter(category__isnull=True).count()

    return render(
        request,
        "tracker/categories.html",
        {
            "form": form,
            "categories": categories_qs,
            "uncategorized_count": uncategorized_count,
        },
    )


def edit_category(request, pk: int):
    category = get_object_or_404(Category, pk=pk)

    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect("categories")
    else:
        form = CategoryForm(instance=category)

    return render(
        request,
        "tracker/edit_category.html",
        {"form": form, "category": category},
    )


def about(request):
    return render(request, "tracker/about.html")


def calendar_view(request):
    today = date.today()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    cal = calendar.Calendar(firstweekday=6)
    weeks = cal.monthdatescalendar(year, month)

    grid_start = weeks[0][0]
    grid_end = weeks[-1][-1]

    tasks = (
        Task.objects.filter(
            due_date__isnull=False,
            due_date__range=(grid_start, grid_end),
        )
        .select_related("category")
        .order_by("due_date", "completed", "title")
    )

    tasks_by_day: dict[date, list[Task]] = {}
    for task in tasks:
        tasks_by_day.setdefault(task.due_date, []).append(task)

    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1

    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year += 1

    context = {
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "weeks": weeks,
        "tasks_by_day": tasks_by_day,
        "today": today,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
    }
    return render(request, "tracker/calendar.html", context)


def import_tasks(request):
    if request.method == "POST":
        form = TaskImportForm(request.POST, request.FILES)
        if form.is_valid():
            file_obj = form.cleaned_data["file"]

            if not file_obj.name.lower().endswith(".csv"):
                form.add_error("file", "Please upload a .csv file.")
            else:
                decoded = file_obj.read().decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(decoded))

                required = {"title"}
                missing = required - set(reader.fieldnames or [])
                if missing:
                    form.add_error(
                        "file",
                        f"Missing required column(s): {', '.join(sorted(missing))}",
                    )
                else:
                    created = 0
                    skipped = 0
                    errors: list[str] = []

                    for idx, row in enumerate(reader, start=2):
                        title = (row.get("title") or "").strip()
                        if not title:
                            skipped += 1
                            errors.append(f"Row {idx}: title is required.")
                            continue

                        cat_name = (row.get("category") or "").strip()
                        category = None
                        if cat_name:
                            category, _ = Category.objects.get_or_create(name=cat_name)

                        try:
                            due_date = _parse_csv_date(row.get("due_date") or "")
                        except ValueError:
                            skipped += 1
                            errors.append(
                                f"Row {idx}: invalid due_date "
                                f"'{(row.get('due_date') or '').strip()}' "
                                f"(use YYYY-MM-DD)."
                            )
                            continue

                        try:
                            start_at = _parse_csv_datetime(row.get("start_at") or "")
                        except ValueError as exc:
                            skipped += 1
                            errors.append(f"Row {idx}: {exc}.")
                            continue

                        try:
                            end_at = _parse_csv_datetime(row.get("end_at") or "")
                        except ValueError as exc:
                            skipped += 1
                            errors.append(f"Row {idx}: {exc}.")
                            continue

                        if start_at and end_at and end_at < start_at:
                            skipped += 1
                            errors.append(
                                f"Row {idx}: end_at must be after start_at."
                            )
                            continue

                        try:
                            estimated_minutes = _parse_estimated_minutes(row)
                        except ValueError:
                            skipped += 1
                            errors.append(
                                f"Row {idx}: invalid estimate values "
                                f"(estimated_minutes, estimated_hours, "
                                f"estimated_minutes_part must be integers)."
                            )
                            continue

                        notes = (row.get("notes") or "").strip()
                        completed = _parse_bool(row.get("completed") or "")

                        Task.objects.create(
                            title=title,
                            category=category,
                            due_date=due_date,
                            start_at=start_at,
                            end_at=end_at,
                            estimated_minutes=estimated_minutes,
                            notes=notes,
                            completed=completed,
                        )
                        created += 1

                    messages.success(
                        request,
                        f"Imported {created} task(s). Skipped {skipped}.",
                    )
                    if errors:
                        messages.warning(
                            request,
                            "Some rows were skipped. Review errors on the import page.",
                        )

                    request.session["import_errors"] = errors[:50]
                    return redirect("import_tasks")
    else:
        form = TaskImportForm()

    errors = request.session.pop("import_errors", [])
    return render(
        request,
        "tracker/import_tasks.html",
        {"form": form, "errors": errors},
    )