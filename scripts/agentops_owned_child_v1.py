"""Reap one Popen-owned child before inspecting its remaining Linux group.

The preserved group helper explicitly requires parent exit. A timed-out child
must therefore be stopped and reaped first. This does not turn a forced exit
into a clean one, and never signals a process identified only by a loose PID.
"""
from __future__ import annotations

import math
import subprocess

from agentops_owned_process_v1 import finish_owned_group


def finish_owned_child(process, allowed_argvs, *, graceful_seconds=20.0,
                       terminate_seconds=2.0, kill_seconds=3.0):
    for value in (graceful_seconds, terminate_seconds, kill_seconds):
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError('Cleanup waits must be finite and nonnegative')
    if (not isinstance(process, subprocess.Popen) or type(process.pid) is not int
            or process.pid <= 1 or not isinstance(process.args, (list, tuple))
            or not allowed_argvs or not any(list(process.args) == list(argv) for argv in allowed_argvs)):
        raise ValueError('Require the actual Popen child and its exact allowed launch argv')
    report = {'schema_version': 'agentops-owned-child-finish/1', 'pid': process.pid,
              'argv': list(process.args), 'graceful_timeout': False,
              'signal_requests': [], 'returncode': None, 'reaped_before_group_check': False,
              'errors': [], 'owned_group': None}

    def wait(seconds):
        try:
            process.wait(timeout=seconds)
            return True
        except subprocess.TimeoutExpired:
            return False
        except Exception as error:
            report['errors'].append('wait: ' + type(error).__name__ + ': ' + str(error))
            return False

    def poll():
        try:
            return True, process.poll()
        except Exception as error:
            report['errors'].append('poll: ' + type(error).__name__ + ': ' + str(error))
            return False, None

    if not wait(graceful_seconds):
        report['graceful_timeout'] = process.returncode is None
        for name, action, seconds in (('SIGTERM', process.terminate, terminate_seconds),
                                      ('SIGKILL', process.kill, kill_seconds)):
            known, returncode = poll()
            if not known:
                report['errors'].append('Owned child state uncertain; further signals and group inspection withheld')
                return report
            if returncode is not None:
                break
            request = {'signal': name, 'method_returned': False,
                       'meaning': 'Popen signal method requested; not proof of OS delivery'}
            report['signal_requests'].append(request)
            try:
                action()
                request['method_returned'] = True
            except Exception as error:
                report['errors'].append(name + ': ' + type(error).__name__ + ': ' + str(error))
            if wait(seconds):
                break
    known, report['returncode'] = poll()
    if not known:
        report['errors'].append('Owned child exit is unconfirmed; group inspection withheld')
        return report
    if report['returncode'] is None:
        report['errors'].append('Owned child exit is unconfirmed; group inspection withheld')
        return report
    report['reaped_before_group_check'] = True
    try:
        report['owned_group'] = finish_owned_group(process.pid, allowed_argvs)
    except Exception as error:
        report['errors'].append('group: ' + type(error).__name__ + ': ' + str(error))
    return report
