from django.urls import path
from . import views

urlpatterns = [
    path('', views.task_list, name='task_list'),
    path('create/', views.task_create, name='task_create'),
    path('<int:pk>/edit/', views.task_edit, name='task_edit'),
    
    path('<int:pk>/toggle/', views.task_toggle, name='task_toggle'),
    path('<int:pk>/delete/', views.task_delete, name='task_delete'),
    path('subtask/<int:pk>/toggle/', views.subtask_toggle, name='subtask_toggle'),
    
    path('<int:pk>/record-focus/', views.record_focus_session, name='record_focus_session'),
    
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    
    path('analytics/', views.analytics_view, name='analytics'),
    path('export/json/', views.export_data_json, name='export_data'),
    path('import/json/', views.import_data_json, name='import_data'),
]