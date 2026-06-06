from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from datetime import timedelta
from django.contrib.auth.models import User
from .models import Task

@shared_task
def send_upcoming_task_reminders():
    now = timezone.now()
    target_start = now + timedelta(hours=23)
    target_end = now + timedelta(hours=24)
    
    upcoming_tasks = Task.objects.filter(
        completed=False,
        due_date__range=(target_start, target_end)
    ).select_related('user')
    
    sent_notifications_count = 0
    
    for task in upcoming_tasks:
        user = task.user
        if user.email:
            subject = f"⏳ Reminder: Task '{task.title}' is due in 24 hours!"
            message = f"Hello {user.username},\n\nThis is a notification that your task '{task.title}' is scheduled to be due on {task.due_date.strftime('%B %d, %Y at %I:%M %p')}.\n\nLog in to TaskFlow to check off your items or adjust priorities.\n\nBest,\nTaskFlow Fleet Admin"
            
            send_mail(
                subject=subject,
                message=message,
                from_email=None,
                recipient_list=[user.email],
                fail_silently=True
            )
            sent_notifications_count += 1
            
    return f"Dispatched {sent_notifications_count} reminder emails out."