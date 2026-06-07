from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp', 'ip_hash')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username', 'details')
    readonly_fields = ('user', 'action', 'ip_hash', 'timestamp', 'details') 

    def has_add_permission(self, request):
        return False  

    def has_change_permission(self, request, obj=None):
        return False 