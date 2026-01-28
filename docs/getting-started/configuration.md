# Configuration

All settings are configured in your Django `settings.py` with the `DJANGO_SIMPLE_QUEUE_` prefix.

## Available Settings

### DJANGO_SIMPLE_QUEUE_ALLOWED_TASKS

**Type:** `set[str] | None`
**Default:** `None` (all tasks allowed)

Restricts which callables can be executed. When set, only tasks in this set can be created.

```python
DJANGO_SIMPLE_QUEUE_ALLOWED_TASKS = {
    "myapp.tasks.send_email",
    "myapp.tasks.process_order",
    "myapp.tasks.generate_report",
}
```

!!! warning "Security Recommendation"
    Always configure an allowlist in production. Without it, any callable in your codebase could potentially be executed.

Set to an empty set to disallow all tasks:

```python
DJANGO_SIMPLE_QUEUE_ALLOWED_TASKS = set()  # No tasks allowed
```

---

### DJANGO_SIMPLE_QUEUE_TASK_TIMEOUT

**Type:** `int | None`
**Default:** `3600` (1 hour)

Maximum execution time for a task in seconds. Tasks exceeding this timeout are terminated and marked as failed.

```python
# 5 minute timeout
DJANGO_SIMPLE_QUEUE_TASK_TIMEOUT = 300

# 30 minute timeout
DJANGO_SIMPLE_QUEUE_TASK_TIMEOUT = 1800

# Disable timeout (tasks can run indefinitely)
DJANGO_SIMPLE_QUEUE_TASK_TIMEOUT = None
```

!!! tip
    Set appropriate timeouts based on your longest-running tasks. Tasks that time out will be terminated with SIGTERM, then SIGKILL if they don't stop.

---

### DJANGO_SIMPLE_QUEUE_MAX_OUTPUT_SIZE

**Type:** `int`
**Default:** `10485760` (10 MB)

Maximum size in bytes for task output stored in the database.

```python
# 1 MB limit
DJANGO_SIMPLE_QUEUE_MAX_OUTPUT_SIZE = 1_000_000

# 100 KB limit
DJANGO_SIMPLE_QUEUE_MAX_OUTPUT_SIZE = 100_000
```

---

### DJANGO_SIMPLE_QUEUE_MAX_ARGS_SIZE

**Type:** `int`
**Default:** `1048576` (1 MB)

Maximum size in bytes for the JSON-serialized task arguments.

```python
# 100 KB limit
DJANGO_SIMPLE_QUEUE_MAX_ARGS_SIZE = 100_000
```

## Example Configuration

```python
# settings.py

# Only allow specific tasks to be executed
DJANGO_SIMPLE_QUEUE_ALLOWED_TASKS = {
    "orders.tasks.process_order",
    "orders.tasks.send_confirmation",
    "reports.tasks.generate_daily_report",
    "reports.tasks.send_report_email",
}

# Tasks timeout after 10 minutes
DJANGO_SIMPLE_QUEUE_TASK_TIMEOUT = 600

# Limit output size to 5 MB
DJANGO_SIMPLE_QUEUE_MAX_OUTPUT_SIZE = 5 * 1024 * 1024

# Limit args size to 500 KB
DJANGO_SIMPLE_QUEUE_MAX_ARGS_SIZE = 500 * 1024
```

## Next Steps

- See the [Quick Start](quickstart.md) for a complete example
- Learn about [worker optimization](../guides/worker-optimization.md) for production deployments
