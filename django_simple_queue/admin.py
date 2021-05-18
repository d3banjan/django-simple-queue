from django.contrib import admin
from django.shortcuts import reverse
from django.utils.safestring import mark_safe
from django_simple_queue.models import Task


@admin.action(description='Enqueue')
def enqueue_tasks(modeladmin, request, queryset):
    queryset.update(status=Task.QUEUED)


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

    ordering = ['-created', ]
    list_display = ('id', 'created', 'modified', 'task', 'status_page_link')
    list_filter = ('status', 'created', )
    search_fields = ('id', 'task', 'output')
    actions = [enqueue_tasks]
