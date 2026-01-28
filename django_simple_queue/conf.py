"""
Configuration settings for django_simple_queue.

Settings are read from Django's settings.py with the DJANGO_SIMPLE_QUEUE_ prefix.
"""
from __future__ import annotations

from django.conf import settings


def get_allowed_tasks() -> set[str] | None:
    """
    Returns the set of allowed task callables.

    Configure in settings.py:
        DJANGO_SIMPLE_QUEUE_ALLOWED_TASKS = {
            "myapp.tasks.process_order",
            "myapp.tasks.send_email",
        }

    If not set or set to None, ALL tasks are allowed (unsafe, but backwards-compatible).
    Set to an empty set to disallow all tasks.
    """
    allowed = getattr(settings, "DJANGO_SIMPLE_QUEUE_ALLOWED_TASKS", None)
    if allowed is None:
        return None  # No restriction (backwards-compatible but unsafe)
    return set(allowed)


def is_task_allowed(task_path: str) -> bool:
    """
    Check if a task path is in the allowed list.

    Args:
        task_path: Dotted path to the callable (e.g., "myapp.tasks.process_order")

    Returns:
        True if allowed, False if not allowed.
        If DJANGO_SIMPLE_QUEUE_ALLOWED_TASKS is not configured, returns True (permissive).
    """
    allowed = get_allowed_tasks()
    if allowed is None:
        # No allowlist configured - permissive mode (backwards-compatible)
        return True
    return task_path in allowed


def get_max_output_size() -> int:
    """
    Returns the maximum allowed output size in bytes.

    Configure in settings.py:
        DJANGO_SIMPLE_QUEUE_MAX_OUTPUT_SIZE = 1_000_000  # 1MB

    Default: 10MB
    """
    return getattr(settings, "DJANGO_SIMPLE_QUEUE_MAX_OUTPUT_SIZE", 10 * 1024 * 1024)


def get_max_args_size() -> int:
    """
    Returns the maximum allowed args JSON size in bytes.

    Configure in settings.py:
        DJANGO_SIMPLE_QUEUE_MAX_ARGS_SIZE = 100_000  # 100KB

    Default: 1MB
    """
    return getattr(settings, "DJANGO_SIMPLE_QUEUE_MAX_ARGS_SIZE", 1024 * 1024)


def get_task_timeout() -> int | None:
    """
    Returns the maximum execution time for a task in seconds.

    Configure in settings.py:
        DJANGO_SIMPLE_QUEUE_TASK_TIMEOUT = 300  # 5 minutes

    If not set or set to None, tasks can run indefinitely.
    Set to 0 or negative to disable timeout.

    Default: 3600 (1 hour)
    """
    timeout = getattr(settings, "DJANGO_SIMPLE_QUEUE_TASK_TIMEOUT", 3600)
    if timeout is None or timeout <= 0:
        return None
    return timeout
