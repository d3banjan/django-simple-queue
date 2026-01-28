# Task Model

The `Task` model represents a unit of work to be executed asynchronously by a worker process.

## API Reference

::: django_simple_queue.models.Task
    options:
      show_source: true
      members:
        - QUEUED
        - PROGRESS
        - COMPLETED
        - FAILED
        - CANCELLED
        - STATUS_CHOICES
        - as_dict
        - clean_task
        - clean_args

## Status Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `Task.QUEUED` | 0 | Task is waiting to be picked up |
| `Task.PROGRESS` | 1 | Task is currently executing |
| `Task.COMPLETED` | 2 | Task finished successfully |
| `Task.FAILED` | 3 | Task encountered an error |
| `Task.CANCELLED` | 4 | Task was manually cancelled |

## Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key (auto-generated) |
| `created` | DateTime | When the task was created |
| `modified` | DateTime | When the task was last updated |
| `task` | CharField | Dotted path to the callable |
| `args` | TextField | JSON-encoded keyword arguments |
| `status` | IntegerField | Current status (see constants above) |
| `output` | TextField | Return value from the task function |
| `worker_pid` | IntegerField | PID of the worker process |
| `error` | TextField | Error message and traceback |
| `log` | TextField | Captured stdout/stderr/logging |

## Usage Examples

### Query Tasks by Status

```python
from django_simple_queue.models import Task

# Get all pending tasks
pending = Task.objects.filter(status=Task.QUEUED)

# Get failed tasks from today
from django.utils import timezone
from datetime import timedelta

today = timezone.now().date()
failed_today = Task.objects.filter(
    status=Task.FAILED,
    created__date=today
)
```

### Check Task Result

```python
task = Task.objects.get(id=task_id)

if task.status == Task.COMPLETED:
    print(f"Result: {task.output}")
elif task.status == Task.FAILED:
    print(f"Error: {task.error}")
    print(f"Logs: {task.log}")
```

### Re-queue a Failed Task

```python
task = Task.objects.get(id=task_id)
task.status = Task.QUEUED
task.error = None
task.worker_pid = None
task.save()
```

### Get JSON Representation

```python
task = Task.objects.get(id=task_id)
data = task.as_dict
# {
#     "id": "...",
#     "created": "...",
#     "status": "Completed",
#     "output": "...",
#     ...
# }
```
