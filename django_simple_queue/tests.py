from django.test import TransactionTestCase

from django_simple_queue.models import Task
from django_simple_queue.worker import execute_task


class ExecuteTaskTest(TransactionTestCase):
    def test_regular_task(self):
        task = Task.objects.create(
            task="django_simple_queue.test_tasks.return_hello", args="{}"
        )
        execute_task(task.id)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.COMPLETED)
        self.assertEqual(task.output, "hello")

    def test_generator_task(self):
        task = Task.objects.create(
            task="django_simple_queue.test_tasks.gen_abc", args="{}"
        )
        execute_task(task.id)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.COMPLETED)
        self.assertEqual(task.output, "abc")

    def test_failing_task(self):
        task = Task.objects.create(
            task="django_simple_queue.test_tasks.raise_error", args="{}"
        )
        execute_task(task.id)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.FAILED)
        self.assertIn("ValueError", task.output)
