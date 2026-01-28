# Configuration

Configuration functions for reading Django Simple Queue settings.

## API Reference

::: django_simple_queue.conf
    options:
      show_source: true

## Settings Overview

All settings are read from Django's `settings.py` with the `DJANGO_SIMPLE_QUEUE_` prefix.

| Setting | Default | Description |
|---------|---------|-------------|
| `DJANGO_SIMPLE_QUEUE_ALLOWED_TASKS` | `None` | Set of allowed task paths |
| `DJANGO_SIMPLE_QUEUE_TASK_TIMEOUT` | `3600` | Task timeout in seconds |
| `DJANGO_SIMPLE_QUEUE_MAX_OUTPUT_SIZE` | `10MB` | Max output size in bytes |
| `DJANGO_SIMPLE_QUEUE_MAX_ARGS_SIZE` | `1MB` | Max args JSON size in bytes |

## Functions

### get_allowed_tasks()

Returns the set of allowed task callables, or `None` if no restriction.

```python
from django_simple_queue.conf import get_allowed_tasks

allowed = get_allowed_tasks()
if allowed is None:
    print("All tasks allowed (not recommended)")
else:
    print(f"Allowed tasks: {allowed}")
```

### is_task_allowed(task_path)

Check if a specific task path is allowed.

```python
from django_simple_queue.conf import is_task_allowed

if is_task_allowed("myapp.tasks.send_email"):
    print("Task is allowed")
else:
    print("Task is blocked")
```

### get_task_timeout()

Returns the task timeout in seconds, or `None` if disabled.

```python
from django_simple_queue.conf import get_task_timeout

timeout = get_task_timeout()
if timeout:
    print(f"Tasks timeout after {timeout} seconds")
else:
    print("No timeout configured")
```

### get_max_output_size()

Returns the maximum output size in bytes.

```python
from django_simple_queue.conf import get_max_output_size

max_size = get_max_output_size()
print(f"Max output: {max_size / 1024 / 1024:.1f} MB")
```

### get_max_args_size()

Returns the maximum args JSON size in bytes.

```python
from django_simple_queue.conf import get_max_args_size

max_size = get_max_args_size()
print(f"Max args: {max_size / 1024:.1f} KB")
```

## Example Configuration

```python
# settings.py

# Only allow specific tasks
DJANGO_SIMPLE_QUEUE_ALLOWED_TASKS = {
    "orders.tasks.process_order",
    "emails.tasks.send_notification",
    "reports.tasks.generate_daily",
}

# 5 minute timeout
DJANGO_SIMPLE_QUEUE_TASK_TIMEOUT = 300

# Limit output to 5 MB
DJANGO_SIMPLE_QUEUE_MAX_OUTPUT_SIZE = 5 * 1024 * 1024

# Limit args to 100 KB
DJANGO_SIMPLE_QUEUE_MAX_ARGS_SIZE = 100 * 1024
```

See the [Configuration Guide](../getting-started/configuration.md) for detailed explanations of each setting.
