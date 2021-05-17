from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
import uuid
import importlib
import json


class Task(models.Model):
    """Model for the task."""
    
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
    
    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = _("Task")
        verbose_name_plural = _("Tasks")
        
    @property
    def as_dict(self):
        return {
            "id": str(self.id),
            "created": str(self.created),
            "modified": str(self.modified),
            "task": self.task,
            "args": self.args,
            "status": self.get_status_display(),
            "output": self.output,
        }

    @staticmethod
    def _callable_task(task):
        """Checks if the task is callable."""
        path = task.split('.')
        module = importlib.import_module('.'.join(path[:-1]))
        func = getattr(module, path[-1])
        if callable(func) is False:
            raise TypeError("'{}' is not callable".format(task))
        return func

    def clean_task(self):
        """Custom validation of the task field."""
        try:
            self._callable_task(self.task)
        except:
            raise ValidationError({
                'callable': ValidationError(
                    _('Invalid callable, must be importable'), code='invalid')
            })
        
    def clean_args(self):
        """Custom validation of the args field."""
        try:
            json.loads(self.args)
        except:
            raise ValidationError(_('Invalid JSON text'), code='invalid')