"""Freeze the tested protocol control and inspected runtime before execution."""
from datetime import datetime, timezone
import json
from pathlib import Path

import agentops_protocol_preparation_v2 as preparation

ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT / preparation.SEAL_RELATIVE
    if target.exists():
        raise FileExistsError('Preserve the existing preparation seal')
    if (ROOT / 'runs/agentops-native-eligibility/linux-protocol-v9').exists():
        raise FileExistsError('Cannot freeze after protocol execution')
    software = json.loads((ROOT / preparation.PREPARATION_RELATIVE / 'result.json').read_bytes())
    if (software.get('schema_version') != 'agentops-protocol-software-preparation/2'
            or software.get('returncode') != 0 or software.get('inputs_unchanged') is not True
            or software.get('application_execution_performed') is not False):
        raise ValueError('Successful, unchanged software preparation required')
    preparation.verify_records(ROOT, software['inputs'], preparation.SOFTWARE_INPUT_PATHS)
    prior = json.loads((ROOT / preparation.PRIOR_RELATIVE / 'result.json').read_bytes())
    if prior['status'] != 'native_and_http_controls_passed':
        raise ValueError('Passed native/HTTP prerequisite required')
    inspection = json.loads((ROOT / preparation.INSPECTION_RELATIVE).read_bytes())
    record = lambda name: preparation.file_record(ROOT, name)
    seal = {
        'schema_version': preparation.SCHEMA,
        'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
        'launch_inputs': [record(name) for name in preparation.LAUNCH_PATHS],
        'prerequisites': [record(name) for name in preparation.PREREQUISITE_PATHS],
        'runtime_sources': inspection['modules'],
        'artifacts': [record(name) for name in preparation.ARTIFACT_PATHS],
        'prior_result': record(preparation.PRIOR_RELATIVE + '/result.json'),
        'prior_export': record(preparation.PRIOR_RELATIVE + '/export-manifest.json'),
        'prior_parent_check': record(preparation.PARENT_CHECK_RELATIVE),
        'preflight_manifest': record(preparation.PREFLIGHT_RELATIVE),
        'runtime_source_inspection': record(preparation.INSPECTION_RELATIVE),
        'application_execution_performed': False,
        'live_model_calls': 0,
        'research_gate_credit_added': 0,
        'scope': 'Two native protocol fixture controls only; no unchanged bridge or scientific qualification',
    }
    preparation.validate_seal(ROOT, seal, prior)
    with target.open('x', encoding='utf-8') as stream:
        json.dump(seal, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'status': 'sealed_not_executed', 'path': str(target),
                      'runtime_sources': len(seal['runtime_sources'])}))


if __name__ == '__main__':
    main()
