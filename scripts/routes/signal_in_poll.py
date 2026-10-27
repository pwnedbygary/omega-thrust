#!/usr/bin/env python3
"""Run a route script with a signal sent inside its child's first Popen.poll().

test_run_route.py and test_beetle_route.py run run_route.py and beetle_route.py
through this script. It sends the signal right after poll() has taken the
child's waitpid lock (CPython's Popen._waitpid_lock) and before the try that
releases the lock. An exception raised by the script's signal handler at that
point would leave the lock taken, and the script's later wait for the child
would block forever.

The script starts with the handlers that a terminal leaves, whatever the tests
inherited: SIGINT raises KeyboardInterrupt, and SIGTERM and SIGHUP have their
default action.

Usage: python3 -B signal_in_poll.py SIGNAL SCRIPT [ARG...], where SIGNAL is a
signal's name, such as SIGTERM.
"""
import os
import runpy
import signal
import subprocess
import sys


class SignalOnFirstAcquire:
    """A lock that sends a signal to this process once, right after it is first taken."""

    def __init__(self, lock, signum):
        self.lock = lock
        self.signum = signum

    def acquire(self, blocking=True, timeout=-1):
        taken = self.lock.acquire(blocking, timeout)
        if taken and self.signum is not None:
            signum, self.signum = self.signum, None
            os.kill(os.getpid(), signum)
        return taken

    def release(self):
        self.lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc_info):
        self.release()


def main():
    signum = signal.Signals[sys.argv[1]]
    script = os.path.abspath(sys.argv[2])

    class Popen(subprocess.Popen):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._waitpid_lock = SignalOnFirstAcquire(self._waitpid_lock, signum)

    signal.signal(signal.SIGINT, signal.default_int_handler)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    signal.signal(signal.SIGHUP, signal.SIG_DFL)
    subprocess.Popen = Popen
    sys.argv = sys.argv[2:]
    sys.path.insert(0, os.path.dirname(script))
    runpy.run_path(script, run_name="__main__")


if __name__ == "__main__":
    main()
