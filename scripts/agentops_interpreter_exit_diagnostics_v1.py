"""Passive, process-lifetime diagnostics after the asyncio observer finishes.

Install before application imports and call ``arm`` after the v2 asyncio
observer returns or raises. That order preserves v2's process-global watchdog:
this watchdog starts only after v2 has cancelled its own watchdog. Neither this
module nor its atexit callbacks cancel the new watchdog or terminate the process.

The two raw, non-inheritable descriptors are deliberately owned until process
death. No Python file finalizer can close/recycle the traceback descriptor while
faulthandler uses it. Setup failures close any descriptors already acquired;
one observer per dedicated process prevents accumulating lifetime descriptors.

The markers bracket callbacks registered between installation and ``arm``, not
all possible atexit callbacks. Python waits for non-daemon threads before atexit.
The watchdog can observe that wait, atexit, and subsequent finalization while
CPython keeps faulthandler operational; it cannot observe past faulthandler's
own runtime teardown. Tracebacks contain Python locations, not locals or a
complete native stack. Markers and empty traces never prove process exit; the
owning coordinator's process receipt remains authoritative.
"""
from __future__ import annotations

import atexit
import faulthandler
import json
import math
import os
from pathlib import Path
import time


_ACTIVE_OBSERVER = None


class InterpreterExitObserver:
    """One observer in a dedicated service process; not an embedding API."""

    def __init__(self, output: Path, *, watchdog_seconds: float = 5.0):
        global _ACTIVE_OBSERVER
        if (type(watchdog_seconds) not in (int, float)
                or not math.isfinite(watchdog_seconds) or watchdog_seconds <= 0):
            raise ValueError('Require a finite positive diagnostic delay')
        if _ACTIVE_OBSERVER is not None:
            raise RuntimeError('An interpreter-exit observer already owns this process')
        self.pid = os.getpid()
        self.seconds = watchdog_seconds
        self.errors = []
        self.sequence = 0
        self.handoff_started = False
        self.watchdog_armed = False
        self.trace_fd = self.events_fd = None
        # Retain callable references for the late atexit callback. The trace
        # descriptor has no file object, weakref finalizer, or __del__ method.
        self._write = os.write
        self._monotonic_ns = time.monotonic_ns
        self._time_ns = time.time_ns
        self._dumps = json.dumps
        self._getpid = os.getpid
        self._arm_watchdog = faulthandler.dump_traceback_later
        self._register = atexit.register
        output = Path(output)
        output.mkdir(exist_ok=False)
        acquired = []
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            flags |= getattr(os, 'O_CLOEXEC', 0) | getattr(os, 'O_BINARY', 0)
            for name in ('interpreter-exit-stacks.txt', 'lifecycle.jsonl'):
                descriptor = os.open(output / name, flags, 0o600)
                acquired.append(descriptor)
                os.set_inheritable(descriptor, False)
            self.trace_fd, self.events_fd = acquired
            # Registered before app/SDK imports, so it runs after callbacks
            # those imports register. It is not claimed to be globally last.
            self._register(self._late_atexit)
        except BaseException:
            for descriptor in acquired:
                os.close(descriptor)
            self.trace_fd = self.events_fd = None
            raise
        _ACTIVE_OBSERVER = self
        self._observe('interpreter_exit_observer_installed')

    def _guarded(self, stage, action):
        try:
            action()
            return True
        except Exception as error:
            # Record type only: exception strings may contain application data.
            self.errors.append({'stage': stage, 'error_type': type(error).__name__})
            return False

    def _observe(self, phase, **details):
        if self._getpid() != self.pid:
            return

        def write():
            row = {'schema_version': 'agentops-interpreter-exit-event/1',
                   'sequence': self.sequence + 1, 'pid': self.pid,
                   'monotonic_ns': self._monotonic_ns(),
                   'at_epoch_ns': self._time_ns(), 'phase': phase,
                   'watchdog_armed': self.watchdog_armed,
                   **details, 'diagnostic_errors': list(self.errors)}
            remaining = self._dumps(row, allow_nan=False).encode('utf-8') + b'\n'
            while remaining:
                written = self._write(self.events_fd, remaining)
                if written <= 0:
                    raise OSError('Diagnostic descriptor accepted no bytes')
                remaining = remaining[written:]
            self.sequence += 1
        self._guarded('write_' + phase, write)

    def arm(self, *, boundary='asyncio_observer', outcome='returned'):
        """Hand off after v2 finishes; preserve any caller result/exception.

        ``service_imports`` reports a failed import before v2 was entered. It
        does not falsely assert that asyncio ran. Operational diagnostic errors
        are recorded and never replace the service outcome.
        """
        if boundary not in ('asyncio_observer', 'service_imports'):
            raise ValueError('Unknown interpreter-exit boundary')
        if outcome not in ('returned', 'raised'):
            raise ValueError('Unknown entrypoint outcome')
        if self._getpid() != self.pid or self.handoff_started:
            raise RuntimeError('Interpreter-exit handoff requires its owner once')
        self.handoff_started = True
        self._observe('entrypoint_boundary', boundary=boundary, outcome=outcome)
        self._guarded('register_early_atexit', lambda: self._register(self._early_atexit))

        def start():
            self._arm_watchdog(self.seconds, repeat=True, file=self.trace_fd, exit=False)
            self.watchdog_armed = True
        if self._guarded('arm_interpreter_exit_watchdog', start):
            self._observe('interpreter_exit_watchdog_armed', seconds=self.seconds,
                          repeat=True, exit=False)
        else:
            self._observe('interpreter_exit_watchdog_unavailable')

    def _early_atexit(self):
        self._observe('atexit_early_boundary')

    def _late_atexit(self):
        self._observe('atexit_late_boundary')

