# Database Backends

Django Simple Queue uses your existing database as the task queue broker. This page covers database-specific considerations.

## Recommended: PostgreSQL

PostgreSQL is the recommended database for production use due to its robust locking features.

### Key Features

- **`SELECT FOR UPDATE SKIP LOCKED`**: Allows multiple workers to claim tasks concurrently without blocking each other
- **ACID transactions**: Ensures task state changes are atomic
- **Good performance**: Efficient row-level locking

### Configuration

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mydb',
        'USER': 'myuser',
        'PASSWORD': 'mypassword',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,  # Keep connections open for 10 minutes
    }
}
```

### Connection Pool Settings

For production with multiple workers:

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        # ...
        'CONN_MAX_AGE': None,  # Persistent connections
        'CONN_HEALTH_CHECKS': True,  # Django 4.1+
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}
```

## SQLite

SQLite is suitable for development and single-worker setups.

### Limitations

- **No `SKIP LOCKED`**: Falls back to basic `SELECT FOR UPDATE`
- **Database locking**: May experience contention with multiple workers
- **File-based**: Not suitable for distributed deployments

### When to Use

- Local development
- Testing
- Single worker deployments
- Low-volume applications

### Configuration

```python
# settings.py (development)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

## MySQL/MariaDB

MySQL 8.0+ and MariaDB 10.3+ support `SKIP LOCKED`.

### Configuration

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'mydb',
        'USER': 'myuser',
        'PASSWORD': 'mypassword',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}
```

### Considerations

- Ensure InnoDB engine for row-level locking
- Use READ COMMITTED isolation level for best concurrency

## How Task Claiming Works

The worker uses database-level pessimistic locking:

```python
# Simplified from task_worker.py
with transaction.atomic():
    try:
        # Try to use SKIP LOCKED for better concurrency
        qs = Task.objects.select_for_update(skip_locked=True)
    except NotSupportedError:
        # Fallback for databases without skip_locked
        qs = Task.objects.select_for_update()

    # Get the oldest queued task
    task = qs.filter(status=Task.QUEUED).order_by('modified').first()

    if task:
        # Claim the task within the transaction
        task.status = Task.PROGRESS
        task.worker_pid = os.getpid()
        task.save()
```

### With `SKIP LOCKED` (PostgreSQL, MySQL 8+)

```
Worker A: SELECT ... WHERE status=QUEUED FOR UPDATE SKIP LOCKED → Gets Task 1
Worker B: SELECT ... WHERE status=QUEUED FOR UPDATE SKIP LOCKED → Gets Task 2 (skips locked Task 1)
```

Both workers proceed immediately without waiting.

### Without `SKIP LOCKED` (SQLite)

```
Worker A: SELECT ... WHERE status=QUEUED FOR UPDATE → Gets Task 1
Worker B: SELECT ... WHERE status=QUEUED FOR UPDATE → Waits for Worker A to commit
Worker A: Commits → Task 1 now PROGRESS
Worker B: Gets Task 2
```

Worker B must wait, reducing concurrency.

## Multiple Workers

### With PostgreSQL

Run as many workers as needed:

```bash
# Start 4 workers
for i in {1..4}; do
    python manage.py task_worker &
done
```

Each worker claims different tasks thanks to `SKIP LOCKED`.

### With SQLite

Limit to 1-2 workers to avoid contention:

```bash
# Single worker recommended for SQLite
python manage.py task_worker
```

## Indexing

The Task model should have indexes on commonly queried fields. The default migration includes:

- Primary key on `id` (UUID)
- Index on `status` (for filtering queued tasks)
- Index on `modified` (for ordering)

For high-volume queues, consider:

```python
# Custom migration for additional indexes
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('django_simple_queue', 'XXXX_previous'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='task',
            index=models.Index(
                fields=['status', 'modified'],
                name='status_modified_idx'
            ),
        ),
    ]
```

## Cleanup Old Tasks

Regularly clean up completed/failed tasks to maintain performance:

```python
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django_simple_queue.models import Task

class Command(BaseCommand):
    help = 'Clean up old completed tasks'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30)

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options['days'])
        deleted, _ = Task.objects.filter(
            status__in=[Task.COMPLETED, Task.FAILED],
            modified__lt=cutoff
        ).delete()
        self.stdout.write(f"Deleted {deleted} tasks")
```

## Database Comparison

| Feature | PostgreSQL | MySQL 8+ | SQLite |
|---------|------------|----------|--------|
| `SKIP LOCKED` | Yes | Yes | No |
| Multiple workers | Excellent | Good | Limited |
| Row-level locking | Yes | Yes (InnoDB) | No |
| Production ready | Yes | Yes | Dev only |
| Distributed setup | Yes | Yes | No |
