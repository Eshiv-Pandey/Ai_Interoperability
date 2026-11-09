"""Separately sealed diagnostic deployment; the v10 service routine is unchanged."""
import argparse
from pathlib import Path

import agentops_native_probe_v2 as evidence
from agentops_shutdown_diagnostics_v2 import run_observed
from serve_agentops_bridge_v1 import serve


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    args = parser.parse_args()
    target = evidence.within(args.output, evidence.WORKSPACE / 'runs/agentops-http-control')
    run_observed(lambda: serve(target, args.port), target / 'shutdown-diagnostics')
