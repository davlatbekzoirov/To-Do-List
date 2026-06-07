from django.urls import path
from . import views

urlpatterns = [
    # Tasks
    path('', views.task_list, name='task_list'),
    path('task/new/', views.task_create, name='task_create'),
    path('task/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('task/<int:pk>/toggle/', views.task_toggle, name='task_toggle'),   # AJAX POST
    path('task/<int:pk>/delete/', views.task_delete, name='task_delete'),   # AJAX POST

    # Subtasks
    path('subtask/<int:pk>/toggle/', views.subtask_toggle, name='subtask_toggle'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Analysis
    path('analytics/', views.analytics_view, name='analytics'),

    path('data/export/', views.export_data_json, name='export_data'),
    path('data/import/', views.import_data_json, name='import_data'),

    # Notifications API backend
    path('api/notifications/', views.fetch_notifications, name='fetch_notifications'),
    path('api/notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
]
