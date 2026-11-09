"""Observe asyncio teardown without changing its cancellation or exit behavior.

This helper starts no application, sends no signal and performs no cleanup.
It records stack locations only, never frame locals or coroutine arguments.
Use in a separately specified diagnostic deployment, never to replace v10.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import faulthandler
import json
import math
from pathlib import Path
import sys
import threading
import traceback


def now():
    return datetime.now(timezone.utc).isoformat()


def stack_locations(frame):
    return [{'file': item.filename, 'line': item.lineno, 'function': item.name}
            for item in traceback.extract_stack(frame)]


def thread_state():
    frames = sys._current_frames()
    return [{'ident': thread.ident, 'daemon': thread.daemon,
             'alive': thread.is_alive(),
             'stack': stack_locations(frames[thread.ident]) if thread.ident in frames else []}
            for thread in threading.enumerate()]


def task_state():
    current = asyncio.current_task()
    rows = []
    for task in asyncio.all_tasks():
        rows.append({'current': task is current, 'done': task.done(),
                     'cancelling': task.cancelling(),
                     'stack': [{'file': frame.f_code.co_filename,
                                'line': frame.f_lineno,
                                'function': frame.f_code.co_name}
                               for frame in task.get_stack(limit=32)]})
    return rows


def run_observed(coroutine_factory, output: Path, *, watchdog_seconds=5.0):
    """Run with ordinary asyncio.run and retain observations around its return.

    The one-shot stack dump is armed only after the supplied coroutine returns
    or raises. It diagnoses cancellation/executor/interpreter teardown stalls;
    it cannot diagnose a stall before that boundary. No timeout is extended.
    Existing faulthandler global configuration must be owned by this process.
    """
    if (not isinstance(watchdog_seconds, (int, float)) or isinstance(watchdog_seconds, bool)
            or not math.isfinite(watchdog_seconds) or watchdog_seconds <= 0):
        raise ValueError('Require a finite positive diagnostic delay')
    output.mkdir(exist_ok=False)
    events = output / 'lifecycle.jsonl'
    errors = []

    def emit(phase, **details):
        with events.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'phase': phase, 'at_utc': now(), **details}) + '\n')

    def observe(phase, **details):
        # Diagnostics must not replace an application exception or prevent
        # normal asyncio teardown when a diagnostic filesystem write fails.
        try:
            emit(phase, **details)
        except Exception as error:
            errors.append(f'{phase}: {type(error).__name__}: {error}')

    with (output / 'teardown-stacks.txt').open('x', encoding='utf-8') as trace:
        async def wrapped():
            try:
                return await coroutine_factory()
            finally:
                try:
                    observe('coroutine_finished', tasks=task_state(), threads=thread_state())
                    faulthandler.dump_traceback_later(watchdog_seconds, repeat=False, file=trace)
                    observe('teardown_watchdog_armed', seconds=watchdog_seconds)
                except Exception as error:
                    errors.append(f'arm_watchdog: {type(error).__name__}: {error}')

        outcome = 'raised'
        observe('asyncio_run_entered')
        try:
            result = asyncio.run(wrapped())
            outcome = 'returned'
            return result
        finally:
            faulthandler.cancel_dump_traceback_later()
            observe('asyncio_run_exited', outcome=outcome, threads=thread_state(),
                    diagnostic_errors=list(errors))

