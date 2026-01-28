# Error Handling

This guide covers how errors are captured, stored, and handled in Django Simple Queue.

## Error Storage

When a task fails, error information is stored in separate fields:

| Field | Contents |
|-------|----------|
| `output` | Return value from the task function (may be partial for generators) |
| `error` | Exception representation and traceback |
| `log` | Captured stdout, stderr, and Python logging output |

## Types of Failures

### 1. Exception in Task Function

When your task raises an exception:

```python
def failing_task(x):
    if x < 0:
        raise ValueError("x must be non-negative")
    return f"Processed {x}"
```

The `error` field contains:

```
ValueError('x must be non-negative')

Traceback (most recent call last):
  File ".../worker.py", line 76, in execute_task
    task_obj.output = func(**args)
  File ".../myapp/tasks.py", line 3, in failing_task
    raise ValueError("x must be non-negative")
ValueError: x must be non-negative
```

### 2. Timeout

When a task exceeds `DJANGO_SIMPLE_QUEUE_TASK_TIMEOUT`:

```
Task timed out after 300 seconds
```

### 3. Worker Process Crash

When the worker subprocess exits unexpectedly:

```
Worker subprocess exited with code 1
```

### 4. Orphaned Task

When the worker process dies while task is in progress:

```
Task failed: worker process (PID 12345) no longer running
```

## Reading Error Information

```python
from django_simple_queue.models import Task

task = Task.objects.get(id=task_id)

if task.status == Task.FAILED:
    print("Task failed!")
    print(f"Error: {task.error}")
    print(f"Logs: {task.log}")
    print(f"Partial output: {task.output}")
```

## Handling Errors in Task Functions

### Catching Expected Errors

```python
def resilient_task(item_id):
    from myapp.models import Item

    try:
        item = Item.objects.get(id=item_id)
    except Item.DoesNotExist:
        return f"Item {item_id} not found"  # Return error message, don't fail

    try:
        result = process_item(item)
        return f"Processed: {result}"
    except ProcessingError as e:
        # Re-raise to mark task as failed
        raise
```

### Partial Success in Generators

For generator tasks, you can yield error messages while continuing:

```python
def batch_process(item_ids):
    succeeded = 0
    failed = 0

    for item_id in item_ids:
        try:
            process_item(item_id)
            succeeded += 1
            yield f"Processed {item_id}\n"
        except Exception as e:
            failed += 1
            yield f"ERROR processing {item_id}: {e}\n"

    yield f"Complete: {succeeded} succeeded, {failed} failed"
```

## Using Signals for Error Handling

### Logging Failures

```python
from django.dispatch import receiver
from django_simple_queue.signals import on_failure
import logging

logger = logging.getLogger('tasks')

@receiver(on_failure)
def log_task_failure(sender, task, error, **kwargs):
    logger.error(
        f"Task {task.id} ({task.task}) failed",
        extra={
            'task_id': str(task.id),
            'task_path': task.task,
            'error': str(error) if error else task.error,
        }
    )
```

### Alerting on Critical Failures

```python
@receiver(on_failure)
def alert_on_critical_failure(sender, task, error, **kwargs):
    critical_tasks = ['payments.tasks.', 'orders.tasks.']

    if any(task.task.startswith(prefix) for prefix in critical_tasks):
        send_alert(
            channel='#alerts',
            message=f"Critical task failed: {task.task}\nError: {error}"
        )
```

### Automatic Retry

```python
from django_simple_queue.utils import create_task
import json

MAX_RETRIES = 3

@receiver(on_failure)
def retry_failed_task(sender, task, error, **kwargs):
    args = json.loads(task.args) if task.args else {}
    retry_count = args.get('_retry_count', 0)

    # Only retry certain tasks
    retryable = ['myapp.tasks.send_email', 'myapp.tasks.sync_data']
    if task.task not in retryable:
        return

    if retry_count < MAX_RETRIES:
        create_task(
            task=task.task,
            args={**args, '_retry_count': retry_count + 1}
        )
        logger.info(f"Scheduled retry {retry_count + 1} for task {task.id}")
```

## Re-queuing Failed Tasks

### Via Code

```python
def requeue_failed_task(task_id):
    task = Task.objects.get(id=task_id)
    if task.status == Task.FAILED:
        task.status = Task.QUEUED
        task.error = None
        task.output = None
        task.log = None
        task.worker_pid = None
        task.save()
```

### Via Admin

Use the "Enqueue" action in Django Admin to re-queue selected tasks.

### Bulk Re-queue

```python
def requeue_all_failed():
    return Task.objects.filter(status=Task.FAILED).update(
        status=Task.QUEUED,
        error=None,
        output=None,
        log=None,
        worker_pid=None
    )
```

## Debugging Failed Tasks

### View Full Error

```python
task = Task.objects.get(id=task_id)
print(task.error)  # Full traceback
```

### Check Captured Logs

```python
print(task.log)  # stdout, stderr, logging output
```

### Reproduce Locally

```python
# Get the args that were passed
import json
args = json.loads(task.args)

# Import and call the function directly
from myapp.tasks import my_task
my_task(**args)  # Will raise the exception
```

## Best Practices

### 1. Use Logging

Configure logging in your task functions:

```python
import logging

logger = logging.getLogger(__name__)

def my_task(item_id):
    logger.info(f"Starting task for item {item_id}")
    try:
        result = process(item_id)
        logger.info(f"Completed: {result}")
        return result
    except Exception:
        logger.exception("Task failed")
        raise
```

All logging output is captured in `task.log`.

### 2. Validate Early

Check arguments at the start of the task:

```python
def my_task(item_id, action):
    if action not in ('create', 'update', 'delete'):
        raise ValueError(f"Invalid action: {action}")

    if not Item.objects.filter(id=item_id).exists():
        raise ValueError(f"Item {item_id} not found")

    # Now proceed with confidence
    ...
```

### 3. Clean Up on Failure

Use try/finally for cleanup:

```python
def process_file(file_path):
    temp_file = None
    try:
        temp_file = create_temp_copy(file_path)
        result = process(temp_file)
        return result
    finally:
        if temp_file:
            os.unlink(temp_file)
```

### 4. Don't Swallow Errors

Let exceptions propagate so they're recorded:

```python
# Bad - error is hidden
def my_task():
    try:
        do_work()
    except Exception:
        pass  # Task appears to succeed!

# Good - error is recorded
def my_task():
    try:
        do_work()
    except TemporaryError:
        raise  # Will be marked as failed
    except PermanentError as e:
        return f"Permanent error: {e}"  # Return error message
```

## Next Steps

- [Worker optimization](worker-optimization.md) for production deployments
- [Task lifecycle](lifecycle.md) for understanding status transitions
