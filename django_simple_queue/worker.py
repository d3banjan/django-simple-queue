"""
Task execution worker module.

This module contains the core logic for executing tasks in a subprocess,
including support for generator functions and log capture.
"""
import asyncio
import importlib
import inspect
import json
import logging
import os
import sys
import traceback

from django_simple_queue import signals
from django_simple_queue.models import Task


class ManagedEventLoop:
    """
    Context manager for asyncio event loop management.

    Ensures an event loop exists for the current context, creating one if
    necessary. Cleans up the loop on exit.

    Example:
        with ManagedEventLoop() as loop:
            loop.run_until_complete(async_func())
    """

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
    """
    Execute a task by its ID.

    This function is called in a subprocess by the task_worker command.
    It handles loading the callable, executing it with the provided arguments,
    and updating the task status/output in the database.

    For generator functions, each yielded value is appended to the output,
    and before_loop/after_loop signals are fired for each iteration.

    Args:
        task_id: UUID of the task to execute.
        log_fd: Optional file descriptor for capturing stdout/stderr/logging.
            If provided, all output is redirected to this descriptor.

    Signals Fired:
        - before_job: Before execution starts
        - on_success: If task completes successfully
        - on_failure: If task raises an exception
        - before_loop/after_loop: For each generator iteration
    """
    log_file = None
    log_handler = None
    if log_fd is not None:
        log_file = os.fdopen(log_fd, "w")
        sys.stdout = log_file
        sys.stderr = log_file
        log_handler = logging.StreamHandler(log_file)
        log_handler.setFormatter(
            logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
        )
        logging.root.addHandler(log_handler)
        logging.root.setLevel(logging.DEBUG)

    try:
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
    finally:
        if log_file is not None:
            if log_handler is not None:
                logging.root.removeHandler(log_handler)
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            log_file.flush()
            log_file.close()
