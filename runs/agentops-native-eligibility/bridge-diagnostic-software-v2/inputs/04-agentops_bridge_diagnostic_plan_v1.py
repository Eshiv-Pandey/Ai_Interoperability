"""New diagnostic allocation; original v10 profiles, fresh directories and state."""
from copy import deepcopy
from pathlib import Path
import agentops_bridge_plan_v1 as original

ROOT = Path(__file__).resolve().parents[1]
PORT, BRIDGE_PORT = original.PORT, original.BRIDGE_PORT
RATIONALE, LIMITS = original.RATIONALE, original.LIMITS
CASE_PREFIX = 'runs/agentops-http-control/bridge-diagnostic-v1-'
CASES = {name: deepcopy(original.CASES[name]) for name in ('N11', 'B6', 'B7')}
for name in ('B6', 'B7'):
    CASES[name]['native_prerequisites'] = ['N11']
bridge_environment = original.bridge_environment
client_config = original.client_config
