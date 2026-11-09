"""Prospective bounded cases; successful controls never imply a C1 result."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RATIONALE = 'Inventory is down and INC-002 matches the service-down runbook.'
PORT = 18764
BRIDGE_PORT = 18765
LIMITS = {'request_timeout_ms': 15000, 'poll_interval_ms': 100,
          'poll_attempts': 30, 'total_timeout_ms': 180000,
          'max_response_bytes': 33554432}
CASES = {}
for profile in ('amir-sync', 'amir-stream', 'mg-poll'):
    for representation in ('literal', 'json-text', 'data'):
        case_id = 'N' + str(len(CASES) + 1)
        CASES[case_id] = {'case_id': case_id, 'kind': 'native',
                          'profile': profile, 'representation': representation,
                          'native_prerequisites': []}
for profile in ('mg-raw-no-header', 'mg-raw-header'):
    case_id = 'N' + str(len(CASES) + 1)
    CASES[case_id] = {'case_id': case_id, 'kind': 'native',
                      'profile': profile, 'representation': 'data',
                      'native_prerequisites': []}
for number, prerequisites in enumerate((['N3'], ['N6'], ['N3'], ['N9'],
                                       ['N9'], ['N9'], ['N9', 'N11']), 1):
    case_id = 'B' + str(number)
    CASES[case_id] = {'case_id': case_id, 'kind': 'bridge', 'arm': case_id,
                      'native_prerequisites': prerequisites}


def bridge_environment(case):
    """A fixed credential-free CLI environment, with isolated state/config."""
    return {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'TZ': 'UTC',
            'A2A_ALLOW_WRITES': '1', 'A2A_CHANNEL': '0', 'A2A_MAX_RETRIES': '0',
            'A2A_CONFIG': str(case / 'absent-bridge-config.json'),
            'A2A_STATE_DIR': str(case / 'bridge-state'),
            'TMPDIR': str(case / 'temp')}


def client_config(definition, case, runtime_root):
    base = {'output_dir': str(case / 'client'), 'agent_base_url': f'http://127.0.0.1:{PORT}/',
            'rationale': RATIONALE, 'limits': LIMITS}
    if definition['kind'] == 'native':
        return {**base, 'schema_version': 'agentops-native-profile-client-config/1',
                'profile': definition['profile'], 'representation': definition['representation'],
                'runtime_root': str(runtime_root)}
    arm = definition['arm']
    amir = arm in ('B1', 'B2', 'B3')
    package = runtime_root / 'external' / ('a2a-to-mcp' if amir else 'mcp-a2a')
    argv = [str(package / 'dist/cli.js')]
    if amir:
        argv.extend(['--config', str(case / 'agents.json'), '--host', '127.0.0.1', '--port', str(BRIDGE_PORT)])
    elif arm in ('B6', 'B7'):
        argv = [str(ROOT / 'scripts/agentops_mgcrea_embed_v1.mjs'),
                '--workspace', str(runtime_root), '--mode', 'version-header' if arm == 'B7' else 'passthrough',
                '--origin', base['agent_base_url']]
    return {**base, 'schema_version': 'agentops-bridge-client-config/1', 'arm': arm,
            'agent_alias': 'agentops', 'amir_endpoint': f'http://127.0.0.1:{BRIDGE_PORT}/mcp',
            'bridge': {'command': '/usr/bin/node', 'args': argv, 'cwd': str(runtime_root),
                       'env': bridge_environment(case)}}
