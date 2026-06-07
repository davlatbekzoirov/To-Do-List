from django import forms
from .models import Task, SubTask, Category

class CategoryForm(forms.ModelForm):
    COLOR_PRESETS = [
        ('#6366f1', 'Indigo'),
        ('#ec4899', 'Pink'),
        ('#f59e0b', 'Amber'),
        ('#10b981', 'Emerald'),
        ('#3b82f6', 'Blue'),
        ('#ef4444', 'Red'),
        ('#8b5cf6', 'Violet'),
        ('#14b8a6', 'Teal'),
        ('#f97316', 'Orange'),
        ('#6b7280', 'Gray'),
    ]

    class Meta:
        model = Category
        fields = ['name', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Work, Personal, Shopping…'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control form-control-color',
                'type': 'color',
            }),
        }


class TaskForm(forms.ModelForm):
    subtask_titles = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    class Meta:
        model = Task
        fields = ['title', 'description', 'priority', 'category', 'due_date', 'recurrence']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'What needs to be done?'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add details (optional)'
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }, format='%Y-%m-%dT%H:%M'),
            'recurrence': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = (
            Category.objects.filter(user=user) if user else Category.objects.none()
        )
        self.fields['category'].empty_label = '— No Category —'
        self.fields['due_date'].input_formats = ['%Y-%m-%dT%H:%M']

        # Prepopulate the hidden field when editing
        if self.instance and self.instance.pk:
            titles = '\n'.join(
                s.title for s in self.instance.subtasks.order_by('order', 'created_at')
            )
            self.fields['subtask_titles'].initial = titles


class SubTaskForm(forms.ModelForm):
    class Meta:
        model = SubTask
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Subtask title…'
            })
        }


class TaskFilterForm(forms.Form):
    STATUS_CHOICES = [
        ('', 'All Tasks'),
        ('active', 'Active'),
        ('completed', 'Completed'),
    ]
    # Keep using Task.PRIORITY_CHOICES cleanly since we are inside the task app
    PRIORITY_CHOICES = [('', 'All Priorities')] + Task.PRIORITY_CHOICES
    SORT_CHOICES = [
        ('', 'Sort: Default'),
        ('due_date', 'Due Date ↑'),
        ('priority', 'Priority ↓'),
        ('created_at', 'Oldest First'),
        ('-created_at', 'Newest First'),
    ]

    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False,
                               widget=forms.Select(attrs={'class': 'form-select'}))
    priority = forms.ChoiceField(choices=PRIORITY_CHOICES, required=False,
                                 widget=forms.Select(attrs={'class': 'form-select'}))
    category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=False,
        empty_label='All Categories',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    sort = forms.ChoiceField(choices=SORT_CHOICES, required=False,
                             widget=forms.Select(attrs={'class': 'form-select'}))
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Search tasks…'
    }))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'].queryset = Category.objects.filter(user=user)