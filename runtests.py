import os
import sys
import tempfile

import django
from django.conf import settings
from django.test.utils import get_runner

# Use a file-based SQLite database so subprocesses can access it
# (in-memory databases are not shared across processes)
TEST_DB_FILE = os.path.join(tempfile.gettempdir(), "django_simple_queue_test.db")

if not settings.configured:
    settings.configure(
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": TEST_DB_FILE,
                # Use same name for test DB so subprocesses can access it
                "TEST": {
                    "NAME": TEST_DB_FILE,
                },
            }
        },
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "django_simple_queue",
        ],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
    )

django.setup()

if __name__ == "__main__":
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["django_simple_queue"])
    # Clean up test database file
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)
    sys.exit(bool(failures))
