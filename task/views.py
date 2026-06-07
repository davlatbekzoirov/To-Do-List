import datetime
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.dateparse import parse_datetime
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Case, When, Value, IntegerField, Count
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models.functions import Coalesce
from .models import Task, SubTask, Category, FocusSession
from notification.models import Notification  
from .forms import TaskForm, TaskFilterForm, CategoryForm
from core.utils import get_client_ip_hash
from account.models import AuditLog
from django.db import models

PRIORITY_ORDER = Case(
    When(priority='urgent', then=Value(0)),
    When(priority='high',   then=Value(1)),
    When(priority='medium', then=Value(2)),
    When(priority='low',    then=Value(3)),
    output_field=IntegerField(),
)

@login_required
def task_list(request):
    tasks = Task.objects.filter(user=request.user).select_related('category').prefetch_related('subtasks')
    filter_form = TaskFilterForm(request.GET, user=request.user)

    if filter_form.is_valid():
        status   = filter_form.cleaned_data.get('status')
        priority = filter_form.cleaned_data.get('priority')
        search   = filter_form.cleaned_data.get('search')
        category = filter_form.cleaned_data.get('category')
        sort     = filter_form.cleaned_data.get('sort')

        if status == 'active':
            tasks = tasks.filter(completed=False)
        elif status == 'completed':
            tasks = tasks.filter(completed=True)
        if priority:
            tasks = tasks.filter(priority=priority)
        if search:
            tasks = tasks.filter(Q(title__icontains=search) | Q(description__icontains=search))
        if category:
            tasks = tasks.filter(category=category)

        # Sorting
        if sort == 'due_date':
            far_future = timezone.now() + datetime.timedelta(days=36500)
            tasks = tasks.annotate(
                due_sort=Coalesce('due_date', Value(far_future))
            ).order_by('due_sort')
        elif sort == 'priority':
            tasks = tasks.annotate(pri_order=PRIORITY_ORDER).order_by('pri_order')
        elif sort == 'created_at':
            tasks = tasks.order_by('created_at')
        elif sort == '-created_at':
            tasks = tasks.order_by('-created_at')

    stats = {
        'total':     Task.objects.filter(user=request.user).count(),
        'completed': Task.objects.filter(user=request.user, completed=True).count(),
        'active':    Task.objects.filter(user=request.user, completed=False).count(),
        'urgent':    Task.objects.filter(user=request.user, priority='urgent', completed=False).count(),
    }

    return render(request, 'task/task_list.html', {
        'tasks': tasks,
        'filter_form': filter_form,
        'stats': stats,
    })

def _save_subtasks(task, subtask_titles_raw):
    new_titles = [t.strip() for t in (subtask_titles_raw or '').split('\n') if t.strip()]
    existing = list(task.subtasks.order_by('order', 'created_at'))
    for i, title in enumerate(new_titles):
        if i < len(existing):
            if existing[i].title != title:
                existing[i].title = title
                existing[i].save(update_fields=['title'])
            existing[i].order = i
            existing[i].save(update_fields=['order'])
        else:
            SubTask.objects.create(task=task, title=title, order=i)
    if len(new_titles) < len(existing):
        for leftover in existing[len(new_titles):]:
            leftover.delete()


@login_required
def task_create(request):
    if request.method == 'POST':
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            _save_subtasks(task, form.cleaned_data.get('subtask_titles', ''))
            messages.success(request, 'Task created!')
            return redirect('task_list')
    else:
        form = TaskForm(user=request.user)
    return render(request, 'task/task_form.html', {'form': form, 'action': 'Create'})


@login_required
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            form.save()
            _save_subtasks(task, form.cleaned_data.get('subtask_titles', ''))
            messages.success(request, 'Task updated!')
            return redirect('task_list')
    else:
        form = TaskForm(instance=task, user=request.user)
    return render(request, 'task/task_form.html', {'form': form, 'action': 'Edit', 'task': task})


