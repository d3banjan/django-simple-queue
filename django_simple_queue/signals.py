"""
Signals emitted during task lifecycle.

This module defines Django signals that are fired at various points during
task execution, allowing you to hook into the task lifecycle.

Signals:
    before_job: Fired before task execution begins.
        - sender: Task class
        - task: The Task instance being executed

    on_success: Fired when a task completes successfully.
        - sender: Task class
        - task: The completed Task instance

    on_failure: Fired when a task fails with an exception or timeout.
        - sender: Task class
        - task: The failed Task instance
        - error: The exception that caused the failure (may be None for orphaned tasks)

    before_loop: Fired before each iteration of a generator task.
        - sender: Task class
        - task: The Task instance
        - iteration: Current iteration index (0-based)

    after_loop: Fired after each iteration of a generator task.
        - sender: Task class
        - task: The Task instance
        - output: The value yielded by the generator
        - iteration: Current iteration index (0-based)

Example:
    Connecting to signals::

        from django.dispatch import receiver
        from django_simple_queue.signals import on_success, on_failure

        @receiver(on_success)
        def handle_task_success(sender, task, **kwargs):
            print(f"Task {task.id} completed successfully!")

        @receiver(on_failure)
        def handle_task_failure(sender, task, error, **kwargs):
            print(f"Task {task.id} failed: {error}")
"""
import django.dispatch

before_job = django.dispatch.Signal()
"""Signal fired before task execution begins. Provides: task."""

on_success = django.dispatch.Signal()
"""Signal fired when a task completes successfully. Provides: task."""

on_failure = django.dispatch.Signal()
"""Signal fired when a task fails. Provides: task, error."""

before_loop = django.dispatch.Signal()
"""Signal fired before each generator iteration. Provides: task, iteration."""

after_loop = django.dispatch.Signal()
"""Signal fired after each generator iteration. Provides: task, output, iteration."""
