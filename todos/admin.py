from django.contrib import admin
from .models import Task, SubTask, Category


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