@login_required
@require_POST
def task_toggle(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.completed = not task.completed
    task.save()

    spawned = None
    if task.completed and task.recurrence:
        new_task = task.spawn_next_recurrence()
        if new_task:
            msg = f"Recurring schedule spawned a new task instance: '{new_task.title}'"
            Notification.objects.create(
                user=request.user,
                task=new_task,
                notification_type='recurrence',
                message=msg
            )
            
            spawned = {
                'id': new_task.pk,
                'title': new_task.title,
                'due_date': new_task.due_date.isoformat() if new_task.due_date else None,
                'recurrence': new_task.recurrence,
            }

    return JsonResponse({
        'ok': True,
        'completed': task.completed,
        'task_id': task.pk,
        'spawned': spawned,
    })


@login_required
@require_POST
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.delete() 
    return JsonResponse({'ok': True, 'task_id': pk})


@login_required
@require_POST
def subtask_toggle(request, pk):
    subtask = get_object_or_404(SubTask, pk=pk, task__user=request.user)
    subtask.completed = not subtask.completed
    subtask.save()
    task = subtask.task
    return JsonResponse({
        'completed': subtask.completed,
        'progress': task.subtask_progress,
        'completed_count': task.completed_subtasks_count,
        'total_count': task.total_subtasks_count,
    })


@login_required
def category_list(request):
    categories = Category.objects.filter(user=request.user)
    form = CategoryForm()
    return render(request, 'task/category_list.html', {'categories': categories, 'form': form})


@login_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.user = request.user
            cat.save()
            messages.success(request, f'Category "{cat.name}" created!')
    return redirect('category_list')


@login_required
def category_delete(request, pk):
    cat = get_object_or_404(Category, pk=pk, user=request.user)
    if request.method == 'POST':
        cat.delete()
        messages.success(request, f'Category "{cat.name}" deleted.')
    return redirect('category_list')


@login_required
def analytics_view(request):
    categories_data = Category.objects.filter(user=request.user).annotate(
        task_count=Count('tasks')
    ).values('name', 'color', 'task_count')
    
    cat_labels = [c['name'] for c in categories_data]
    cat_colors = [c['color'] for c in categories_data]
    cat_counts = [c['task_count'] for c in categories_data]
    
    uncategorized_count = Task.objects.filter(user=request.user, category__isnull=True).count()
    if uncategorized_count > 0:
        cat_labels.append("Uncategorized")
        cat_colors.append("#6b7280")
        cat_counts.append(uncategorized_count)

    today = timezone.now().date()
    days_list = [today - datetime.timedelta(days=i) for i in range(6, -1, -1)]
    
    completion_counts = []
    completion_labels = []
    
    for day in days_list:
        count = Task.objects.filter(
            user=request.user,
            completed=True,
            updated_at__date=day
        ).count()
        completion_counts.append(count)
        completion_labels.append(day.strftime('%b %d'))

    categories = Category.objects.filter(user=request.user)
    focus_labels = []
    estimated_times = []
    actual_times = []

    for cat in categories:
        focus_labels.append(cat.name)
        cat_tasks = Task.objects.filter(user=request.user, category=cat)
        total_est = sum(t.estimated_minutes for t in cat_tasks)
        estimated_times.append(total_est)
        
        total_act = FocusSession.objects.filter(
            user=request.user, 
            task__category=cat, 
            is_completed=True
        ).aggregate(models.Sum('duration_minutes'))['duration_minutes__sum'] or 0
        actual_times.append(total_act)

    uncat_tasks = Task.objects.filter(user=request.user, category__isnull=True)
    total_uncat_est = sum(t.estimated_minutes for t in uncat_tasks)
    total_uncat_act = FocusSession.objects.filter(
        user=request.user,
        task__category__isnull=True,
        is_completed=True
    ).aggregate(models.Sum('duration_minutes'))['duration_minutes__sum'] or 0

    if total_uncat_est > 0 or total_uncat_act > 0:
        focus_labels.append("Uncategorized")
        estimated_times.append(total_uncat_est)
        actual_times.append(total_uncat_act)

    context = {
        'cat_labels': cat_labels,
        'cat_colors': cat_colors,
        'cat_counts': cat_counts,
        'completion_labels': completion_labels,
        'completion_counts': completion_counts,
        'focus_labels': focus_labels,
        'estimated_times': estimated_times,
        'actual_times': actual_times,
    }
    return render(request, 'task/analytics.html', context)

@login_required
def export_data_json(request):
    backup_payload = []
    user_tasks = Task.objects.filter(user=request.user).select_related('category').prefetch_related('subtasks')
    
    for task in user_tasks:
        task_dump = {
            'title': task.title,
            'description': task.description,
            'completed': task.completed,
            'priority': task.priority,
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'recurrence': task.recurrence,
            'category': {
                'name': task.category.name,
                'color': task.category.color
            } if task.category else None,
            'subtasks': [
                {'title': st.title, 'completed': st.completed, 'order': st.order} 
                for st in task.subtasks.all()
            ]
        }
        backup_payload.append(task_dump)
        
    response = HttpResponse(json.dumps(backup_payload, indent=4), content_type='application/json')
    filename = f"taskflow_backup_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    AuditLog.objects.create(
        user=request.user,
        action='data_export',
        ip_hash=get_client_ip_hash(request),
        details=f"Exported {user_tasks.count()} tasks safely."
    )
    return response


@login_required
@require_POST
def import_data_json(request):
    json_file = request.FILES.get('backup_file')
    if not json_file:
        messages.error(request, 'No blueprint backup file found.')
        return redirect('task_list')
        
    try:
        data_records = json.loads(json_file.read().decode('utf-8'))
        import_count = 0
        
        for item in data_records:
            category_obj = None
            if item.get('category'):
                cat_info = item['category']
                category_obj, _ = Category.objects.get_or_create(
                    user=request.user,
                    name=cat_info['name'],
                    defaults={'color': cat_info.get('color', '#6366f1')}
                )
            
            due_val = item.get('due_date')
            parsed_due = parse_datetime(due_val) if due_val else None
            
            task = Task.objects.create(
                user=request.user,
                category=category_obj,
                title=item.get('title', 'Imported Task'),
                description=item.get('description', ''),
                completed=item.get('completed', False),
                priority=item.get('priority', 'medium'),
                due_date=parsed_due,
                recurrence=item.get('recurrence', '')
            )
            
            for st_info in item.get('subtasks', []):
                SubTask.objects.create(
                    task=task,
                    title=st_info.get('title', ''),
                    completed=st_info.get('completed', False),
                    order=st_info.get('order', 0)
                )
            import_count += 1
            
        messages.success(request, f'Successfully structuralized and imported {import_count} tasks!')
    except Exception as e:
        messages.error(request, f'Structural failure reading data architecture file: {str(e)}')
        
    return redirect('task_list')

@login_required
@require_POST
def record_focus_session(request, pk):
    """Endpoint called via AJAX when a Pomodoro clock finishes counting down."""
    task = get_object_or_404(Task, pk=pk, user=request.user)
    
    try:
        data = json.loads(request.body)
        duration = int(data.get('duration_minutes', 25))
    except (ValueError, TypeError, json.JSONDecodeError):
        duration = 25

    FocusSession.objects.create(
        user=request.user,
        task=task,
        duration_minutes=duration,
        is_completed=True
    )
    
    return JsonResponse({
        'ok': True, 
        'total_task_minutes': task.total_time_spent
    })
