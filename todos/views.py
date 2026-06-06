from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Case, When, Value, IntegerField
from django.views.decorators.http import require_POST
from .models import Task, SubTask, Category
from .forms import TaskForm, TaskFilterForm, CategoryForm


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
            from django.db.models.functions import Coalesce
            from django.utils import timezone
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
