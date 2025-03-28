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

[^1]: The metric used is Resident Set Size from the `psutil` python module, which double counts shared libraries and is 
slightly more than actual RAM Usage.
