from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.db.models import Q, Count
from .models import Task
from .forms import TaskForm, TaskFilterForm


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


@login_required
def task_list(request):
    tasks = Task.objects.filter(user=request.user)
    filter_form = TaskFilterForm(request.GET)

    if filter_form.is_valid():
        status = filter_form.cleaned_data.get('status')
        priority = filter_form.cleaned_data.get('priority')
        search = filter_form.cleaned_data.get('search')

        if status == 'active':
            tasks = tasks.filter(completed=False)
        elif status == 'completed':
            tasks = tasks.filter(completed=True)
        if priority:
            tasks = tasks.filter(priority=priority)
        if search:
            tasks = tasks.filter(Q(title__icontains=search) | Q(description__icontains=search))

    stats = {
        'total': Task.objects.filter(user=request.user).count(),
        'completed': Task.objects.filter(user=request.user, completed=True).count(),
        'active': Task.objects.filter(user=request.user, completed=False).count(),
        'urgent': Task.objects.filter(user=request.user, priority='urgent', completed=False).count(),
    }

    return render(request, 'todos/task_list.html', {
        'tasks': tasks,
        'filter_form': filter_form,
        'stats': stats,
    })


@login_required
def task_create(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            messages.success(request, 'Task created!')
            return redirect('task_list')
    else:
        form = TaskForm()
    return render(request, 'todos/task_form.html', {'form': form, 'action': 'Create'})


@login_required
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task updated!')
            return redirect('task_list')
    else:
        form = TaskForm(instance=task)
    return render(request, 'todos/task_form.html', {'form': form, 'action': 'Edit', 'task': task})


@login_required
def task_toggle(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.completed = not task.completed
    task.save()
    return redirect('task_list')


@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == 'POST':
        task.delete()
        messages.success(request, 'Task deleted.')
        return redirect('task_list')
    return render(request, 'todos/task_confirm_delete.html', {'task': task})