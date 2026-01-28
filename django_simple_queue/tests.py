import os

from django.test import TransactionTestCase

from django_simple_queue.models import Task
from django_simple_queue.monitor import detect_orphaned_tasks, handle_subprocess_exit
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
        self.assertIn("ValueError", task.error)


class FieldSeparationTest(TransactionTestCase):
    def test_output_only_has_return_value(self):
        task = Task.objects.create(
            task="django_simple_queue.test_tasks.return_hello", args="{}"
        )
        execute_task(task.id)
        task.refresh_from_db()
        self.assertEqual(task.output, "hello")
        self.assertIsNone(task.error)

    def test_error_has_traceback(self):
        task = Task.objects.create(
            task="django_simple_queue.test_tasks.raise_error", args="{}"
        )
        execute_task(task.id)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.FAILED)
        self.assertIn("ValueError", task.error)
        self.assertIn("Traceback", task.error)
        # output should have whatever was produced before the error
        self.assertEqual(task.output, "")

    def test_generator_output_concatenation(self):
        task = Task.objects.create(
            task="django_simple_queue.test_tasks.gen_abc", args="{}"
        )
        execute_task(task.id)
        task.refresh_from_db()
        self.assertEqual(task.output, "abc")
        self.assertIsNone(task.error)


class OrphanDetectionTest(TransactionTestCase):
    def test_dead_pid_marks_task_failed(self):
        task = Task.objects.create(
            task="django_simple_queue.test_tasks.return_hello",
            args="{}",
            status=Task.PROGRESS,
            worker_pid=999999,  # nonexistent PID
        )
        detect_orphaned_tasks()
        task.refresh_from_db()
        self.assertEqual(task.status, Task.FAILED)
        self.assertIn("no longer running", task.error)
        self.assertIsNone(task.worker_pid)

    def test_live_pid_not_touched(self):
        task = Task.objects.create(
            task="django_simple_queue.test_tasks.return_hello",
            args="{}",
            status=Task.PROGRESS,
            worker_pid=os.getpid(),  # this process is alive
        )
        detect_orphaned_tasks()
        task.refresh_from_db()
        self.assertEqual(task.status, Task.PROGRESS)

    def test_nonzero_exit_code_marks_failed(self):
        task = Task.objects.create(
            task="django_simple_queue.test_tasks.return_hello",
            args="{}",
            status=Task.PROGRESS,
        )
        handle_subprocess_exit(task.id, exit_code=1)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.FAILED)
        self.assertIn("exited with code 1", task.error)

    def test_zero_exit_code_no_change(self):
        task = Task.objects.create(
            task="django_simple_queue.test_tasks.return_hello",
            args="{}",
            status=Task.COMPLETED,
        )
        handle_subprocess_exit(task.id, exit_code=0)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.COMPLETED)
