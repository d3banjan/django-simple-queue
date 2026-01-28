import random
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
                        queued_task.save(update_fields=["status", "modified"])
                        task_id = queued_task.id

                if task_id:
                    # since parent connections are copied to the child process
                    # avoid corruption by closing all connections
                    connections.close_all()

                    # Create a new process for the task
                    p = Process(target=execute_task, args=(task_id,))
                    p.start()
                    p.join()  # Wait for the process to complete

        except KeyboardInterrupt:
            pass
