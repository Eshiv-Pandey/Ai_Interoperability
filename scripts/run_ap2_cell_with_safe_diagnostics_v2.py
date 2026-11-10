"""Launch exactly one supplied actor command, print safe metadata, return its code."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from print_ap2_owned_cell_diagnostics_v2 import print_diagnostics


def run_once(cell, launcher_logs, command, printer=print_diagnostics):
    cell, launcher_logs = Path(cell).absolute(), Path(launcher_logs).absolute()
    if not command:
        raise ValueError('one_actor_command_required')
    launcher_logs.mkdir(parents=True, exist_ok=False)
    with (launcher_logs / 'stdout.txt').open('xb') as stdout, (launcher_logs / 'stderr.txt').open('xb') as stderr:
        result = subprocess.run(list(command), stdout=stdout, stderr=stderr, check=False)
    returncode = result.returncode
    try:
        printer(cell, returncode)
    except BaseException:
        try:
            print('{"kind":"owned_diagnostics","status":"printer_unavailable"}')
        except Exception:
            pass
    return returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cell', type=Path, required=True)
    parser.add_argument('--launcher-logs', type=Path, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    return run_once(args.cell, args.launcher_logs, command)


if __name__ == '__main__':
    raise SystemExit(main())
