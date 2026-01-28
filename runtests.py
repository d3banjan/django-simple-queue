import sys

import django
from django.conf import settings
from django.test.utils import get_runner

if not settings.configured:
    settings.configure(
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
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
    sys.exit(bool(failures))
