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
