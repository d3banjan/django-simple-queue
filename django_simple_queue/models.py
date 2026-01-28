"""
Task model for django-simple-queue.

This module defines the Task model which represents a unit of work to be
executed asynchronously by a worker process.
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import uuid
import importlib
import json


class Task(models.Model):
    """
    Represents a task to be executed asynchronously by the worker.

    A Task stores all the information needed to execute a callable function
    with the specified arguments, along with its execution state and results.

    Attributes:
        id: UUID primary key for the task.
        created: Timestamp when the task was created.
        modified: Timestamp when the task was last modified.
        task: Dotted path to the callable (e.g., "myapp.tasks.send_email").
        args: JSON-serialized keyword arguments for the callable.
        status: Current execution status (QUEUED, PROGRESS, COMPLETED, FAILED, CANCELLED).
        output: Return value from the callable (stored as text).
        worker_pid: Process ID of the worker handling this task.
        error: Error message and traceback if the task failed.
        log: Captured stdout/stderr/logging output from task execution.

    Example:
        Creating a task directly (prefer using ``create_task`` utility)::

            from django_simple_queue.models import Task
            import json

            task = Task.objects.create(
                task="myapp.tasks.send_email",
                args=json.dumps({"to": "user@example.com", "subject": "Hello"})
            )
    """

    QUEUED = 0
    PROGRESS = 1
    COMPLETED = 2
    FAILED = 3
    CANCELLED = 4

    STATUS_CHOICES = (
        (QUEUED, _("Queued")),
        (PROGRESS, _("In progress")),
        (COMPLETED, _("Completed")),
        (FAILED, _("Failed")),
        (CANCELLED, _("Cancelled"))
    )

    id = models.UUIDField(_("ID"), primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(_("Created"), auto_now_add=True)
    modified = models.DateTimeField(_("Modified"), auto_now=True)
    task = models.CharField(_("Task"), max_length=127, help_text="Name of the function to be called.")
    args = models.TextField(_("Arguments"), null=True, blank=True, help_text="Arguments in JSON format")
    status = models.IntegerField(_("Status"), default=QUEUED, choices=STATUS_CHOICES)
    output = models.TextField(_("Output"), null=True, blank=True)
    worker_pid = models.IntegerField(_("Worker PID"), null=True, blank=True)
    error = models.TextField(_("Error"), null=True, blank=True)
    log = models.TextField(_("Log"), null=True, blank=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = _("Task")
        verbose_name_plural = _("Tasks")

    @property
    def as_dict(self):
        """
        Returns a dictionary representation of the task.

        Useful for JSON serialization in API responses.

        Returns:
            dict: Task data with string-formatted dates and status display.
        """
        return {
            "id": str(self.id),
            "created": str(self.created),
            "modified": str(self.modified),
            "task": self.task,
            "args": self.args,
            "status": self.get_status_display(),
            "output": self.output,
            "worker_pid": self.worker_pid,
            "error": self.error,
            "log": self.log,
        }

    @staticmethod
    def _callable_task(task):
        """
        Validates and returns the callable for a task path.

        Args:
            task: Dotted path to the callable (e.g., "myapp.tasks.send_email").

        Returns:
            The callable function or class.

        Raises:
            ImportError: If the module cannot be imported.
            AttributeError: If the function doesn't exist in the module.
            TypeError: If the resolved object is not callable.
        """
        path = task.split('.')
        module = importlib.import_module('.'.join(path[:-1]))
        func = getattr(module, path[-1])
        if callable(func) is False:
            raise TypeError("'{}' is not callable".format(task))
        return func

    def clean_task(self):
        """
        Validates that the task field contains a valid callable path.

        Called automatically during model validation. Ensures the dotted path
        can be imported and resolved to a callable.

        Raises:
            ValidationError: If the task path is invalid or not callable.
        """
        try:
            self._callable_task(self.task)
        except (ImportError, AttributeError, TypeError, ValueError) as e:
            raise ValidationError({
                'task': ValidationError(
                    _('Invalid callable: %(error)s'),
                    code='invalid',
                    params={'error': str(e)}
                )
            })

    def clean_args(self):
        """
        Validates that the args field contains valid JSON.

        Called automatically during model validation. Ensures the args field
        can be parsed as JSON (should be a dict when deserialized).

        Raises:
            ValidationError: If the args field is not valid JSON.
        """
        if self.args is None or self.args == "":
            return

        try:
            json.loads(self.args)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            raise ValidationError({
                'args': ValidationError(
                    _('Invalid JSON: %(error)s'),
                    code='invalid',
                    params={'error': str(e)}
                )
            })
