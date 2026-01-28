# Monitoring

Functions for monitoring task health and handling failures.

## API Reference

::: django_simple_queue.monitor
    options:
      show_source: true

## Functions

### detect_orphaned_tasks()

Scans for tasks whose worker processes have died and marks them as failed.

This function is called automatically by the task worker on each polling cycle. It:

1. Finds all tasks with status `PROGRESS`
2. Checks if each task's `worker_pid` is still alive
3. If the process is dead, marks the task as `FAILED`
4. Fires the `on_failure` signal

```python
from django_simple_queue.monitor import detect_orphaned_tasks

# Usually called by the worker, but can be called manually
detect_orphaned_tasks()
```

### handle_subprocess_exit(task_id, exit_code)

Handles non-zero subprocess exit codes.

Called by the worker when a task subprocess exits with a non-zero code but didn't raise an exception (e.g., killed by signal).

```python
from django_simple_queue.monitor import handle_subprocess_exit

# Called internally by the worker
handle_subprocess_exit(task_id, exit_code=1)
```

### handle_task_timeout(task_id, timeout_seconds)

Marks a task as failed due to timeout.

Called by the worker when a task exceeds `DJANGO_SIMPLE_QUEUE_TASK_TIMEOUT`.

```python
from django_simple_queue.monitor import handle_task_timeout

# Called internally by the worker
handle_task_timeout(task_id, timeout_seconds=300)
```

## How Orphan Detection Works

```
Worker Process A                  Worker Process B
     │                                  │
     │ Claims Task T1                   │
     │ Sets status=PROGRESS             │
     │ Sets worker_pid=A                │
     │                                  │
     │ Starts executing...              │
     │                                  │
     X Worker A crashes!                │
                                        │
                                        │ Polls for tasks...
                                        │ Calls detect_orphaned_tasks()
                                        │ Finds T1 with status=PROGRESS
                                        │ Checks: is PID A alive?
                                        │ os.kill(A, 0) → ProcessLookupError
                                        │ Marks T1 as FAILED
                                        │ Fires on_failure signal
```

## Failure Messages

| Scenario | Error Message |
|----------|---------------|
| Worker crash | "Task failed: worker process (PID X) no longer running" |
| Timeout | "Task timed out after X seconds" |
| Non-zero exit | "Worker subprocess exited with code X" |

## Monitoring in Production

### Check for Orphaned Tasks

```python
from django_simple_queue.models import Task

# Tasks that might be orphaned (in progress for too long)
from django.utils import timezone
from datetime import timedelta

stale = Task.objects.filter(
    status=Task.PROGRESS,
    modified__lt=timezone.now() - timedelta(hours=1)
)
for task in stale:
    print(f"Possibly orphaned: {task.id} (PID: {task.worker_pid})")
```

### Cleanup Script

```python
from django_simple_queue.monitor import detect_orphaned_tasks

# Run periodically as a cron job or management command
detect_orphaned_tasks()
print("Orphan detection complete")
```

See the [Task Lifecycle](../guides/lifecycle.md) guide for more on failure handling.
