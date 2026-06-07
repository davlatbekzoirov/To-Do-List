from django.contrib import admin
from .models import Task, SubTask, Category, FocusSession

class SubTaskInline(admin.TabularInline):
    model = SubTask
    extra = 1

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'category', 'priority', 'completed', 'due_date', 'created_at']
    list_filter = ['priority', 'completed', 'category', 'user']
    search_fields = ['title', 'description']
    inlines = [SubTaskInline]

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'color']
    list_filter = ['user']

@admin.register(SubTask)
class SubTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'task', 'completed', 'order']
    list_filter = ['completed']

@admin.register(FocusSession)
class FocusSessionAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'duration_minutes', 'started_at', 'is_completed')
    list_filter = ('is_completed', 'started_at')
    search_fields = ('task__title', 'user__username')
    readonly_fields = ('started_at',)

    def has_change_permission(self, request, obj=None):
        return False