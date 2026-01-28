# Generator Functions

Django Simple Queue supports generator functions for tasks that produce output incrementally. This is useful for long-running tasks where you want to track progress or stream results.

## Basic Usage

Define your task as a generator function using `yield`:

```python
# myapp/tasks.py

def process_items(items):
    """Process items one at a time, yielding progress."""
    for i, item in enumerate(items):
        # Do some work
        result = process_single_item(item)

        # Yield progress update
        yield f"Processed item {i+1}/{len(items)}: {result}\n"

    yield "All items processed!"
```

## How It Works

When the worker detects a generator function:

1. It iterates through the generator
2. Each yielded value is **appended** to `task.output`
3. The task is saved after each yield (visible in real-time)
4. `before_loop` and `after_loop` signals fire for each iteration

```
Generator yields:  "Step 1 done\n" → "Step 2 done\n" → "Finished!"

task.output:       "Step 1 done\n"
                   "Step 1 done\nStep 2 done\n"
                   "Step 1 done\nStep 2 done\nFinished!"
```

## Progress Tracking Example

```python
def import_csv(file_path, batch_size=100):
    """Import CSV file with progress updates."""
    import csv

    with open(file_path) as f:
        reader = list(csv.DictReader(f))
        total = len(reader)

        for i in range(0, total, batch_size):
            batch = reader[i:i + batch_size]

            # Process batch
            for row in batch:
                process_row(row)

            progress = min(i + batch_size, total)
            yield f"Imported {progress}/{total} rows ({progress*100//total}%)\n"

    yield f"Import complete: {total} rows processed"
```

## Monitoring Progress

### Check Progress via API

Poll the task status endpoint to see real-time output:

```python
import requests
import time

def poll_task_progress(task_id):
    while True:
        response = requests.get(
            f"http://localhost:8000/django_simple_queue/task",
            params={"task_id": task_id, "type": "json"}
        )
        data = response.json()

        print(data["output"])

        if data["status"] in ("Completed", "Failed"):
            break

        time.sleep(1)
```

### Using Signals

React to each iteration with signals:

```python
from django.dispatch import receiver
from django_simple_queue.signals import after_loop

@receiver(after_loop)
def on_progress(sender, task, output, iteration, **kwargs):
    """Called after each yield."""
    print(f"Task {task.id} iteration {iteration}: {output}")

    # Example: Update a progress bar, send websocket message, etc.
    if "myapp.tasks.import_csv" in task.task:
        broadcast_progress(task.id, output)
```

## Use Cases

### Large Data Processing

```python
def process_large_dataset(dataset_id):
    """Process records in chunks with progress."""
    from myapp.models import Record

    records = Record.objects.filter(dataset_id=dataset_id)
    total = records.count()
    processed = 0

    for record in records.iterator(chunk_size=1000):
        process_record(record)
        processed += 1

        if processed % 1000 == 0:
            yield f"Processed {processed}/{total} records\n"

    yield f"Complete: processed {total} records"
```

### Multi-Step Pipeline

```python
def run_pipeline(job_id):
    """Run a multi-step pipeline with status updates."""
    yield "Step 1: Fetching data...\n"
    data = fetch_data(job_id)

    yield "Step 2: Validating...\n"
    validated = validate_data(data)

    yield "Step 3: Transforming...\n"
    transformed = transform_data(validated)

    yield "Step 4: Saving results...\n"
    save_results(job_id, transformed)

    yield f"Pipeline complete: processed {len(transformed)} items"
```

### File Download with Progress

```python
def download_large_file(url, destination):
    """Download file with progress reporting."""
    import requests

    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))

    downloaded = 0
    chunk_size = 8192

    with open(destination, 'wb') as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            f.write(chunk)
            downloaded += len(chunk)

            if total_size:
                progress = downloaded * 100 // total_size
                yield f"Downloaded {downloaded}/{total_size} bytes ({progress}%)\n"

    yield f"Download complete: {destination}"
```

## Best Practices

### 1. Yield Meaningful Updates

```python
# Good - clear progress indication
yield f"Processing batch {batch_num}/{total_batches}\n"
yield f"Imported {count} records in {duration:.1f}s\n"

# Less useful - too verbose
yield f"Processing record {i}\n"  # Don't yield for every single item
```

### 2. Include Newlines

Add newlines to output for readability:

```python
yield "Step 1 complete\n"  # Good - newline included
yield "Step 2 complete\n"
```

### 3. Final Summary

End with a summary message:

```python
def my_task():
    yield "Working...\n"
    yield "Still working...\n"
    yield "Done! Processed 1000 items in 45 seconds."  # Summary
```

### 4. Handle Errors in Generator

```python
def safe_generator_task(items):
    for i, item in enumerate(items):
        try:
            result = process(item)
            yield f"Item {i}: {result}\n"
        except Exception as e:
            yield f"Item {i}: ERROR - {e}\n"
            # Continue processing or re-raise based on requirements

    yield "Processing complete"
```

## Comparison: Generator vs Regular Function

| Aspect | Regular Function | Generator Function |
|--------|------------------|-------------------|
| Output | Single return value | Accumulated yields |
| Progress | Not visible until complete | Real-time updates |
| Signals | `before_job`, `on_success/failure` | + `before_loop`, `after_loop` |
| Memory | May need to hold all data | Can process incrementally |
| Use case | Quick tasks, single result | Long tasks, progress tracking |

## Next Steps

- Handle [errors](errors.md) in generator tasks
- Use [signals](signals.md) to react to `before_loop` and `after_loop`
