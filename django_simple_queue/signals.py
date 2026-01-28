import django.dispatch

before_job = django.dispatch.Signal()  # kwargs: task
on_success = django.dispatch.Signal()  # kwargs: task
on_failure = django.dispatch.Signal()  # kwargs: task, error
before_loop = django.dispatch.Signal()  # kwargs: task, iteration
after_loop = django.dispatch.Signal()  # kwargs: task, output, iteration
