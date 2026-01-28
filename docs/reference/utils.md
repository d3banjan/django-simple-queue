# Utilities

Utility functions for creating and managing tasks.

## API Reference

::: django_simple_queue.utils
    options:
      show_source: true
      members:
        - create_task
        - TaskNotAllowedError

## create_task

The primary way to enqueue tasks for background execution.

### Signature

```python
def create_task(task: str, args: dict) -> UUID:
    ...
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `task` | str | Dotted path to the callable (e.g., "myapp.tasks.send_email") |
| `args` | dict | Keyword arguments to pass to the callable |

### Returns

- `UUID`: The unique identifier of the created task

### Raises

- `TypeError`: If `args` is not a dictionary
- `TaskNotAllowedError`: If task is not in `DJANGO_SIMPLE_QUEUE_ALLOWED_TASKS`

### Examples

```python
from django_simple_queue.utils import create_task

# Basic usage
task_id = create_task(
    task="myapp.tasks.send_email",
    args={"to": "user@example.com", "subject": "Hello"}
)

# With complex arguments
task_id = create_task(
    task="myapp.tasks.process_order",
    args={
        "order_id": 12345,
        "options": {
            "notify": True,
            "priority": "high"
        }
    }
)

# Check the created task
from django_simple_queue.models import Task
task = Task.objects.get(id=task_id)
print(task.status)  # 0 (QUEUED)
```

## TaskNotAllowedError

Exception raised when attempting to create a task that is not in the allowlist.

### Example

```python
from django_simple_queue.utils import create_task, TaskNotAllowedError

try:
    task_id = create_task(
        task="some.unknown.function",
        args={}
    )
except TaskNotAllowedError as e:
    print(f"Task not allowed: {e}")
```

## Best Practices

### Pass IDs, Not Objects

```python
# Good
create_task(
    task="myapp.tasks.process_user",
    args={"user_id": user.id}
)

# Bad - can't serialize model instances
create_task(
    task="myapp.tasks.process_user",
    args={"user": user}  # TypeError!
)
```

### Use JSON-Serializable Arguments

```python
# Good
create_task(
    task="myapp.tasks.schedule",
    args={"date": "2024-01-15T10:00:00"}
)

# Bad - datetime not JSON-serializable by default
create_task(
    task="myapp.tasks.schedule",
    args={"date": datetime.now()}  # Error!
)
```
