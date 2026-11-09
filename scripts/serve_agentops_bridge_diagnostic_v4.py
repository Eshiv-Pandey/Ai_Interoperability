"""Add passive startup sampling while preserving the v2/v3 exit observers."""
import argparse
from pathlib import Path

from agentops_interpreter_exit_diagnostics_v1 import InterpreterExitObserver
from agentops_startup_diagnostics_v1 import StartupObserver


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--exit-watchdog-seconds', type=float, default=5.0)
    parser.add_argument('--startup-stack-seconds', type=float, default=5.0)
    args = parser.parse_args(argv)
    import agentops_native_probe_v2 as evidence
    target = evidence.within(args.output, evidence.WORKSPACE / 'runs/agentops-http-control')
    startup = StartupObserver(target / 'startup-diagnostics', target / 'service-ready.json',
                              interval_seconds=args.startup_stack_seconds)
    observer = None
    boundary, outcome = 'service_imports', 'raised'
    try:
        observer = InterpreterExitObserver(target / 'interpreter-exit-diagnostics',
                                           watchdog_seconds=args.exit_watchdog_seconds)
        # Both observers are installed before service and application imports.
        from agentops_shutdown_diagnostics_v2 import run_observed
        from serve_agentops_bridge_v1 import serve

        async def observed_service():
            try:
                return await serve(target, args.port)
            finally:
                # A normal stop finishes before v2 starts asyncio-teardown
                # sampling. If a diagnostic write itself is stuck, stop() is
                # bounded and keeps its raw descriptors owned by the daemon.
                startup.stop('service_coroutine_finished')

        boundary = 'asyncio_observer'
        result = run_observed(observed_service, target / 'shutdown-diagnostics')
        outcome = 'returned'
        return result
    finally:
        startup.stop('wrapper_finished')
        if observer is not None:
            observer.arm(boundary=boundary, outcome=outcome)


if __name__ == '__main__':
    main()
