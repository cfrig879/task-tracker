from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="tracker/login.html"),
        name="login",
    ),
    path("signup/", views.signup, name="signup"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("demo/", views.dashboard, name="dashboard"),

    path("tasks/add/", views.add_task, name="add_task"),
    path("tasks/<int:pk>/", views.task_detail, name="task_detail"),
    path("tasks/<int:pk>/edit/", views.edit_task, name="edit_task"),
    path("tasks/<int:pk>/toggle/", views.toggle_task_complete, name="toggle_task_complete"),
    path("tasks/", views.task_list, name="task_list"),

    path("tasks/import/", views.import_tasks, name="import_tasks"),
    path("tasks/import/template/", views.download_import_template, name="download_import_template"),

    path("categories/", views.categories, name="categories"),
    path("categories/<int:pk>/edit/", views.edit_category, name="edit_category"),
    path("categories/<int:pk>/delete/", views.delete_category, name="delete_category"),

    path("calendar/", views.calendar_view, name="calendar"),
    path("about/", views.about, name="about"),
]