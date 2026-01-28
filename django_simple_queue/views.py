from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render

from django_simple_queue.models import Task


def view_task_status(request):
    """View for displaying the status of the task."""
    task_id = request.GET.get("task_id")
    if not task_id:
        return HttpResponseBadRequest("Missing task_id parameter.")

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return HttpResponseBadRequest("Task not found.")
    except (ValueError, TypeError, ValidationError):
        return HttpResponseBadRequest("Invalid task_id format.")

    if request.GET.get("type") == "json":
        return JsonResponse(task.as_dict)

    return render(request, "django_simple_queue/task_status.html", {"task": task})
