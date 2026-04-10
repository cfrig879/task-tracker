import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from .models import Task, Category
from .forms import TaskForm
from .import_forms import TaskImportForm
from django.contrib import messages
from django.db.models import Count, Q
from django.views.decorators.http import require_POST
from .category_forms import CategoryForm
from datetime import date, datetime
import calendar


def categories(request):
    # Handle "Add Category" submission on the same page
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

    return render(request, "tracker/edit_category.html", {"form": form, "category": category})

def edit_task(request, pk: int):
    task = get_object_or_404(Task, pk=pk)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            task = form.save()
            return redirect(task)  # uses get_absolute_url()
    else:
        form = TaskForm(instance=task)

    return render(request, "tracker/edit_task.html", {"form": form, "task": task})

@require_POST
def toggle_task_complete(request, pk: int):
    task = get_object_or_404(Task, pk=pk)
    task.completed = not task.completed
    task.save(update_fields=["completed"])
    return redirect(task)

def dashboard(request):
    tasks = (
        Task.objects
        .select_related("category")
        .order_by("completed", "due_date", "title")
    )
    categories = Category.objects.order_by("name")
    return render(request, "tracker/dashboard.html", {"tasks": tasks, "categories": categories})


def add_task(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save()
            return redirect(task)  # uses task.get_absolute_url()
    else:
        form = TaskForm()

    return render(request, "tracker/add_task.html", {"form": form})


def task_detail(request, pk: int):
    task = get_object_or_404(Task.objects.select_related("category"), pk=pk)
    return render(request, "tracker/task_detail.html", {"task": task})

def about(request):
    return render(request, "tracker/about.html")

def calendar_view(request):
    # month navigation via query params: ?year=2026&month=4
    today = date.today()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    cal = calendar.Calendar(firstweekday=6)  # start weeks on Sunday
    weeks = cal.monthdatescalendar(year, month)

    # Pull tasks for all days shown in the grid (includes spillover days)
    grid_start = weeks[0][0]
    grid_end = weeks[-1][-1]

    tasks = (
        Task.objects
        .filter(due_date__isnull=False, due_date__range=(grid_start, grid_end))
        .select_related("category")
        .order_by("due_date", "completed", "title")
    )

    # Group tasks by due_date
    tasks_by_day = {}
    for t in tasks:
        tasks_by_day.setdefault(t.due_date, []).append(t)

    # Prev/next month links
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

def _parse_bool(value: str) -> bool:
    v = (value or "").strip().lower()
    return v in {"1", "true", "yes", "y", "t"}

def import_tasks(request):
    if request.method == "POST":
        form = TaskImportForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data["file"]
            if not f.name.lower().endswith(".csv"):
                form.add_error("file", "Please upload a .csv file.")
            else:
                decoded = f.read().decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(decoded))

                required = {"title"}
                missing = required - set((reader.fieldnames or []))
                if missing:
                    form.add_error("file", f"Missing required column(s): {', '.join(sorted(missing))}")
                else:
                    created = 0
                    skipped = 0
                    errors = []

                    for idx, row in enumerate(reader, start=2):  # start=2 for header row
                        title = (row.get("title") or "").strip()
                        if not title:
                            skipped += 1
                            errors.append(f"Row {idx}: title is required.")
                            continue

                        # Category by name (create if needed)
                        cat_name = (row.get("category") or "").strip()
                        category = None
                        if cat_name:
                            category, _ = Category.objects.get_or_create(name=cat_name)

                        # Due date (YYYY-MM-DD)
                        due_date = None
                        due_raw = (row.get("due_date") or "").strip()
                        if due_raw:
                            try:
                                due_date = datetime.strptime(due_raw, "%Y-%m-%d").date()
                            except ValueError:
                                skipped += 1
                                errors.append(f"Row {idx}: invalid due_date '{due_raw}' (use YYYY-MM-DD).")
                                continue

                        notes = (row.get("notes") or "").strip()
                        completed = _parse_bool(row.get("completed") or "")

                        Task.objects.create(
                            title=title,
                            category=category,
                            due_date=due_date,
                            notes=notes,
                            completed=completed,
                        )
                        created += 1

                    messages.success(request, f"Imported {created} task(s). Skipped {skipped}.")
                    if errors:
                        # Keep it short; you can also display a list on the page
                        messages.warning(request, "Some rows were skipped. Review errors on the import page.")
                    request.session["import_errors"] = errors[:50]  # store first 50
                    return redirect("import_tasks")
    else:
        form = TaskImportForm()

    errors = request.session.pop("import_errors", [])
    return render(request, "tracker/import_tasks.html", {"form": form, "errors": errors})