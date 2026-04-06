from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('tasks/add/', views.add_task, name='add_task'),
    path('tasks/<int:pk>/', views.task_detail, name='task_detail'),
    path('categories/', views.categories, name='categories'),
    path('about/', views.about, name='about'),
]