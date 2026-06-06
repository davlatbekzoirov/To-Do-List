import datetime
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Case, When, Value, IntegerField
from django.views.decorators.http import require_POST
from .models import Task, SubTask, Category
from .forms import TaskForm, TaskFilterForm, CategoryForm
from django.db.models import Count
from django.utils import timezone
from django.db.models.functions import Coalesce

# ─── Auth ────────────────────────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('task_list')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.username}! Your account has been created.')
            return redirect('task_list')
    else:
        form = UserCreationForm()
    return render(request, 'todos/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('task_list')
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('task_list')
    else:
        form = AuthenticationForm()
    return render(request, 'todos/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


# ─── Priority sort helper ─────────────────────────────────────────────────────

PRIORITY_ORDER = Case(
    When(priority='urgent', then=Value(0)),
    When(priority='high',   then=Value(1)),
    When(priority='medium', then=Value(2)),
    When(priority='low',    then=Value(3)),
    output_field=IntegerField(),
)


# ─── Task List ────────────────────────────────────────────────────────────────

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
            import datetime
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

    return render(request, 'todos/task_list.html', {
        'tasks': tasks,
        'filter_form': filter_form,
        'stats': stats,
    })


# ─── Task CRUD ────────────────────────────────────────────────────────────────

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
    return render(request, 'todos/task_form.html', {'form': form, 'action': 'Create'})


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
    return render(request, 'todos/task_form.html', {'form': form, 'action': 'Edit', 'task': task})


# ─── AJAX: Task Toggle ────────────────────────────────────────────────────────

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


# ─── AJAX: Task Delete ────────────────────────────────────────────────────────

@login_required
@require_POST
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.delete()
    return JsonResponse({'ok': True, 'task_id': pk})


# ─── AJAX: Subtask Toggle ─────────────────────────────────────────────────────

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


# ─── Category CRUD ────────────────────────────────────────────────────────────

@login_required
def category_list(request):
    categories = Category.objects.filter(user=request.user)
    form = CategoryForm()
    return render(request, 'todos/category_list.html', {'categories': categories, 'form': form})


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
    # 1. Category Breakdown Data
    categories_data = Category.objects.filter(user=request.user).annotate(
        task_count=Count('tasks')
    ).values('name', 'color', 'task_count')
    
    cat_labels = [c['name'] for c in categories_data]
    cat_colors = [c['color'] for c in categories_data]
    cat_counts = [c['task_count'] for c in categories_data]
    
    # Handle Uncategorized tasks
    uncategorized_count = Task.objects.filter(user=request.user, category__isnull=True).count()
    if uncategorized_count > 0:
        cat_labels.append("Uncategorized")
        cat_colors.append("#6b7280")
        cat_counts.append(uncategorized_count)

    # 2. Historical Completion Tracking (Last 7 Days)
    today = timezone.now().date()
    days_list = [today - datetime.timedelta(days=i) for i in range(6, -1, -1)]
    
    completion_counts = []
    completion_labels = []
    
    for day in days_list:
        count = Task.objects.filter(
            user=request.user,
            completed=True,
            updated_at__date=day # Assuming updated_at reflects the completion date accurately
        ).count()
        completion_counts.append(count)
        completion_labels.append(day.strftime('%b %d'))

    context = {
        'cat_labels': cat_labels,
        'cat_colors': cat_colors,
        'cat_counts': cat_counts,
        'completion_labels': completion_labels,
        'completion_counts': completion_counts,
    }
    return render(request, 'todos/analytics.html', context)



@login_required
def export_data_json(request):
    """Exports user Categories, Tasks, and Subtasks securely as an identical JSON blueprint."""
    backup_payload = []
    
    # Fetch all tasks belonging to the user
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
        
    response = HttpResponse(
        json.dumps(backup_payload, indent=4), 
        content_type='application/json'
    )
    filename = f"taskflow_backup_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_POST
def import_data_json(request):
    """Parses JSON file upload backups to reconstitute matching object relations safely."""
    json_file = request.FILES.get('backup_file')
    if not json_file:
        messages.error(request, 'No blueprint backup file found.')
        return redirect('task_list')
        
    try:
        data_records = json.loads(json_file.read().decode('utf-8'))
        import_count = 0
        
        for item in data_records:
            # 1. Deduplicate or dynamically resolve category definitions
            category_obj = None
            if item.get('category'):
                cat_info = item['category']
                category_obj, _ = Category.objects.get_or_create(
                    user=request.user,
                    name=cat_info['name'],
                    defaults={'color': cat_info.get('color', '#6366f1')}
                )
            
            # 2. Re-create base task object
            due_val = item.get('due_date')
            parsed_due = timezone.datetime.fromisoformat(due_val) if due_val else None
            
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
            
            # 3. Re-link subtasks
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