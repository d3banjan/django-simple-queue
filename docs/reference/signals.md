# Signals

Signals emitted during task lifecycle. Connect to these signals to hook into task execution.

## API Reference

::: django_simple_queue.signals
    options:
      show_source: true

## Signal Summary

| Signal | When Fired | Arguments |
|--------|------------|-----------|
| `before_job` | Before task execution | `task` |
| `on_success` | Task completed successfully | `task` |
| `on_failure` | Task failed | `task`, `error` |
| `before_loop` | Before generator iteration | `task`, `iteration` |
| `after_loop` | After generator iteration | `task`, `output`, `iteration` |

## Connecting to Signals

### Using Decorator

```python
from django.dispatch import receiver
from django_simple_queue.signals import on_success, on_failure

@receiver(on_success)
def handle_success(sender, task, **kwargs):
    print(f"Task {task.id} completed")

@receiver(on_failure)
def handle_failure(sender, task, error, **kwargs):
    print(f"Task {task.id} failed: {error}")
```

### Manual Connection

```python
from django_simple_queue.signals import before_job

def my_handler(sender, task, **kwargs):
    print(f"Starting {task.task}")

before_job.connect(my_handler)
```

## Signal Arguments

### before_job

```python
@receiver(before_job)
def handler(sender, task, **kwargs):
    # sender: Task class
    # task: Task instance about to execute
    pass
```

### on_success

```python
@receiver(on_success)
def handler(sender, task, **kwargs):
    # sender: Task class
    # task: Completed Task instance
    pass
```

### on_failure

```python
@receiver(on_failure)
def handler(sender, task, error, **kwargs):
    # sender: Task class
    # task: Failed Task instance
    # error: Exception or None (for orphaned/timeout)
    pass
```

### before_loop / after_loop

```python
@receiver(before_loop)
def handler(sender, task, iteration, **kwargs):
    # iteration: 0-based index
    pass

@receiver(after_loop)
def handler(sender, task, output, iteration, **kwargs):
    # output: Value yielded by generator
    # iteration: 0-based index
    pass
```

## Loading Signal Handlers

Ensure handlers load on Django startup:

```python
# myapp/apps.py
from django.apps import AppConfig

class MyAppConfig(AppConfig):
    name = 'myapp'

    def ready(self):
        import myapp.signals  # noqa
```

See the [Using Signals](../guides/signals.md) guide for more examples.
