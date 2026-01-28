# Worker Optimization

This guide covers how to optimize worker memory usage and performance for production deployments.

## The Problem

By default, when you run `python manage.py task_worker`, Django loads your entire application including:

- All installed apps
- All middleware
- Template engines
- Static file handlers
- Authentication backends
- etc.

This can result in workers using 400-500 MB of RAM each, with 10-20 subprocesses.

## The Solution: Lean Settings

Create a dedicated settings file that only loads what the worker needs:

```python
# myproject/task_worker_settings.py
from .settings import *

# Only essential apps
INSTALLED_APPS = [
    "django.contrib.contenttypes",  # Required for models
    "django_simple_queue",
    "myapp",  # Your app with task functions
]

# No middleware needed
MIDDLEWARE = []

# No templates needed
TEMPLATES = []

# Disable static/media files
STATICFILES_DIRS = ()
STATIC_URL = None
STATIC_ROOT = None
MEDIA_ROOT = None
MEDIA_URL = None

# Disable i18n if not needed
USE_I18N = False
USE_TZ = True  # Keep if tasks rely on timezones

# Optimize database connections
DATABASES["default"]["CONN_MAX_AGE"] = None  # Persistent connections
DATABASES["default"]["OPTIONS"] = {
    "connect_timeout": 10,
}

# Disable auth validators
AUTH_PASSWORD_VALIDATORS = []

# Disable admin
ADMIN_ENABLED = False

# No URL routing needed
ROOT_URLCONF = None
```

## Running with Lean Settings

Use the `DJANGO_SETTINGS_MODULE` environment variable:

```bash
DJANGO_SETTINGS_MODULE=myproject.task_worker_settings python manage.py task_worker
```

Or set it in your process manager configuration.

## Results

With lean settings, you can expect:

| Metric | Default Settings | Lean Settings |
|--------|------------------|---------------|
| RAM per worker | 400-500 MB | 30-50 MB |
| Subprocess count | 10-20 | 1 |
| Startup time | Slower | Faster |

## Which Apps to Include

Include only apps that:

1. Define models used by your tasks
2. Contain your task functions
3. Are dependencies of the above

```python
INSTALLED_APPS = [
    "django.contrib.contenttypes",  # Always required
    "django_simple_queue",          # The queue itself

    # Only your apps that tasks actually use
    "myapp.orders",      # If tasks access Order model
    "myapp.emails",      # If tasks send emails
    # "myapp.frontend",  # Skip - not used by tasks
    # "myapp.admin",     # Skip - not used by tasks
]
```

## Process Manager Configuration

### systemd

```ini
# /etc/systemd/system/task_worker.service
[Unit]
Description=Django Simple Queue Worker
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/myproject
Environment=DJANGO_SETTINGS_MODULE=myproject.task_worker_settings
ExecStart=/var/www/myproject/venv/bin/python manage.py task_worker
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Supervisor

```ini
# /etc/supervisor/conf.d/task_worker.conf
[program:task_worker]
command=/var/www/myproject/venv/bin/python manage.py task_worker
directory=/var/www/myproject
user=www-data
environment=DJANGO_SETTINGS_MODULE="myproject.task_worker_settings"
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/task_worker.log
```

### Docker

```dockerfile
# Dockerfile.worker
FROM python:3.11

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

ENV DJANGO_SETTINGS_MODULE=myproject.task_worker_settings

CMD ["python", "manage.py", "task_worker"]
```

```yaml
# docker-compose.yml
services:
  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      - DJANGO_SETTINGS_MODULE=myproject.task_worker_settings
    depends_on:
      - db
    restart: always
```

## Multiple Workers

For parallel task processing, run multiple worker instances:

```bash
# Run 4 workers
for i in {1..4}; do
    DJANGO_SETTINGS_MODULE=myproject.task_worker_settings \
    python manage.py task_worker &
done
```

Each worker polls independently and uses `SELECT FOR UPDATE SKIP LOCKED` to avoid processing the same task.

### With systemd (multiple instances)

```ini
# /etc/systemd/system/task_worker@.service
[Unit]
Description=Django Task Worker %i
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/myproject
Environment=DJANGO_SETTINGS_MODULE=myproject.task_worker_settings
ExecStart=/var/www/myproject/venv/bin/python manage.py task_worker
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable 4 worker instances
sudo systemctl enable task_worker@{1..4}
sudo systemctl start task_worker@{1..4}
```

## Monitoring Workers

### Check Memory Usage

The worker logs memory usage on each heartbeat:

```
2024-01-15 10:30:00: [RAM Usage: 45.2 MB] Heartbeat..
```

### Check Worker Status

```bash
# systemd
sudo systemctl status task_worker

# supervisor
sudo supervisorctl status task_worker

# docker
docker-compose logs -f worker
```

### Monitor Task Queue

```python
from django_simple_queue.models import Task

# Queue depth
queued = Task.objects.filter(status=Task.QUEUED).count()

# In-progress tasks
in_progress = Task.objects.filter(status=Task.PROGRESS).count()

# Failed in last hour
from django.utils import timezone
from datetime import timedelta

recent_failures = Task.objects.filter(
    status=Task.FAILED,
    modified__gte=timezone.now() - timedelta(hours=1)
).count()
```

## Troubleshooting

### ImportError in Worker

If tasks fail with `ImportError`, ensure the required app is in `INSTALLED_APPS`:

```python
# task_worker_settings.py
INSTALLED_APPS = [
    ...
    "myapp.payments",  # Add the app your task needs
]
```

### Database Connection Issues

With persistent connections, stale connections can cause issues:

```python
# task_worker_settings.py
DATABASES["default"]["CONN_MAX_AGE"] = 600  # 10 minutes instead of unlimited
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True  # Django 4.1+
```

### High Memory with Lean Settings

If memory is still high, check:

1. Your task functions aren't loading heavy modules at import time
2. You're not importing from apps not in `INSTALLED_APPS`
3. Consider using `gc.collect()` after large tasks

## Next Steps

- Configure [task timeouts](../getting-started/configuration.md)
- Use [PostgreSQL](../advanced/databases.md) for production
- Monitor tasks via the [Admin interface](../advanced/admin.md)
