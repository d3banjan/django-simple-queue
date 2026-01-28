# Installation

## Requirements

- Python 3.8+
- Django 3.2+

## Install the Package

```bash
pip install django-simple-queue
```

## Configure Django

### 1. Add to INSTALLED_APPS

Add `django_simple_queue` to your `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    # Django apps...
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps...
    'django_simple_queue',

    # Your apps...
    'myapp',
]
```

### 2. Add URL Configuration

Include the task status URL in your `urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ...
    path('django_simple_queue/', include('django_simple_queue.urls')),
]
```

### 3. Run Migrations

Apply the database migrations to create the Task table:

```bash
python manage.py migrate django_simple_queue
```

## Start the Worker

Run the worker command to start processing tasks:

```bash
python manage.py task_worker
```

!!! tip "Running in Production"
    In production, use a process manager like systemd, supervisor, or Docker to keep the worker running. You can run multiple workers for parallel processing.

## Verify Installation

1. Create a simple task function:

    ```python
    # myapp/tasks.py
    def hello_world(name):
        return f"Hello, {name}!"
    ```

2. Enqueue a task from Django shell:

    ```python
    from django_simple_queue.utils import create_task

    task_id = create_task(
        task="myapp.tasks.hello_world",
        args={"name": "World"}
    )
    print(f"Created task: {task_id}")
    ```

3. Check the task status at `/django_simple_queue/task?task_id=<task_id>` or in the Django admin.

## Next Steps

- [Configure settings](configuration.md) for task timeouts, allowed tasks, etc.
- Learn how to [create tasks](../guides/creating-tasks.md) in your application
- Understand the [task lifecycle](../guides/lifecycle.md)
