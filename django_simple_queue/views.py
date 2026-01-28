"""
Views for django-simple-queue.

Provides HTTP endpoints for checking task status.
"""
from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render

from django_simple_queue.models import Task


def view_task_status(request):
    """
    Display or return the status of a task.

    GET Parameters:
        task_id (required): UUID of the task to query.
        type (optional): Set to "json" for JSON response, otherwise renders HTML.

    Returns:
        - JSON response with task data if type=json
        - HTML page with task details otherwise
        - HttpResponseBadRequest if task_id is missing, invalid, or not found

    Example:
        GET /django_simple_queue/task?task_id=abc123
        GET /django_simple_queue/task?task_id=abc123&type=json
    """
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
