import asyncio
import importlib
import inspect
import json
import traceback

from django_simple_queue import signals
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


def execute_task(task_id, log_fd=None):
    task_obj = Task.objects.get(id=task_id)
    print(f"Initiating task id: {task_id}")
    if task_obj.status in (Task.QUEUED, Task.PROGRESS):
        with ManagedEventLoop():
            signals.before_job.send(sender=Task, task=task_obj)
            try:
                path = task_obj.task.split(".")
                module = importlib.import_module(".".join(path[:-1]))
                func = getattr(module, path[-1])
                args = json.loads(task_obj.args)
                task_obj.output = ""
                task_obj.save()

                if inspect.isgeneratorfunction(func):
                    gen = func(**args)
                    iteration = 0
                    for output in gen:
                        signals.before_loop.send(
                            sender=Task, task=task_obj, iteration=iteration
                        )
                        task_obj.output += output
                        task_obj.save()
                        signals.after_loop.send(
                            sender=Task,
                            task=task_obj,
                            output=output,
                            iteration=iteration,
                        )
                        iteration += 1
                else:
                    task_obj.output = func(**args)
                    task_obj.save()

                task_obj.status = Task.COMPLETED
                task_obj.save()
                signals.on_success.send(sender=Task, task=task_obj)
            except Exception as e:
                task_obj.error = f"{repr(e)}\n\n{traceback.format_exc()}"
                task_obj.status = Task.FAILED
                task_obj.save()
                signals.on_failure.send(sender=Task, task=task_obj, error=e)
            finally:
                print(f"Finished task id: {task_id}")
