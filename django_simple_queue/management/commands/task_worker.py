import os
import random
import threading
import time
from multiprocessing import Process

import psutil
from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.db.utils import NotSupportedError
from django.utils import timezone

from django_simple_queue.models import Task
from django_simple_queue.monitor import detect_orphaned_tasks, handle_subprocess_exit
from django_simple_queue.worker import execute_task


def log_memory_usage():
    """Returns the memory usage of the current process in MB."""
    process = psutil.Process()
    mem_info = process.memory_info()
    return round(mem_info.rss / (1024 * 1024), 2)


class Command(BaseCommand):
    help = "Executes the enqueued tasks."

    def handle(self, *args, **options):
        try:
            sleep_interval = random.randint(3, 9)
            while True:
                time.sleep(sleep_interval)
                print(
                    f"{timezone.now()}: [RAM Usage: {log_memory_usage()} MB] Heartbeat.."
                )
                task_id = None
                # Use pessimistic locking to claim a single queued task
                with transaction.atomic():
                    try:
                        qs = Task.objects.select_for_update(skip_locked=True)
                    except NotSupportedError:
                        # Fallback for DBs without skip_locked support
                        qs = Task.objects.select_for_update()

                    queued_task = (
                        qs.filter(status=Task.QUEUED).order_by("modified").first()
                    )
                    if queued_task:
                        queued_task.status = Task.PROGRESS  # claim the task
                        queued_task.worker_pid = os.getpid()
                        queued_task.save(
                            update_fields=["status", "modified", "worker_pid"]
                        )
                        task_id = queued_task.id

                if task_id:
                    # since parent connections are copied to the child process
                    # avoid corruption by closing all connections
                    connections.close_all()

                    # Create pipe for capturing child stdout/stderr/logging
                    read_fd, write_fd = os.pipe()
                    p = Process(
                        target=execute_task, args=(task_id, write_fd)
                    )
                    p.start()
                    os.close(write_fd)  # Parent doesn't write

                    log_chunks = []

                    def drain():
                        with os.fdopen(read_fd, "r", closefd=True) as f:
                            while True:
                                chunk = f.read(4096)
                                if not chunk:
                                    break
                                log_chunks.append(chunk)

                    reader = threading.Thread(target=drain, daemon=True)
                    reader.start()
                    p.join()
                    reader.join(timeout=5)

                    # Store log + clear PID (parent-owned fields only)
                    log_text = "".join(log_chunks)
                    task = Task.objects.get(id=task_id)
                    task.log = log_text if log_text else None
                    task.worker_pid = None
                    task.save(
                        update_fields=["log", "worker_pid", "modified"]
                    )

                    handle_subprocess_exit(task_id, p.exitcode)

                # Check for orphaned tasks before polling for new ones
                detect_orphaned_tasks()

        except KeyboardInterrupt:
            pass
