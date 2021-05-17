from django.urls import re_path, path
from taskmanager.views import (
    view_task_status,
)


app_name = 'taskmanager'
urlpatterns = [
    path('task', view_task_status, name="task"),
]