import os
import threading
from multiprocessing import Process

from django.core.exceptions import ValidationError
from django.test import Client, TestCase, TransactionTestCase, override_settings

from django_simple_queue import signals
from django_simple_queue.models import Task
from django_simple_queue.monitor import (
    detect_orphaned_tasks,
    handle_subprocess_exit,
    handle_task_timeout,
)
from django_simple_queue.utils import TaskNotAllowedError, create_task
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

    def test_timeout_marks_task_failed(self):
        """Tasks that timeout should be marked as failed."""
        task = Task.objects.create(
            task="django_simple_queue.test_tasks.sleep_task",
            args='{"seconds": 10}',
            status=Task.PROGRESS,
        )
        handle_task_timeout(task.id, timeout_seconds=5)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.FAILED)
        self.assertIn("timed out", task.error)
        self.assertIn("5 seconds", task.error)


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


# =============================================================================
# Security Tests
# =============================================================================


class XSSProtectionTest(TestCase):
    """Test that user-controlled data is properly escaped in HTML output."""

    def setUp(self):
        self.client = Client()

    def test_html_response_escapes_task_name(self):
        """Task name with HTML should be escaped."""
        malicious_task = "<script>alert('xss')</script>"
        task = Task.objects.create(
            task=malicious_task,
            args="{}",
            status=Task.COMPLETED,
        )
        response = self.client.get(f"/task?task_id={task.id}")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # The script tag should be escaped, not rendered as HTML
        self.assertNotIn("<script>", content)
        self.assertIn("&lt;script&gt;", content)

    def test_html_response_escapes_output(self):
        """Task output with HTML should be escaped."""
        task = Task.objects.create(
            task="django_simple_queue.test_tasks.return_hello",
            args="{}",
            status=Task.COMPLETED,
            output="<img src=x onerror=alert('xss')>",
        )
        response = self.client.get(f"/task?task_id={task.id}")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # The img tag should be escaped
        self.assertNotIn("<img src=x", content)
        self.assertIn("&lt;img", content)

    def test_html_response_escapes_args(self):
        """Task args with HTML should be escaped."""
        task = Task.objects.create(
            task="django_simple_queue.test_tasks.return_hello",
            args='{"key": "<script>evil</script>"}',
            status=Task.QUEUED,
        )
        response = self.client.get(f"/task?task_id={task.id}")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("<script>evil</script>", content)

    def test_json_response_does_not_escape(self):
        """JSON response should contain raw data (not HTML-escaped)."""
        task = Task.objects.create(
            task="test.task",
            args='{"key": "<script>test</script>"}',
            status=Task.QUEUED,
        )
        response = self.client.get(f"/task?task_id={task.id}&type=json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        # JSON should have raw data
        self.assertIn("<script>test</script>", response.content.decode())


class TaskAllowlistTest(TestCase):
    """Test task allowlist functionality."""

    def test_no_allowlist_permits_all_tasks(self):
        """Without DJANGO_SIMPLE_QUEUE_ALLOWED_TASKS, all tasks are allowed."""
        # Default config has no allowlist
        task_id = create_task(
            task="django_simple_queue.test_tasks.return_hello",
            args={}
        )
        self.assertIsNotNone(task_id)

    @override_settings(DJANGO_SIMPLE_QUEUE_ALLOWED_TASKS={
        "django_simple_queue.test_tasks.return_hello",
    })
    def test_allowlist_permits_listed_tasks(self):
        """Tasks in the allowlist should be permitted."""
        task_id = create_task(
            task="django_simple_queue.test_tasks.return_hello",
            args={}
        )
        self.assertIsNotNone(task_id)

    @override_settings(DJANGO_SIMPLE_QUEUE_ALLOWED_TASKS={
        "django_simple_queue.test_tasks.return_hello",
    })
    def test_allowlist_blocks_unlisted_tasks(self):
        """Tasks NOT in the allowlist should raise TaskNotAllowedError."""
        with self.assertRaises(TaskNotAllowedError) as ctx:
            create_task(
                task="django_simple_queue.test_tasks.gen_abc",
                args={}
            )
        self.assertIn("not in the allowed list", str(ctx.exception))

    @override_settings(DJANGO_SIMPLE_QUEUE_ALLOWED_TASKS=set())
    def test_empty_allowlist_blocks_all_tasks(self):
        """Empty allowlist should block all tasks."""
        with self.assertRaises(TaskNotAllowedError):
            create_task(
                task="django_simple_queue.test_tasks.return_hello",
                args={}
            )


class ModelValidationTest(TestCase):
    """Test that model validation catches specific exceptions."""

    def test_clean_args_rejects_invalid_json(self):
        """Invalid JSON should raise ValidationError."""
        task = Task(
            task="django_simple_queue.test_tasks.return_hello",
            args="not valid json {",
        )
        with self.assertRaises(ValidationError) as ctx:
            task.clean_args()
        self.assertIn("args", ctx.exception.message_dict)

    def test_clean_args_accepts_valid_json(self):
        """Valid JSON should pass validation."""
        task = Task(
            task="django_simple_queue.test_tasks.return_hello",
            args='{"key": "value", "num": 123}',
        )
        # Should not raise
        task.clean_args()

    def test_clean_args_accepts_empty(self):
        """Empty args should pass validation."""
        task = Task(
            task="django_simple_queue.test_tasks.return_hello",
            args=None,
        )
        task.clean_args()  # Should not raise

        task.args = ""
        task.clean_args()  # Should not raise

    def test_clean_task_rejects_nonexistent_module(self):
        """Non-existent module should raise ValidationError."""
        task = Task(
            task="nonexistent.module.function",
            args="{}",
        )
        with self.assertRaises(ValidationError) as ctx:
            task.clean_task()
        self.assertIn("task", ctx.exception.message_dict)


class ViewErrorHandlingTest(TestCase):
    """Test proper error handling in views."""

    def setUp(self):
        self.client = Client()

    def test_missing_task_id_returns_400(self):
        """Missing task_id parameter should return 400."""
        response = self.client.get("/task")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing", response.content.decode())

    def test_invalid_uuid_returns_400(self):
        """Invalid UUID format should return 400."""
        response = self.client.get("/task?task_id=not-a-uuid")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid", response.content.decode())

    def test_nonexistent_task_returns_400(self):
        """Non-existent task UUID should return 400."""
        import uuid
        fake_id = uuid.uuid4()
        response = self.client.get(f"/task?task_id={fake_id}")
        self.assertEqual(response.status_code, 400)
        self.assertIn("not found", response.content.decode())
