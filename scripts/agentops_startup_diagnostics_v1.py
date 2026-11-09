"""Passive readiness observation on a dedicated daemon, with independent dumps.

No dump_traceback_later timer is installed, cancelled or replaced. A separate
daemon calls dump_traceback into its own raw non-inheritable descriptor while
readiness is absent. The owner requests stopping at coroutine/wrapper exit;
readiness also stops the monitor. No task, signal, application deadline or exit
status is changed. Python stack locations are captured without frame locals.

The daemon must receive Python/GIL scheduling. Missing or delayed samples cannot
prove that startup was unstalled, and a sample location does not establish the
cause. A bounded stop wait never closes a descriptor while the daemon might
still write to it; a delayed daemon keeps ownership until it finishes or the OS
reclaims the process. Successful stopping closes both descriptors.
"""
from __future__ import annotations

import faulthandler
import json
import math
import os
from pathlib import Path
import threading
import time


# A Thread.start exception does not prove that its native thread never launched.
# Failed service construction exits this dedicated process; until then, retain
# ownership rather than risk recycling an fd a delayed daemon may still use.
_UNCONFIRMED_STARTS = []


class StartupObserver:
    def __init__(self, output: Path, readiness: Path, *, interval_seconds=5.0,
                 poll_seconds=0.05, stop_wait_seconds=1.0):
        for value in (interval_seconds, poll_seconds, stop_wait_seconds):
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError('Require finite positive startup observer intervals')
        if stop_wait_seconds > 5.0:
            raise ValueError('Startup observer stop wait must not exceed five seconds')
        self.pid = os.getpid()
        self.interval = interval_seconds
        self.poll_seconds = poll_seconds
        self.stop_wait_seconds = stop_wait_seconds
        self.errors = []
        self.sequence = 0
        self.captures = 0
        self._stop_reason = 'wrapper_finished'
        self._stop = threading.Event()
        self._done = threading.Event()
        self._trace_fd = self._events_fd = None
        self._exists = Path(readiness).exists
        self._write = os.write
        self._close = os.close
        self._dump = faulthandler.dump_traceback
        self._monotonic = time.monotonic
        self._monotonic_ns = time.monotonic_ns
        self._time_ns = time.time_ns
        self._dumps = json.dumps
        output = Path(output)
        output.mkdir(exist_ok=False)
        acquired = []
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            flags |= getattr(os, 'O_CLOEXEC', 0) | getattr(os, 'O_BINARY', 0)
            for name in ('startup-stacks.txt', 'lifecycle.jsonl'):
                descriptor = os.open(output / name, flags, 0o600)
                acquired.append(descriptor)
                os.set_inheritable(descriptor, False)
            self._trace_fd, self._events_fd = acquired
        except BaseException:
            for descriptor in acquired:
                os.close(descriptor)
            raise
        # This is the only lifecycle write by the constructing thread. After
        # start(), the daemon exclusively owns logging, dumps and descriptor
        # closure; stop() only sets an Event and performs a bounded join.
        self._first_capture = self._monotonic() + self.interval
        self._observe('startup_observer_armed', interval_seconds=interval_seconds,
                      poll_seconds=poll_seconds, capture_backend='daemon_dump_traceback')
        try:
            self._thread = threading.Thread(target=self._watch, name='agentops-startup-observer', daemon=True)
        except BaseException as error:
            self.errors.append({'stage': 'construct_daemon', 'error_type': type(error).__name__})
            # start() has never been called, so no daemon can own the fds.
            self._finish('daemon_construction_failed')
            raise
        try:
            self._thread.start()
        except BaseException as error:
            self.errors.append({'stage': 'start_daemon', 'error_type': type(error).__name__})
            self._stop_reason = 'daemon_start_failed'
            self._stop.set()
            # Even ident/is_alive cannot prove that a newly launched thread
            # will not enter _watch later. Only _watch may close these fds now.
            _UNCONFIRMED_STARTS.append(self)
            raise

    def _write_all(self, descriptor, data):
        while data:
            size = self._write(descriptor, data)
            if size <= 0:
                raise OSError('Diagnostic descriptor accepted no bytes')
            data = data[size:]

    def _observe(self, phase, **details):
        try:
            row = {'schema_version': 'agentops-startup-event/1', 'sequence': self.sequence + 1,
                   'pid': self.pid, 'monotonic_ns': self._monotonic_ns(),
                   'at_epoch_ns': self._time_ns(), 'phase': phase,
                   **details, 'diagnostic_errors': list(self.errors)}
            self._write_all(self._events_fd, self._dumps(row, allow_nan=False).encode('utf-8') + b'\n')
            self.sequence += 1
        except Exception as error:
            self.errors.append({'stage': 'write_' + phase, 'error_type': type(error).__name__})

    def _capture(self):
        self.captures += 1
        tick = self._monotonic_ns()
        self._observe('startup_stack_capture_started', capture=self.captures, capture_monotonic_ns=tick)
        try:
            header = f'Startup traceback {self.captures}; pid={self.pid}; monotonic_ns={tick}\n'
            self._write_all(self._trace_fd, header.encode('ascii'))
            self._dump(file=self._trace_fd, all_threads=True)
        except Exception as error:
            self.errors.append({'stage': 'dump_startup_stack', 'error_type': type(error).__name__})
            self._observe('startup_stack_capture_failed', capture=self.captures)
        else:
            self._observe('startup_stack_capture_completed', capture=self.captures)

    def _finish(self, reason):
        # Only the daemon (or constructor before start() was called) closes
        # its descriptors. In particular, a timed-out stop() never recycles one.
        try:
            self._close(self._trace_fd)
        except OSError as error:
            self.errors.append({'stage': 'close_startup_trace', 'error_type': type(error).__name__})
        self._trace_fd = None
        self._observe('startup_observer_stopped', reason=reason, captures=self.captures)
        try:
            self._close(self._events_fd)
        except OSError as error:
            self.errors.append({'stage': 'close_startup_events', 'error_type': type(error).__name__})
        self._events_fd = None
        self._done.set()

    def _watch(self):
        reason = 'observer_failed'
        self._observe('startup_monitor_started')
        next_capture = self._first_capture
        try:
            while True:
                if self._exists():
                    self._observe('readiness_observed')
                    reason = 'readiness_observed'
                    break
                if self._stop.is_set():
                    reason = self._stop_reason
                    break
                now = self._monotonic()
                if now >= next_capture:
                    self._capture()
                    next_capture = self._monotonic() + self.interval
                self._stop.wait(min(self.poll_seconds, max(0.0, next_capture - self._monotonic())))
        except Exception as error:
            self.errors.append({'stage': 'startup_monitor', 'error_type': type(error).__name__})
        finally:
            self._finish(reason)

    def stop(self, reason='wrapper_finished'):
        """Request stopping and wait briefly; never cancel, signal or force exit."""
        if reason not in ('wrapper_finished', 'service_coroutine_finished'):
            raise ValueError('Unknown startup observer stop boundary')
        if not self._stop.is_set():
            self._stop_reason = reason
        self._stop.set()
        try:
            if self._thread.ident != threading.get_ident():
                self._thread.join(timeout=self.stop_wait_seconds)
        except Exception as error:
            self.errors.append({'stage': 'join_startup_monitor', 'error_type': type(error).__name__})
            return False
        if self._thread.is_alive():
            self.errors.append({'stage': 'join_startup_monitor', 'error_type': 'StopWaitExpired'})
            return False
        return self._done.is_set()

