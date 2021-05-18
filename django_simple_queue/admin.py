from django.contrib import admin
from django.shortcuts import reverse
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.utils.translation import ngettext
from django_simple_queue.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):

    def get_readonly_fields(self, request, obj=None):
        if obj:
            self.readonly_fields = [field.name for field in obj.__class__._meta.fields]
        return self.readonly_fields

    def status_page_link(self, obj):
        return mark_safe("<a href='{}?task_id={}', target='_blank'>{}</a>".format(
            reverse('django_simple_queue:task'),
            obj.id,
            obj.get_status_display(),
        ))
    status_page_link.short_description = "Status"

    @admin.action(description='Enqueue')
    def enqueue_tasks(self, request, queryset):
        updated = queryset.update(status=Task.QUEUED)
        self.message_user(request, ngettext(
            '%d task was successfully enqueued.',
            '%d tasks were successfully enqueued.',
            updated,
        ) % updated, messages.SUCCESS)

    ordering = ['-created', ]
    list_display = ('id', 'created', 'modified', 'task', 'status_page_link')
    list_filter = ('status', 'created', )
    search_fields = ('id', 'task', 'output')
    actions = ['enqueue_tasks']
