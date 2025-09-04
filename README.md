# Django simple queue

It is a very simple app which uses database for managing the task queue.

## Installation
````
pip install django-simple-queue
````

## Set up
* Add ``django_simple_queue`` to INSTALLED_APPS in settings.py
* Add the following to urls.py in the main project directory.
````
path('django_simple_queue/', include('django_simple_queue.urls')),
````
* Apply the database migrations

## Usage

### Create a custom settings file `task_worker_settings.py`
If you want a lean taskworker process, thatdoes not run all of the django apps, create a custom settings file in the same 
directory as `<project>/settings.py` that imports the webserver settings, but doesn't load all the django apps that 
the webserver needs. In our tests, this decreased the RAM usage for a single taskworker from `400-500 MB` to just `30-50 MB`[^1].

Also the number of subprocesses (as reported by htop) drops from `10-21` subprocesses to just `1`!

Here is an example --

```python
# task_worker_settings.py
from .settings import *

# Application definition - keep only what's needed for task processing
INSTALLED_APPS = [
    # django packages - minimal required
    "django.contrib.contenttypes",  # Required for DB models
    "django_simple_queue",
    # Only apps needed for task processing
    "<project>",
]

# Remove all middleware
MIDDLEWARE = []

# Remove template settings - task workers don't need templates
TEMPLATES = []

# Disable static/media file handling
STATICFILES_DIRS = ()
STATIC_URL = None
STATIC_ROOT = None
MEDIA_ROOT = None
MEDIA_URL = None

# Disable unnecessary Django features
USE_I18N = False
USE_TZ = True  # Keep timezone support if your tasks rely on it

# Optimize database connections
DATABASES["default"]["CONN_MAX_AGE"] = None  # Persistent connections
DATABASES["default"]["OPTIONS"] = {
    "connect_timeout": 10,
}

# Remove unnecessary authentication settings
AUTH_PASSWORD_VALIDATORS = []

# Disable admin
ADMIN_ENABLED = False

# Disable URL configuration
ROOT_URLCONF = None
```

Start the worker process as follows:
````
python manage.py task_worker
````

Use ``from django_simple_queue.utils import create_task`` for creating new tasks.
e.g.
````
create_task(
    task="full_path_of_function",
    args={"arg1": 1, "arg2": 2} # Should be a dict object
)
````
The task queue can be viewed at /django_simple_queue/task

## Concurrency and locking

To prevent multiple workers from picking the same task, the worker command (`django_simple_queue/management/commands/task_worker.py`) uses database-level pessimistic locking when claiming tasks:

- It wraps the selection in a transaction and queries with `select_for_update(skip_locked=True)` to lock a single queued task row and skip any rows currently locked by another worker.
- Once a task is selected under the lock, the worker immediately marks it as `In progress` (`Task.PROGRESS`) within the same transaction. Only after claiming does it spawn a subprocess to execute the task.
- If the database backend does not support `skip_locked`, the code falls back to `select_for_update()` without the `skip_locked` argument. While this still provides row-level locking on supported backends, `skip_locked` offers better concurrency characteristics.

Recommended backends: For robust concurrent processing with multiple workers, use a database that supports `SELECT ... FOR UPDATE SKIP LOCKED` (e.g., PostgreSQL). SQLite may not provide full locking semantics for this pattern; it is best suited for development or single-worker setups.

[^1]: The metric used is Resident Set Size from the `psutil` python module, which double counts shared libraries and is 
slightly more than actual RAM Usage.
