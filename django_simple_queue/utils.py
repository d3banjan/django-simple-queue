from django_simple_queue.models import Task
import json


def create_task(task, args):
    if isinstance(args, dict):
        obj = Task.objects.create(
            task=task,
            args=json.dumps(args)
        )
        return obj.id
    else:
        raise TypeError("args should be of type dict.")