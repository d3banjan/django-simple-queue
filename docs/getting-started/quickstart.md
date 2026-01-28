# Quick Start

This guide walks you through creating and running your first background task.

## 1. Create a Task Function

Create a module for your task functions. The function should accept keyword arguments and return a string (or yield strings for generators).

```python
# myapp/tasks.py

def process_order(order_id, notify_customer=True):
    """
    Process an order in the background.

    Args:
        order_id: The ID of the order to process
        notify_customer: Whether to send notification email

    Returns:
        A status message
    """
    from myapp.models import Order

    order = Order.objects.get(id=order_id)

    # Do the processing...
    order.status = 'processed'
    order.save()

    if notify_customer:
        # Send email...
        pass

    return f"Order {order_id} processed successfully"
```

## 2. Configure Allowed Tasks

Add your task to the allowlist in `settings.py`:

```python
DJANGO_SIMPLE_QUEUE_ALLOWED_TASKS = {
    "myapp.tasks.process_order",
}
```

## 3. Create a Task

Use the `create_task` utility to enqueue tasks:

```python
# In a view, signal handler, or anywhere in your code
from django_simple_queue.utils import create_task

def place_order(request):
    # Create the order...
    order = Order.objects.create(...)

    # Queue background processing
    task_id = create_task(
        task="myapp.tasks.process_order",
        args={
            "order_id": order.id,
            "notify_customer": True
        }
    )

    return JsonResponse({
        "order_id": order.id,
        "task_id": str(task_id)
    })
```

## 4. Start the Worker

Run the worker command in a terminal:

```bash
python manage.py task_worker
```

You'll see output like:

```
Task timeout configured: 3600 seconds
2024-01-15 10:30:00: [RAM Usage: 45.2 MB] Heartbeat..
Initiating task id: abc123-def456...
Finished task id: abc123-def456
```

## 5. Check Task Status

### Via URL

Visit `/django_simple_queue/task?task_id=<task_id>` for an HTML status page, or add `&type=json` for JSON response:

```bash
curl "http://localhost:8000/django_simple_queue/task?task_id=abc123&type=json"
```

```json
{
    "id": "abc123-def456-...",
    "created": "2024-01-15 10:30:00",
    "status": "Completed",
    "output": "Order 42 processed successfully",
    "error": null
}
```

### Via Code

```python
from django_simple_queue.models import Task

task = Task.objects.get(id=task_id)
print(task.status)        # 2 (Task.COMPLETED)
print(task.get_status_display())  # "Completed"
print(task.output)        # "Order 42 processed successfully"
```

### Via Admin

Navigate to Django Admin at `/admin/django_simple_queue/task/` to view all tasks with filtering and search.

## Complete Example

Here's a full example showing a view that creates a task and returns immediately:

```python
# myapp/views.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django_simple_queue.utils import create_task

@require_POST
def start_report_generation(request):
    """Start generating a report in the background."""
    report_type = request.POST.get('report_type', 'daily')

    task_id = create_task(
        task="myapp.tasks.generate_report",
        args={
            "report_type": report_type,
            "user_id": request.user.id
        }
    )

    return JsonResponse({
        "message": "Report generation started",
        "task_id": str(task_id),
        "status_url": f"/django_simple_queue/task?task_id={task_id}&type=json"
    })


def check_task_status(request, task_id):
    """Check the status of a background task."""
    from django_simple_queue.models import Task

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return JsonResponse({"error": "Task not found"}, status=404)

    return JsonResponse({
        "id": str(task.id),
        "status": task.get_status_display(),
        "output": task.output,
        "error": task.error
    })
```

## Next Steps

- Learn about [task lifecycle](../guides/lifecycle.md) and status transitions
- Use [signals](../guides/signals.md) to react to task events
- Handle [errors](../guides/errors.md) gracefully
- Optimize for production with [worker optimization](../guides/worker-optimization.md)
