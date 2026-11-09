"""Preserve the v2 asyncio observer and add passive interpreter-exit tracing.

No application or cleanup behavior changes. Both diagnostic directories are
required evidence; only the coordinator's process receipt can prove clean exit.
"""
import argparse
from pathlib import Path

from agentops_interpreter_exit_diagnostics_v1 import InterpreterExitObserver


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--exit-watchdog-seconds', type=float, default=5.0)
    args = parser.parse_args(argv)
    # This helper imports standard-library code only and validates the same
    # output subtree as v2, before allocating a diagnostic directory.
    import agentops_native_probe_v2 as evidence
    target = evidence.within(args.output, evidence.WORKSPACE / 'runs/agentops-http-control')
    observer = InterpreterExitObserver(target / 'interpreter-exit-diagnostics',
                                       watchdog_seconds=args.exit_watchdog_seconds)
    boundary, outcome = 'service_imports', 'raised'
    try:
        # The late atexit marker is installed before service/application imports.
        from agentops_shutdown_diagnostics_v2 import run_observed
        from serve_agentops_bridge_v1 import serve
        boundary = 'asyncio_observer'
        result = run_observed(lambda: serve(target, args.port), target / 'shutdown-diagnostics')
        outcome = 'returned'
        return result
    finally:
        # v2 has already cancelled its watchdog if it was entered. This new
        # watchdog remains armed after this function and the module return.
        observer.arm(boundary=boundary, outcome=outcome)


if __name__ == '__main__':
    main()

