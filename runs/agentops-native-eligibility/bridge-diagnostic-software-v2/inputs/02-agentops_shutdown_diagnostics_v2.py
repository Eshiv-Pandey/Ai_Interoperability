"""Process-bound, passive asyncio teardown diagnostics for a dedicated process.

Preserves v1. No application request, signal or additional cancellation occurs.
Stack locations exclude frame locals and user-controlled task/thread names.
The traceback watchdog covers asyncio teardown only, not later interpreter exit.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import faulthandler
import json
import math
import os
from pathlib import Path
import sys
import threading
import time
import traceback

# If cancellation fails, retain the descriptor so an armed watchdog cannot
# write to a descriptor recycled by unrelated code. This process owns it.
_UNRELEASED_TRACES = []


def thread_state():
    frames = sys._current_frames()
    return [{'ident': thread.ident, 'daemon': thread.daemon, 'alive': thread.is_alive(),
             'stack': [{'file': row.filename, 'line': row.lineno, 'function': row.name}
                       for row in traceback.extract_stack(frames[thread.ident])]
                      if thread.ident in frames else []}
            for thread in threading.enumerate()]


def task_state():
    current = asyncio.current_task()
    return [{'current': task is current, 'done': task.done(), 'cancelling': task.cancelling(),
             'stack': [{'file': frame.f_code.co_filename, 'line': frame.f_lineno,
                        'function': frame.f_code.co_name} for frame in task.get_stack(limit=32)]}
            for task in asyncio.all_tasks()]


def run_observed(coroutine_factory, output: Path, *, watchdog_seconds=5.0):
    if (not isinstance(watchdog_seconds, (int, float)) or isinstance(watchdog_seconds, bool)
            or not math.isfinite(watchdog_seconds) or watchdog_seconds <= 0):
        raise ValueError('Require a finite positive diagnostic delay')
    output.mkdir(exist_ok=False)
    trace = (output / 'teardown-stacks.txt').open('x', encoding='utf-8')
    errors, sequence = [], 0

    def guarded(stage, action, fallback=None):
        try:
            return action()
        except Exception as error:
            errors.append({'stage': stage, 'error_type': type(error).__name__})
            return fallback

    def observe(phase, **details):
        nonlocal sequence
        def write():
            nonlocal sequence
            row = {'schema_version': 'agentops-shutdown-event/2', 'sequence': sequence + 1,
                   'pid': os.getpid(), 'monotonic_ns': time.monotonic_ns(),
                   'at_utc': datetime.now(timezone.utc).isoformat(), 'phase': phase,
                   **details, 'diagnostic_errors': list(errors)}
            with (output / 'lifecycle.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(row) + '\n')
            sequence += 1
        guarded('write_' + phase, write)

    async def wrapped():
        try:
            return await coroutine_factory()
        finally:
            def arm():
                faulthandler.dump_traceback_later(watchdog_seconds, repeat=False, file=trace)
                return True
            if guarded('arm_watchdog', arm, False):
                observe('teardown_watchdog_armed', seconds=watchdog_seconds)
            tasks = guarded('task_snapshot', task_state)
            threads = guarded('coroutine_thread_snapshot', thread_state)
            observe('coroutine_finished',
                    **({'tasks': tasks} if tasks is not None else {}),
                    **({'threads': threads} if threads is not None else {}))

    observe('asyncio_run_entered')
    outcome = 'raised'
    try:
        result = asyncio.run(wrapped())
        outcome = 'returned'
        return result
    finally:
        def cancel():
            faulthandler.cancel_dump_traceback_later()
            return True
        cancelled = guarded('cancel_watchdog', cancel, False)
        threads = guarded('exit_thread_snapshot', thread_state)
        if cancelled:
            guarded('close_trace', trace.close)
        else:
            _UNRELEASED_TRACES.append(trace)
        observe('asyncio_run_exited', outcome=outcome,
                **({'threads': threads} if threads is not None else {}))

