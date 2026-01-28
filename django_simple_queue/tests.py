import os
import threading
from multiprocessing import Process

from django.test import TransactionTestCase

from django_simple_queue import signals
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


class SignalTest(TransactionTestCase):
    def test_regular_task_signals(self):
        received = []

        def on_before(sender, task, **kw):
            received.append("before_job")

        def on_success(sender, task, **kw):
            received.append("on_success")

        signals.before_job.connect(on_before)
        signals.on_success.connect(on_success)
        try:
            task = Task.objects.create(
                task="django_simple_queue.test_tasks.return_hello", args="{}"
            )
            execute_task(task.id)
            self.assertEqual(received, ["before_job", "on_success"])
        finally:
            signals.before_job.disconnect(on_before)
            signals.on_success.disconnect(on_success)

    def test_failing_task_signals(self):
        received = []
        errors = []

        def on_before(sender, task, **kw):
            received.append("before_job")

        def on_fail(sender, task, error=None, **kw):
            received.append("on_failure")
            errors.append(error)

        signals.before_job.connect(on_before)
        signals.on_failure.connect(on_fail)
        try:
            task = Task.objects.create(
                task="django_simple_queue.test_tasks.raise_error", args="{}"
            )
            execute_task(task.id)
            self.assertEqual(received, ["before_job", "on_failure"])
            self.assertIsInstance(errors[0], ValueError)
        finally:
            signals.before_job.disconnect(on_before)
            signals.on_failure.disconnect(on_fail)

    def test_generator_loop_signals(self):
        iterations = []

        def on_before_loop(sender, task, iteration, **kw):
            iterations.append(("before", iteration))

        def on_after_loop(sender, task, output, iteration, **kw):
            iterations.append(("after", iteration, output))

        signals.before_loop.connect(on_before_loop)
        signals.after_loop.connect(on_after_loop)
        try:
            task = Task.objects.create(
                task="django_simple_queue.test_tasks.gen_abc", args="{}"
            )
            execute_task(task.id)
            self.assertEqual(
                iterations,
                [
                    ("before", 0),
                    ("after", 0, "a"),
                    ("before", 1),
                    ("after", 1, "b"),
                    ("before", 2),
                    ("after", 2, "c"),
                ],
            )
        finally:
            signals.before_loop.disconnect(on_before_loop)
            signals.after_loop.disconnect(on_after_loop)


class PipeLogCaptureTest(TransactionTestCase):
    def test_stdout_captured_in_pipe(self):
        from django.db import connections

        task = Task.objects.create(
            task="django_simple_queue.test_tasks.print_and_return",
            args="{}",
            status=Task.PROGRESS,  # Set to PROGRESS like parent would
        )
        # Close parent's DB connections before fork (like task_worker does)
        connections.close_all()

        read_fd, write_fd = os.pipe()
        p = Process(target=execute_task, args=(task.id, write_fd))
        p.start()
        os.close(write_fd)

        log_chunks = []

        def drain():
            with os.fdopen(read_fd, "r", closefd=True) as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    log_chunks.append(chunk)

        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        p.join()
        reader.join(timeout=5)

        log_output = "".join(log_chunks)
        self.assertIn("log line from stdout", log_output)
        self.assertIn("log line from stderr", log_output)
        self.assertIn("log line from logging", log_output)
        task.refresh_from_db()
        self.assertEqual(task.output, "result")  # output is clean
