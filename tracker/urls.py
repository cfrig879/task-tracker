from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('tasks/add/', views.add_task, name='add_task'),
    path('tasks/<int:pk>/', views.task_detail, name='task_detail'),
    path('categories/', views.categories, name='categories'),
    path('about/', views.about, name='about'),
    path("tasks/<int:pk>/toggle/", views.toggle_task_complete, name="toggle_task_complete"),
    path("tasks/<int:pk>/edit/", views.edit_task, name="edit_task"),
    path("categories/<int:pk>/edit/", views.edit_category, name="edit_category"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("tasks/import/", views.import_tasks, name="import_tasks"),
]
