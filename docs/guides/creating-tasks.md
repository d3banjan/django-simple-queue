# Creating Tasks

This guide covers how to define task functions and enqueue them for execution.

## Defining Task Functions

Task functions are regular Python functions that:

1. Accept **keyword arguments only** (passed as a dict)
2. Return a **string** (stored in task output)
3. Are importable via a dotted path

```python
# myapp/tasks.py

def send_email(to, subject, body, cc=None):
    """Send an email in the background."""
    import smtplib
    # Send email logic...
    return f"Email sent to {to}"


def process_image(image_id, resize_to=None, format="png"):
    """Process and optionally resize an image."""
    from myapp.models import Image
    image = Image.objects.get(id=image_id)
    # Processing logic...
    return f"Image {image_id} processed"
```

## Enqueuing Tasks

Use the `create_task` function to add tasks to the queue:

```python
from django_simple_queue.utils import create_task

# Basic usage
task_id = create_task(
    task="myapp.tasks.send_email",
    args={
        "to": "user@example.com",
        "subject": "Hello",
        "body": "Welcome to our service!"
    }
)

# With optional arguments
task_id = create_task(
    task="myapp.tasks.process_image",
    args={
        "image_id": 42,
        "resize_to": (800, 600),
        "format": "webp"
    }
)
```

## Arguments Format

The `args` parameter must be a **dictionary** that is JSON-serializable:

```python
# Valid argument types
args = {
    "string": "hello",
    "number": 42,
    "float": 3.14,
    "boolean": True,
    "null": None,
    "list": [1, 2, 3],
    "nested": {"key": "value"}
}

# NOT valid - will raise TypeError
args = ["positional", "args"]  # Must be dict, not list
```

!!! warning "No Positional Arguments"
    Task functions receive arguments as `**kwargs`, so all arguments must be keyword arguments in the dict.

## Return Values

Task functions should return a string. The return value is stored in `task.output`:

```python
def example_task(data):
    result = process(data)
    return f"Processed {len(result)} items"  # Stored in task.output
```

For complex return data, serialize to JSON:

```python
import json

def example_task(data):
    result = {"processed": 100, "failed": 2}
    return json.dumps(result)
```

## Best Practices

### 1. Import Inside Functions

Import dependencies inside the function to avoid loading them at worker startup:

```python
# Good - imports only when task runs
def send_notification(user_id, message):
    from myapp.models import User
    from myapp.services import NotificationService

    user = User.objects.get(id=user_id)
    NotificationService.send(user, message)
    return "Notification sent"


# Avoid - loads models at import time
from myapp.models import User  # Loaded when worker starts

def send_notification(user_id, message):
    user = User.objects.get(id=user_id)
    ...
```

### 2. Pass IDs, Not Objects

Pass database IDs instead of model instances:

```python
# Good - passes ID
task_id = create_task(
    task="myapp.tasks.process_order",
    args={"order_id": order.id}
)

# Bad - can't serialize model instance
task_id = create_task(
    task="myapp.tasks.process_order",
    args={"order": order}  # TypeError!
)
```

### 3. Keep Tasks Focused

Each task should do one thing:

```python
# Good - separate tasks
def send_welcome_email(user_id): ...
def create_default_settings(user_id): ...
def notify_admin(user_id): ...

# Then create multiple tasks
for task_func in ["send_welcome_email", "create_default_settings", "notify_admin"]:
    create_task(task=f"myapp.tasks.{task_func}", args={"user_id": user.id})
```

### 4. Handle Failures Gracefully

Tasks should handle expected errors and provide useful error messages:

```python
def process_payment(payment_id):
    from myapp.models import Payment
    from myapp.exceptions import PaymentError

    try:
        payment = Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        return f"Payment {payment_id} not found"

    try:
        result = payment.process()
        return f"Payment {payment_id} processed: {result}"
    except PaymentError as e:
        # Log for debugging, return error message
        logger.exception("Payment processing failed")
        raise  # Re-raise to mark task as failed
```

## Creating Tasks from Various Contexts

### From Views

```python
from django.http import JsonResponse
from django_simple_queue.utils import create_task

def upload_file(request):
    file = request.FILES['file']
    saved_path = save_file(file)

    task_id = create_task(
        task="myapp.tasks.process_upload",
        args={"file_path": saved_path}
    )

    return JsonResponse({"task_id": str(task_id)})
```

### From Signals

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from myapp.models import Order
from django_simple_queue.utils import create_task

@receiver(post_save, sender=Order)
def order_created(sender, instance, created, **kwargs):
    if created:
        create_task(
            task="myapp.tasks.process_new_order",
            args={"order_id": instance.id}
        )
```

### From Management Commands

```python
from django.core.management.base import BaseCommand
from django_simple_queue.utils import create_task

class Command(BaseCommand):
    def handle(self, *args, **options):
        for user_id in User.objects.values_list('id', flat=True):
            create_task(
                task="myapp.tasks.send_newsletter",
                args={"user_id": user_id}
            )
        self.stdout.write("Newsletter tasks created")
```

## Next Steps

- Understand the [task lifecycle](lifecycle.md)
- Use [generator functions](generators.md) for streaming output
- Handle [errors](errors.md) and failures
