from __future__ import annotations

import json
import uuid

from django_simple_queue.conf import is_task_allowed, get_allowed_tasks
from django_simple_queue.models import Task


class TaskNotAllowedError(Exception):
    """Raised when attempting to create a task that is not in the allowed list."""
    pass


def create_task(task: str, args: dict) -> uuid.UUID:
    """
    Create a new task to be executed by the worker.

    Args:
        task: Dotted path to the callable (e.g., "myapp.tasks.process_order")
        args: Dictionary of keyword arguments to pass to the callable

    Returns:
        UUID of the created task

    Raises:
        TypeError: If args is not a dict
        TaskNotAllowedError: If task is not in DJANGO_SIMPLE_QUEUE_ALLOWED_TASKS

    Example:
        from django_simple_queue.utils import create_task

        task_id = create_task(
            task="myapp.tasks.send_email",
            args={"to": "user@example.com", "subject": "Hello"}
        )
    """
    if not isinstance(args, dict):
        raise TypeError("args should be of type dict.")

    if not is_task_allowed(task):
        allowed = get_allowed_tasks()
        if allowed is not None:
            raise TaskNotAllowedError(
                f"Task '{task}' is not in the allowed list. "
                f"Add it to DJANGO_SIMPLE_QUEUE_ALLOWED_TASKS in settings.py"
            )

    obj = Task.objects.create(
        task=task,
        args=json.dumps(args)
    )
    return obj.id
