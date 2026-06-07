from django.db import models
from django.contrib.auth.models import User

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('account_change', 'Account Setting Changed'),
        ('data_export', 'Data Exported'),
        ('bulk_deletion', 'Bulk Task Deletion'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    ip_hash = models.CharField(max_length=64)  # Stores SHA-256 hash of the IP address
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} | {self.action} | {self.timestamp}"