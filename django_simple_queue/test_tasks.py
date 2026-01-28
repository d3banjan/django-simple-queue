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
