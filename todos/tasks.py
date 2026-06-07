from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from datetime import timedelta
from django.conf import settings
from .models import Task, Notification
from django.contrib.auth.models import User

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

@shared_task
def send_deadline_reminders():
    """
    Scans active tasks and sends alerts 24 hours and 1 hour before due_date.
    Concurrently creates an in-app Notification and sends an email.
    Recommended Celery Beat Interval: Every 15 minutes.
    """
    now = timezone.now()
    sent_count = 0
    
    # ── 1. 24-HOUR REMINDER WINDOW ──────────────────────────────────────────
    target_24h_start = now + timedelta(hours=23, minutes=45)
    target_24h_end = now + timedelta(hours=24, minutes=15)
    tasks_24h = Task.objects.filter(
        completed=False,
        due_date__range=(target_24h_start, target_24h_end)
    ).select_related('user')
    
    for task in tasks_24h:
        if not Notification.objects.filter(task=task, notification_type='reminder', message__contains="24 hours").exists():
            msg = f"Reminder: Your task '{task.title}' is due in 24 hours!"
            
            Notification.objects.create(user=task.user, task=task, notification_type='reminder', message=msg)
            
            if task.user.email:
                send_mail(
                    subject=f"⏳ Task Deadline Approaching: {task.title}",
                    message=f"Hello {task.user.username},\n\n'{task.title}' is due on {task.due_date.strftime('%B %d, %Y at %I:%M %p')}.\n\nLog in to TaskFlow to check it off!",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[task.user.email],
                    fail_silently=True,
                )
            sent_count += 1

    # ── 2. 1-HOUR REMINDER WINDOW ───────────────────────────────────────────
    target_1h_start = now + timedelta(minutes=45)
    target_1h_end = now + timedelta(hours=1, minutes=15)
    tasks_1h = Task.objects.filter(
        completed=False,
        due_date__range=(target_1h_start, target_1h_end)
    ).select_related('user')
    
    for task in tasks_1h:
        if not Notification.objects.filter(task=task, notification_type='reminder', message__contains="1 hour").exists():
            msg = f"Urgent: Your task '{task.title}' is due in 1 hour!"
            
            Notification.objects.create(user=task.user, task=task, notification_type='reminder', message=msg)
            
            if task.user.email:
                send_mail(
                    subject=f"🚨 Urgent Task Deadline: {task.title}",
                    message=f"Hello {task.user.username},\n\nThis is an urgent reminder that '{task.title}' is due in 1 hour!\n\nDon't miss your milestone!",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[task.user.email],
                    fail_silently=True,
                )
            sent_count += 1

    return f"Processed {sent_count} deadline reminders."

@shared_task
def generate_daily_overdue_digests():
    """
    Loops through users, aggregates all of their overdue tasks,
    creates an in-app check-in notification, and emails a digest.
    """
    now = timezone.now()
    users_notified = 0
    
    for user in User.objects.all():
        overdue_tasks = Task.objects.filter(user=user, completed=False, due_date__lt=now)
        
        if overdue_tasks.exists():
            task_list_str = "\n".join([f"- {t.title} (Due: {t.due_date.strftime('%Y-%m-%d %H:%M')})" for t in overdue_tasks])
            email_msg = f"Hello {user.username},\n\nYou have {overdue_tasks.count()} overdue tasks requiring your attention:\n\n{task_list_str}\n\nLog into TaskFlow to re-schedule or complete them."
            
            Notification.objects.create(
                user=user, 
                notification_type='overdue', 
                message=f"Morning check-in: You have {overdue_tasks.count()} overdue milestones."
            )
            
            if user.email:
                send_mail(
                    subject="⚠️ Daily Workspace Overdue Summary Digest",
                    message=email_msg,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            users_notified += 1
            
    return f"Dispatched daily overdue digests to {users_notified} users."
