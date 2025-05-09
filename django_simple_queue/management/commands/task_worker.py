import asyncio
import importlib
import inspect
import json
import random
import time
import traceback
from multiprocessing import Process

import psutil
from django.core.management.base import BaseCommand
from django.db import connections
from django.utils import timezone

from django_simple_queue.models import Task


class ManagedEventLoop:
    def __init__(self):
        self.loop = None

    def __enter__(self):
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        return self.loop

    def __exit__(self, exc_type, exc_value, exc_tb):
        if self.loop is not None:
            self.loop.close()



def process_task(task_id):
    task_obj = Task.objects.get(id=task_id)
    print(f"Initiating task id: {task_id}")
    if task_obj.status == Task.QUEUED:  # One more extra check to make sure
        # In case event loop gets killed
        with ManagedEventLoop() as loop:
            try:
                path = task_obj.task.split('.')
                module = importlib.import_module('.'.join(path[:-1]))
                func = getattr(module, path[-1])
                args = json.loads(task_obj.args)
                task_obj.output = ""
                task_obj.status = Task.PROGRESS
                task_obj.save()

                if inspect.isgeneratorfunction(func):
                    for i in func(**args):
                        output = i
                        task_obj.output += output
                        task_obj.save()
                else:
                    task_obj.output = func(**args)
                    task_obj.save()
                task_obj.status = Task.COMPLETED
                task_obj.save()
            except Exception as e:
                task_obj.output += f"{repr(e)}\n\n{traceback.format_exc()}"
                task_obj.status = Task.FAILED
                task_obj.save()
            finally:
                print(f"Finished task id: {task_id}")





def log_memory_usage():
    """Returns the memory usage of the current process in MB."""
    process = psutil.Process()
    mem_info = process.memory_info()
    return round(mem_info.rss / (1024 * 1024), 2)

class Command(BaseCommand):
    help = 'Executes the enqueued tasks.'

    def handle(self, *args, **options):
        try:
            sleep_interval = random.randint(3, 9)
            while True:
                time.sleep(sleep_interval)
                print(f"{timezone.now()}: [RAM Usage: {log_memory_usage()} MB] Heartbeat..")
                queued_task = Task.objects.filter(status=Task.QUEUED).order_by('modified').first()
                if queued_task:
                    # since parent connections are copied to the child process
                    # avoid corruption by closing all connections
                    connections.close_all()

                    # Create a new process for the task
                    p = Process(target=process_task, args=(queued_task.id,))
                    p.start()
                    p.join()  # Wait for the process to complete

        except KeyboardInterrupt:
            pass
