import os

from django.db import transaction

from django_simple_queue import signals
from django_simple_queue.models import Task


def detect_orphaned_tasks():
    """Check for PROGRESS tasks with dead worker PIDs and mark them FAILED."""
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


def handle_subprocess_exit(task_id, exit_code):
    """Handle non-zero subprocess exit codes."""
    if exit_code is None or exit_code == 0:
        return
    task = Task.objects.get(id=task_id)
    if task.status == Task.PROGRESS:
        task.error = (task.error or "") + f"\nWorker subprocess exited with code {exit_code}"
        task.status = Task.FAILED
        task.worker_pid = None
        task.save(update_fields=["status", "error", "worker_pid", "modified"])
        signals.on_failure.send(sender=Task, task=task, error=None)


def handle_task_timeout(task_id, timeout_seconds):
    """Mark a task as failed due to exceeding the timeout."""
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
