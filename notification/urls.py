from django.urls import path
from . import views

urlpatterns = [
    # Notifications API backend
    path('api/notifications/', views.fetch_notifications, name='fetch_notifications'),
    path('api/notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
]