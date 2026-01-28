# Admin Interface

Django Simple Queue includes a customized Django Admin interface for viewing and managing tasks.

## Features

The `TaskAdmin` class provides:

- **Read-only fields**: All fields are read-only when editing existing tasks
- **Status page link**: Clickable link to the task status page
- **Enqueue action**: Re-queue failed or cancelled tasks
- **Search**: Find tasks by ID, callable path, or output
- **Filters**: Filter by status, created date, modified date

## Accessing the Admin

After adding `django_simple_queue` to `INSTALLED_APPS` and running migrations, access tasks at:

```
http://localhost:8000/admin/django_simple_queue/task/
```

## List View

The task list displays:

| Column | Description |
|--------|-------------|
| ID | Task UUID (clickable for detail view) |
| Created | When the task was created |
| Modified | When the task was last updated |
| Task | Dotted path to the callable |
| Status | Clickable link to status page (opens in new tab) |

### Default Ordering

Tasks are ordered by `modified` descending (most recent first).

## Detail View

All fields are read-only. Displays:

- All task metadata
- Full output, error, and log content
- Worker PID (if in progress)

## Actions

### Enqueue

Select one or more tasks and choose "Enqueue" from the action dropdown to change their status to `QUEUED`.

This is useful for:

- Retrying failed tasks
- Re-running completed tasks
- Processing cancelled tasks

!!! warning "No Cleanup"
    The Enqueue action only changes status. It does not clear `error`, `output`, or `log` fields. Consider clearing these manually or via code if needed.

## Filtering

### By Status

Filter tasks by their current status:

- Queued
- In progress
- Completed
- Failed
- Cancelled

### By Date

Filter by:

- Created date
- Modified date

Options include: Today, Past 7 days, This month, This year.

## Searching

Search across:

- Task ID (UUID)
- Task path (callable)
- Output content

Example searches:

- `send_email` - Find all email tasks
- `failed` - Search in output/error text
- `abc123` - Find task by partial ID

## Customization

### Extending TaskAdmin

```python
# myapp/admin.py
from django.contrib import admin
from django_simple_queue.admin import TaskAdmin
from django_simple_queue.models import Task

# Unregister the default admin
admin.site.unregister(Task)

# Register your customized version
@admin.register(Task)
class CustomTaskAdmin(TaskAdmin):
    list_display = ('id', 'task', 'status_page_link', 'created', 'duration')

    def duration(self, obj):
        if obj.status in (Task.COMPLETED, Task.FAILED):
            delta = obj.modified - obj.created
            return f"{delta.total_seconds():.1f}s"
        return "-"
    duration.short_description = "Duration"
```

### Adding Custom Actions

```python
@admin.register(Task)
class CustomTaskAdmin(TaskAdmin):

    @admin.action(description='Mark as cancelled')
    def cancel_tasks(self, request, queryset):
        updated = queryset.filter(
            status__in=[Task.QUEUED, Task.PROGRESS]
        ).update(status=Task.CANCELLED)
        self.message_user(request, f"{updated} tasks cancelled")

    actions = TaskAdmin.actions + ['cancel_tasks']
```

### Custom Filters

```python
from django.contrib import admin
from django.utils import timezone
from datetime import timedelta

class SlowTaskFilter(admin.SimpleListFilter):
    title = 'Performance'
    parameter_name = 'slow'

    def lookups(self, request, model_admin):
        return [
            ('slow', 'Slow (>1 min)'),
            ('fast', 'Fast (<1 min)'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'slow':
            return queryset.filter(
                status__in=[Task.COMPLETED, Task.FAILED],
            ).extra(
                where=["modified - created > interval '1 minute'"]
            )
        # ... etc

@admin.register(Task)
class CustomTaskAdmin(TaskAdmin):
    list_filter = TaskAdmin.list_filter + (SlowTaskFilter,)
```

## API Reference

::: django_simple_queue.admin.TaskAdmin
    options:
      show_source: true
      members:
        - get_readonly_fields
        - status_page_link
        - enqueue_tasks

## Security Considerations

The admin interface allows:

- Viewing task arguments (may contain sensitive data)
- Viewing task output and errors
- Re-queuing tasks (which will execute again)

Ensure admin access is properly restricted in production.
