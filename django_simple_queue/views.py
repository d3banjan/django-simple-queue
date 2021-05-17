from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from taskmanager.models import Task


def view_task_status(request):
    """View for displaying the status of the task."""
    try:
        task = Task.objects.get(id=request.GET.get("task_id"))
        if request.GET.get("type") == "json":
            return JsonResponse(task.as_dict)
        html_message = f"""
        <html>
        <head><meta http-equiv="refresh" content='5'></head>
        <body>
        <table><tbdoy>
        <tr><td style='font-style: bold;'>Name</td><td>{task.task}</td></tr>
        <tr><td style='font-style: bold;'>Arguments</td><td>{task.args}</td></tr>
        <tr><td style='font-style: bold;'>Status</td><td>{task.get_status_display()}</td></tr>
        </tbody></table>
        <code><pre>{task.output}</pre></code>
        </body>
        </html>
        """
        return HttpResponse(html_message)
    except:
        pass
    return HttpResponseBadRequest("Invalid task_id requested.")


