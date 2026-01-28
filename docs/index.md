# Django Simple Queue

A lightweight, database-backed task queue for Django applications.

## Overview

Django Simple Queue provides a simple way to run background tasks in Django using your existing database as the message broker. No additional infrastructure like Redis or RabbitMQ is required.

## Features

- **Database-backed**: Uses your existing Django database as the queue broker
- **Subprocess isolation**: Each task runs in its own subprocess for memory safety
- **Generator support**: Stream output from long-running tasks with generator functions
- **Lifecycle signals**: Hook into task execution with Django signals
- **Orphan detection**: Automatically detects and handles crashed worker processes
- **Task timeout**: Configurable timeout to prevent runaway tasks
- **Admin interface**: View and manage tasks through Django admin
- **Allowlist security**: Restrict which callables can be executed

## Quick Example

```python
# myapp/tasks.py
def send_welcome_email(user_id, template="default"):
    from myapp.models import User
    user = User.objects.get(id=user_id)
    # Send email...
    return f"Email sent to {user.email}"

# Enqueue a task
from django_simple_queue.utils import create_task

task_id = create_task(
    task="myapp.tasks.send_welcome_email",
    args={"user_id": 42, "template": "welcome"}
)
```

```bash
# Start the worker
python manage.py task_worker
```

## When to Use

Django Simple Queue is ideal for:

- **Small to medium applications** that don't need the complexity of Celery
- **Development environments** where you want a simple queue without extra services
- **Applications already using PostgreSQL** that can leverage its locking features
- **Teams that want minimal operational overhead**

For high-throughput applications or those requiring advanced features like task chaining, routing, or rate limiting, consider [Celery](https://docs.celeryq.dev/) or [Django-Q2](https://django-q2.readthedocs.io/).

## Installation

```bash
pip install django-simple-queue
```

See the [Installation Guide](getting-started/installation.md) for detailed setup instructions.

## License

MIT License
