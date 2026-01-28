# Using Signals

Django Simple Queue emits signals at various points during task execution, allowing you to hook into the task lifecycle.

## Available Signals

| Signal | Fired When | Arguments |
|--------|------------|-----------|
| `before_job` | Before task execution starts | `task` |
| `on_success` | Task completes successfully | `task` |
| `on_failure` | Task fails (exception, timeout, crash) | `task`, `error` |
| `before_loop` | Before each generator iteration | `task`, `iteration` |
| `after_loop` | After each generator iteration | `task`, `output`, `iteration` |

## Connecting to Signals

### Using the Decorator

```python
# myapp/signals.py
from django.dispatch import receiver
from django_simple_queue.signals import before_job, on_success, on_failure

@receiver(before_job)
def log_task_start(sender, task, **kwargs):
    """Log when a task starts executing."""
    print(f"Starting task {task.id}: {task.task}")


@receiver(on_success)
def handle_task_success(sender, task, **kwargs):
    """Handle successful task completion."""
    print(f"Task {task.id} completed: {task.output}")

    # Example: Send notification
    if task.task == "myapp.tasks.generate_report":
        notify_user_report_ready(task)


@receiver(on_failure)
def handle_task_failure(sender, task, error, **kwargs):
    """Handle task failure."""
    print(f"Task {task.id} failed: {error}")

    # Example: Alert on critical failures
    if "payment" in task.task:
        alert_ops_team(task, error)
```

### Manual Connection

```python
from django_simple_queue.signals import on_success

def my_handler(sender, task, **kwargs):
    print(f"Task {task.id} done")

on_success.connect(my_handler)
```

## Signal Details

### before_job

Fired in the subprocess just before the task function is called.

```python
@receiver(before_job)
def on_before_job(sender, task, **kwargs):
    """
    Args:
        sender: Task class
        task: The Task instance about to execute
    """
    # Good for: logging, setting up context
    logger.info(f"Starting {task.task} with args: {task.args}")
```

### on_success

Fired after the task function returns successfully (no exception).

```python
@receiver(on_success)
def on_task_success(sender, task, **kwargs):
    """
    Args:
        sender: Task class
        task: The completed Task instance (status=COMPLETED)
    """
    # Good for: notifications, triggering follow-up tasks
    if task.output:
        process_result(task.output)
```

### on_failure

Fired when a task fails for any reason.

```python
@receiver(on_failure)
def on_task_failure(sender, task, error, **kwargs):
    """
    Args:
        sender: Task class
        task: The failed Task instance (status=FAILED)
        error: The exception that caused failure, or None for:
               - Orphaned tasks (worker died)
               - Subprocess non-zero exit
    """
    if error:
        logger.exception(f"Task {task.id} raised: {error}")
    else:
        logger.error(f"Task {task.id} failed without exception: {task.error}")
```

### before_loop / after_loop

For generator functions, these fire on each iteration:

```python
@receiver(before_loop)
def on_before_iteration(sender, task, iteration, **kwargs):
    """
    Args:
        sender: Task class
        task: The Task instance
        iteration: 0-based iteration index
    """
    logger.debug(f"Task {task.id} starting iteration {iteration}")


@receiver(after_loop)
def on_after_iteration(sender, task, output, iteration, **kwargs):
    """
    Args:
        sender: Task class
        task: The Task instance
        output: The value yielded by the generator
        iteration: 0-based iteration index
    """
    logger.debug(f"Task {task.id} iteration {iteration} yielded: {output}")
```

## Loading Signal Handlers

Ensure your signal handlers are loaded when Django starts. Add to your app's `apps.py`:

```python
# myapp/apps.py
from django.apps import AppConfig

class MyAppConfig(AppConfig):
    name = 'myapp'

    def ready(self):
        import myapp.signals  # noqa: F401
```

## Common Use Cases

### Retry Failed Tasks

```python
from django_simple_queue.signals import on_failure
from django_simple_queue.utils import create_task
from django_simple_queue.models import Task

@receiver(on_failure)
def auto_retry(sender, task, error, **kwargs):
    """Automatically retry failed tasks up to 3 times."""
    import json

    args = json.loads(task.args) if task.args else {}
    retry_count = args.get('_retry_count', 0)

    if retry_count < 3:
        create_task(
            task=task.task,
            args={**args, '_retry_count': retry_count + 1}
        )
```

### Metrics/Monitoring

```python
from django_simple_queue.signals import before_job, on_success, on_failure
import time

task_start_times = {}

@receiver(before_job)
def record_start(sender, task, **kwargs):
    task_start_times[str(task.id)] = time.time()

@receiver(on_success)
def record_success_metrics(sender, task, **kwargs):
    duration = time.time() - task_start_times.pop(str(task.id), time.time())
    metrics.histogram('task.duration', duration, tags=[f'task:{task.task}'])
    metrics.increment('task.success', tags=[f'task:{task.task}'])

@receiver(on_failure)
def record_failure_metrics(sender, task, error, **kwargs):
    task_start_times.pop(str(task.id), None)
    metrics.increment('task.failure', tags=[f'task:{task.task}'])
```

### Chain Tasks

```python
from django_simple_queue.signals import on_success
from django_simple_queue.utils import create_task
import json

@receiver(on_success)
def chain_tasks(sender, task, **kwargs):
    """Run follow-up tasks based on completed task."""
    if task.task == "myapp.tasks.process_order":
        args = json.loads(task.args)
        order_id = args['order_id']

        # Queue follow-up tasks
        create_task(
            task="myapp.tasks.send_confirmation_email",
            args={"order_id": order_id}
        )
        create_task(
            task="myapp.tasks.update_inventory",
            args={"order_id": order_id}
        )
```

## Important Notes

1. **Signals run in subprocess**: `before_job`, `on_success`, `on_failure`, `before_loop`, and `after_loop` run in the task subprocess, not the main worker process.

2. **Database transactions**: Signal handlers run in the same transaction as the task status update.

3. **Exceptions in handlers**: Exceptions in signal handlers are logged but don't affect the task status.

4. **Order not guaranteed**: If multiple handlers are connected, execution order is not guaranteed.

## Next Steps

- Learn about [generator functions](generators.md) and loop signals
- Handle [errors](errors.md) in your tasks
