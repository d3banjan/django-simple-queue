"""
Task monitoring and orphan detection utilities.

This module provides functions for detecting and handling tasks whose worker
processes have died unexpectedly, as well as handling task timeouts and
subprocess failures.
"""
from __future__ import annotations

import os
import uuid

from django.db import transaction

from django_simple_queue import signals
from django_simple_queue.models import Task


def detect_orphaned_tasks() -> None:
    """
    Detect and mark orphaned tasks as failed.

    Scans all tasks with status PROGRESS and checks if their worker process
    (identified by worker_pid) is still running. If the process is dead,
    marks the task as FAILED and fires the on_failure signal.

    This function is called periodically by the task_worker command to clean
    up tasks whose workers crashed unexpectedly.

    Note:
        Uses ``select_for_update(skip_locked=True)`` to avoid blocking other workers.
        If the PID exists but belongs to a different user (PermissionError),
        the worker is assumed to still be alive.
    """
    with transaction.atomic():
        in_progress = Task.objects.select_for_update(skip_locked=True).filter(
            status=Task.PROGRESS, worker_pid__isnull=False
        )
        for task in in_progress:
            try:
                os.kill(task.worker_pid, 0)
            except ProcessLookupError:
                task.error = (task.error or "") + (
                    f"\nTask failed: worker process (PID {task.worker_pid}) no longer running"
                )
                task.status = Task.FAILED
                task.worker_pid = None
                task.save(
                    update_fields=["status", "error", "worker_pid", "modified"]
                )
                signals.on_failure.send(sender=Task, task=task, error=None)
            except PermissionError:
                pass  # PID exists, different user — worker is alive


def handle_subprocess_exit(task_id: uuid.UUID, exit_code: int | None) -> None:
    """
    Handle a task subprocess that exited with a non-zero code.

    Called by the task_worker after the subprocess finishes. If the exit code
    indicates failure, marks the task as FAILED and fires the on_failure signal.

    Args:
        task_id: UUID of the task that was being executed.
        exit_code: The subprocess exit code (None or 0 means success).
    """
    if exit_code is None or exit_code == 0:
        return
    task = Task.objects.get(id=task_id)
    if task.status == Task.PROGRESS:
        task.error = (task.error or "") + f"\nWorker subprocess exited with code {exit_code}"
        task.status = Task.FAILED
        task.worker_pid = None
        task.save(update_fields=["status", "error", "worker_pid", "modified"])
        signals.on_failure.send(sender=Task, task=task, error=None)


def handle_task_timeout(task_id: uuid.UUID, timeout_seconds: int) -> None:
    """
    Mark a task as failed due to exceeding the timeout.

    Called by the task_worker when a subprocess doesn't complete within the
    configured timeout. Marks the task as FAILED and fires the on_failure
    signal with a TimeoutError.

    Args:
        task_id: UUID of the task that timed out.
        timeout_seconds: The timeout value that was exceeded.
    """
    task = Task.objects.get(id=task_id)
    if task.status == Task.PROGRESS:
        task.error = (task.error or "") + (
            f"\nTask timed out after {timeout_seconds} seconds"
        )
        task.status = Task.FAILED
        task.worker_pid = None
        task.save(update_fields=["status", "error", "worker_pid", "modified"])
        signals.on_failure.send(sender=Task, task=task, error=TimeoutError(
            f"Task exceeded {timeout_seconds}s timeout"
        ))
