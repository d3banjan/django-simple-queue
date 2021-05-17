from django.urls import re_path, path
from django_simple_queue.views import (
    view_task_status,
)


app_name = 'django_simple_queue'
urlpatterns = [
    path('task', view_task_status, name="task"),
]