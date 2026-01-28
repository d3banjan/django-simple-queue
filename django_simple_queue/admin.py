"""
Django admin configuration for django-simple-queue.

Provides a customized admin interface for viewing and managing tasks.
"""
from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ngettext
from django_simple_queue.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """
    Admin interface for Task model.

    Features:
        - All fields are read-only when editing an existing task
        - Status column links to the task status page
        - "Enqueue" action to re-queue selected tasks
        - Search by task ID, callable path, and output
        - Filter by status, created, and modified dates

    Note:
        Tasks are generally created programmatically via ``create_task()``,
        but the admin interface is useful for monitoring and re-queuing
        failed tasks.
    """

    def get_readonly_fields(self, request, obj=None):
        if obj:
            self.readonly_fields = [field.name for field in obj.__class__._meta.fields]
        return self.readonly_fields

    def status_page_link(self, obj):
        """
        Generate a clickable link to the task status page.

        Used as a column in the admin list view. Opens in a new tab.

        Args:
            obj: The Task instance.

        Returns:
            Safe HTML link to the task status view.
        """
        return format_html(
            '<a href="{}?task_id={}" target="_blank">{}</a>',
            reverse('django_simple_queue:task'),
            obj.id,
            obj.get_status_display(),
        )
    status_page_link.short_description = "Status"

    @admin.action(description='Enqueue')
    def enqueue_tasks(self, request, queryset):
        """
        Admin action to re-queue selected tasks.

        Changes the status of selected tasks back to QUEUED so they will
        be picked up by a worker. Useful for retrying failed tasks.

        Args:
            request: The HTTP request.
            queryset: QuerySet of selected Task instances.
        """
        updated = queryset.update(status=Task.QUEUED)
        self.message_user(request, ngettext(
            '%d task was successfully enqueued.',
            '%d tasks were successfully enqueued.',
            updated,
        ) % updated, messages.SUCCESS)

    ordering = ['-modified', ]
    list_display = ('id', 'created', 'modified', 'task', 'status_page_link')
    list_filter = ('status', 'created', 'modified')
    search_fields = ('id', 'task', 'output')
    actions = ['enqueue_tasks']
