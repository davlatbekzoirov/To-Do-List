from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import calendar

class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default='#6366f1')  # hex color

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']
        unique_together = ['user', 'name']

    def __str__(self):
        return self.name


class Task(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    RECURRENCE_CHOICES = [
        ('', 'No recurrence'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tasks'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    due_date = models.DateTimeField(null=True, blank=True)
    recurrence = models.CharField(max_length=10, choices=RECURRENCE_CHOICES, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def is_overdue(self):
        if self.due_date and not self.completed:
            return self.due_date < timezone.now()
        return False

    def spawn_next_recurrence(self):
        """Create the next occurrence when a recurring task is completed."""

        if not self.recurrence or not self.due_date:
            return None

        base = self.due_date
        if self.recurrence == 'daily':
            next_due = base + timedelta(days=1)
        elif self.recurrence == 'weekly':
            next_due = base + timedelta(weeks=1)
        elif self.recurrence == 'monthly':
            # Same day next month, clamped to last day if needed
            month = base.month % 12 + 1
            year = base.year + (1 if base.month == 12 else 0)
            day = min(base.day, calendar.monthrange(year, month)[1])
            next_due = base.replace(year=year, month=month, day=day)
        else:
            return None

        # Only create if no identical future task already exists
        exists = Task.objects.filter(
            user=self.user, title=self.title,
            due_date=next_due, completed=False
        ).exists()
        if exists:
            return None

        new_task = Task.objects.create(
            user=self.user,
            category=self.category,
            title=self.title,
            description=self.description,
            priority=self.priority,
            due_date=next_due,
            recurrence=self.recurrence,
        )
        # Clone subtasks
        for st in self.subtasks.order_by('order'):
            SubTask.objects.create(task=new_task, title=st.title, order=st.order)
        return new_task

    @property
    def completed_subtasks_count(self):
        return self.subtasks.filter(completed=True).count()

    @property
    def total_subtasks_count(self):
        return self.subtasks.count()

    @property
    def subtask_progress(self):
        total = self.total_subtasks_count
        if total == 0:
            return 0
        return int((self.completed_subtasks_count / total) * 100)


class SubTask(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='subtasks')
    title = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.task.title} → {self.title}"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('reminder', 'Reminder'),
        ('overdue', 'Overdue Alert'),
        ('recurrence', 'Task Auto-Generated'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} | {self.notification_type} | {self.message[:30]}"