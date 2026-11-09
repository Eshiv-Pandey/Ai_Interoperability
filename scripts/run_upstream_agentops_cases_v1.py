"""CLI for the gated native AgentOps source-case runner."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from interoperability.upstream_agentops_native_runner_v1 import main

if __name__ == "__main__":
    raise SystemExit(main())
