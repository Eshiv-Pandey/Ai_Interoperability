"""Bounded cleanup of one receipt-owned Linux session/process group.

The caller supplies the recorded group ID and exact allowed launch argv values.
Only /proc stat membership is inspected outside that group; unrelated command
lines are never read. No signal is sent unless every observed group member is
in the owned session and has an explicitly allowed command line.
"""
from __future__ import annotations

import os
from pathlib import Path
import signal
import sys
import time

_PROC_ROOT = Path('/proc')
_TERM_WAIT_SECONDS = 2.0
_KILL_WAIT_SECONDS = 3.0
_POLL_SECONDS = 0.05


def _parse_stat(raw):
    # comm is parenthesized and may itself contain spaces and parentheses.
    opening, closing = raw.find('('), raw.rfind(')')
    if opening < 1 or closing <= opening:
        raise ValueError('Malformed process stat')
    pid = int(raw[:opening].strip())
    fields = raw[closing + 1:].split()
    if len(fields) < 20:
        raise ValueError('Truncated process stat')
    return {'pid': pid, 'state': fields[0], 'pgrp': int(fields[2]),
            'session': int(fields[3]), 'starttick': int(fields[19])}


def _scan_group(pgid):
    """Read exact argv only for members of pgid, including an orphaned group."""
    members, errors = [], []
    try:
        directories = sorted((path for path in _PROC_ROOT.iterdir() if path.name.isdigit()),
                             key=lambda path: int(path.name))
    except OSError as error:
        return [], [f'Cannot enumerate process membership: {type(error).__name__}: {error}']
    for directory in directories:
        try:
            before = _parse_stat((directory / 'stat').read_text(encoding='utf-8', errors='surrogateescape'))
            if before['pid'] != int(directory.name):
                raise ValueError('Process stat PID/path mismatch')
            if before['pgrp'] != pgid:
                continue
            argv = [os.fsdecode(value) for value in (directory / 'cmdline').read_bytes().rstrip(b'\0').split(b'\0')]
            if argv == ['']:
                argv = []
            after = _parse_stat((directory / 'stat').read_text(encoding='utf-8', errors='surrogateescape'))
            if any(before[key] != after[key] for key in ('pid', 'pgrp', 'session', 'starttick')):
                raise ValueError('Owned process identity changed during observation')
            members.append({**after, 'argv': argv})
        except (FileNotFoundError, ProcessLookupError):
            # A process that disappears while inspected supplies no live member.
            continue
        except (OSError, ValueError) as error:
            errors.append(f'PID {directory.name} membership uncertain: {type(error).__name__}: {error}')
    return members, errors


def finish_owned_group(pgid, allowed_argvs):
    """Inspect after parent exit; terminate only a fully recognized owned group.

    A normal empty group receives no signals. A recognized surviving group gets
    SIGTERM, at most two seconds of polling, then SIGKILL and at most three more
    seconds. An unknown argv, session, identity, or membership read fails closed.
    Any sent signal sets forced_cleanup, even when termination succeeds.
    """
    report = {'schema_version': 'agentops-owned-process-group/1', 'pgid': pgid,
              'initially_empty': False, 'final_empty': False, 'forced_cleanup': False,
              'members': [], 'final_members': [], 'snapshots': [], 'signals': [], 'errors': []}
    if (sys.platform != 'linux' or type(pgid) is not int or pgid <= 1
            or pgid == getattr(os, 'getpgrp', lambda: None)()):
        report['errors'].append('Require a recorded Linux process group other than the caller group')
        return report
    if (not isinstance(allowed_argvs, (list, tuple)) or not allowed_argvs
            or any(not isinstance(argv, (list, tuple)) or not argv
                   or any(type(value) is not str or not value or '\0' in value for value in argv)
                   for argv in allowed_argvs)):
        report['errors'].append('Require nonempty exact allowed launch argv lists')
        return report
    allowed = {tuple(argv) for argv in allowed_argvs}
    identities = {}

    def observe(phase):
        members, errors = _scan_group(pgid)
        report['snapshots'].append({'phase': phase, 'monotonic_ns': time.monotonic_ns(),
                                    'members': members, 'errors': errors})
        report['final_members'] = members
        report['errors'].extend(f'{phase}: {value}' for value in errors)
        for member in members:
            if member['pgrp'] != pgid or member['session'] != pgid:
                report['errors'].append(f"{phase}: PID {member['pid']} is not in the owned session/group")
            if tuple(member['argv']) not in allowed:
                report['errors'].append(f"{phase}: PID {member['pid']} has unknown argv")
            prior = identities.get(member['pid'])
            if prior is not None and prior != member['starttick']:
                report['errors'].append(f"{phase}: PID {member['pid']} starttick changed")
            identities[member['pid']] = member['starttick']
        report['final_empty'] = not members and not report['errors']
        return members

    def send_group(signum, phase):
        # Re-observe immediately before each signal; a newly arrived unknown
        # process must not be killed because earlier members were recognized.
        if not observe('before_' + phase) or report['errors']:
            return False
        try:
            os.killpg(pgid, signum)
            report['forced_cleanup'] = True
            report['signals'].append({'signal': 'SIGTERM' if signum == signal.SIGTERM else 'SIGKILL',
                                       'monotonic_ns': time.monotonic_ns(), 'sent': True})
            return True
        except ProcessLookupError:
            observe('disappeared_before_' + phase)
        except OSError as error:
            report['errors'].append(f'{phase}: {type(error).__name__}: {error}')
        return False

    def await_empty(seconds, phase):
        deadline = time.monotonic() + seconds
        while True:
            if not observe(phase) or report['errors']:
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(_POLL_SECONDS, remaining))

    initial = observe('initial')
    report['members'] = initial
    report['initially_empty'] = not initial and not report['errors']
    if report['initially_empty'] or report['errors']:
        return report
    if not send_group(signal.SIGTERM, 'sigterm'):
        return report
    await_empty(_TERM_WAIT_SECONDS, 'after_sigterm')
    if report['final_empty'] or report['errors']:
        return report
    if not send_group(signal.SIGKILL, 'sigkill'):
        return report
    await_empty(_KILL_WAIT_SECONDS, 'after_sigkill')
    if not report['final_empty'] and not report['errors']:
        report['errors'].append('Owned process group survived bounded SIGTERM/SIGKILL cleanup')
    return report
