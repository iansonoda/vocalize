import sys
import threading


_STDOUT_LOCK = threading.Lock()
_STDERR_LOCK = threading.Lock()


def emit_stdout(message):
    with _STDOUT_LOCK:
        sys.stdout.write(f"{message}\n")
        sys.stdout.flush()


def emit_stderr(message):
    with _STDERR_LOCK:
        sys.stderr.write(f"{message}\n")
        sys.stderr.flush()
