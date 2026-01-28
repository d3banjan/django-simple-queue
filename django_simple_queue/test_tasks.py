def return_hello(**kwargs):
    return "hello"


def gen_abc(**kwargs):
    yield "a"
    yield "b"
    yield "c"


def raise_error(**kwargs):
    raise ValueError("test error")


def print_and_return(**kwargs):
    print("log line from stdout")
    import logging

    logging.info("log line from logging")
    import sys

    print("log line from stderr", file=sys.stderr)
    return "result"


def sleep_task(seconds=1, **kwargs):
    """Task that sleeps for testing timeout functionality."""
    import time

    time.sleep(seconds)
    return f"slept for {seconds} seconds"
