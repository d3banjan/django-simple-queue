# Task Lifecycle

Understanding how tasks move through different states helps you monitor execution and handle edge cases.

## Task States

Tasks progress through the following states:

| Status | Value | Description |
|--------|-------|-------------|
| `QUEUED` | 0 | Task is waiting to be picked up by a worker |
| `PROGRESS` | 1 | Task is currently being executed |
| `COMPLETED` | 2 | Task finished successfully |
| `FAILED` | 3 | Task encountered an error |
| `CANCELLED` | 4 | Task was manually cancelled |

```python
from django_simple_queue.models import Task

# Check status by value
if task.status == Task.COMPLETED:
    print("Task finished!")

# Get human-readable status
print(task.get_status_display())  # "Completed"
```

## State Transitions

```
                    ┌──────────────┐
                    │   QUEUED     │
                    │   (0)        │
                    └──────┬───────┘
                           │
                    Worker claims task
                           │
                           ▼
                    ┌──────────────┐
              ┌─────│  PROGRESS    │─────┐
              │     │   (1)        │     │
              │     └──────────────┘     │
              │                          │
         Success                      Exception
         or timeout                   or crash
              │                          │
              ▼                          ▼
       ┌──────────────┐          ┌──────────────┐
       │  COMPLETED   │          │   FAILED     │
       │   (2)        │          │   (3)        │
       └──────────────┘          └──────────────┘


       ┌──────────────┐
       │  CANCELLED   │  ← Set manually via admin or code
       │   (4)        │
       └──────────────┘
```

## Worker Process Flow

1. **Polling**: Worker polls for QUEUED tasks every 3-9 seconds (randomized)
2. **Claiming**: Uses `SELECT FOR UPDATE SKIP LOCKED` to claim exactly one task
3. **Status Update**: Sets status to PROGRESS and records `worker_pid`
4. **Subprocess**: Spawns a subprocess to execute the task function
5. **Completion**: Updates status to COMPLETED or FAILED based on result
6. **Cleanup**: Clears `worker_pid`, stores `log` output

### Task Fields Updated During Execution

| Field | When Updated | Description |
|-------|--------------|-------------|
| `status` | Claim, completion | Current execution state |
| `worker_pid` | Claim, completion | PID of worker (cleared when done) |
| `output` | During execution | Return value from task function |
| `error` | On failure | Exception message and traceback |
| `log` | After completion | Captured stdout/stderr/logging |
| `modified` | Any update | Last modification timestamp |

## Failure Modes

Tasks can fail in several ways:

### 1. Exception in Task Function

If the task function raises an exception:

```python
def failing_task(x):
    raise ValueError("Something went wrong")
```

- Status set to `FAILED`
- Exception and traceback stored in `error` field
- `on_failure` signal fired with the exception

### 2. Timeout

If task exceeds `DJANGO_SIMPLE_QUEUE_TASK_TIMEOUT`:

- Worker sends SIGTERM to subprocess
- After 5 seconds, sends SIGKILL if still alive
- Status set to `FAILED`
- Timeout message added to `error` field

### 3. Worker Crash (Orphaned Tasks)

If the worker process dies unexpectedly:

- Task remains in PROGRESS state with stale `worker_pid`
- Other workers periodically check for orphaned tasks
- Dead tasks are detected via `os.kill(pid, 0)`
- Status set to `FAILED` with "worker process no longer running" error

### 4. Subprocess Exit

If subprocess exits with non-zero code (without exception):

- Status set to `FAILED`
- Exit code recorded in `error` field

## Checking Task Status

### In Code

```python
from django_simple_queue.models import Task

task = Task.objects.get(id=task_id)

if task.status == Task.QUEUED:
    print("Still waiting...")
elif task.status == Task.PROGRESS:
    print(f"Running on PID {task.worker_pid}")
elif task.status == Task.COMPLETED:
    print(f"Done! Output: {task.output}")
elif task.status == Task.FAILED:
    print(f"Failed: {task.error}")
```

### Via HTTP

```bash
# JSON response
curl "http://localhost:8000/django_simple_queue/task?task_id=UUID&type=json"
```

```json
{
    "id": "abc123...",
    "status": "In progress",
    "output": null,
    "error": null,
    "worker_pid": 12345,
    "log": null
}
```

## Re-queuing Failed Tasks

Failed tasks can be re-queued through the admin or code:

```python
# Re-queue a single task
task = Task.objects.get(id=task_id)
task.status = Task.QUEUED
task.error = None
task.worker_pid = None
task.save()

# Re-queue all failed tasks
Task.objects.filter(status=Task.FAILED).update(
    status=Task.QUEUED,
    error=None,
    worker_pid=None
)
```

Or use the "Enqueue" action in Django Admin.

## Task Output Fields

After a task completes, several fields contain useful information:

```python
task = Task.objects.get(id=task_id)

# Return value from the task function
print(task.output)

# Exception traceback (if failed)
print(task.error)

# Captured stdout/stderr/logging output
print(task.log)
```

## Next Steps

- Use [signals](signals.md) to react to lifecycle events
- Handle [errors](errors.md) gracefully
- Learn about [generator functions](generators.md) for streaming output
