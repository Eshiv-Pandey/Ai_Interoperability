"""Post-capture inspection of v10 partial cases, with no application launch."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

import agentops_native_probe_v2 as evidence
from check_agentops_bridge_v1 import parse_asgi_exchange

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'runs/agentops-native-eligibility/linux-bridge-v10'
CASES = RUN / 'workspace/runs/agentops-http-control'
OUTPUT = ROOT / 'docs/research/source-evidence/agentops-bridge-gaps-v1'


def record(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def load(path):
    return json.loads(path.read_bytes())


def write(name, value):
    with (OUTPUT / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    OUTPUT.mkdir(exist_ok=False)
    paths = [RUN / 'result.json', RUN / 'export-manifest.json',
             Path(__file__), ROOT / 'scripts/agentops_native_probe_v2.py',
             ROOT / 'scripts/check_agentops_bridge_v1.py',
             ROOT / 'scripts/serve_agentops_bridge_v1.py',
             ROOT / 'scripts/agentops_bridge_control_v1.py']
    for name in ('B5', 'B6', 'B7'):
        paths.append(RUN / (name + '.json'))
        paths.extend(path for path in (CASES / ('bridge-v1-' + name)).rglob('*') if path.is_file())
    inputs = [record(path) for path in sorted(set(paths))]
    write('inputs.json', inputs)
    report = {'schema_version': 'agentops-bridge-gap-inspection/1', 'status': 'failed',
              'started_at_utc': datetime.now(timezone.utc).isoformat(),
              'application_requests': 0, 'live_model_calls': 0,
              'scientific_gate_credit_added': 0, 'strict_outcomes_changed': False}
    try:
        cases = {}
        for name in ('B5', 'B6', 'B7'):
            target = CASES / ('bridge-v1-' + name)
            checked = load(target / 'case-check.json')
            requests = []
            for folder in sorted((target / 'service/wire').iterdir()):
                parsed = parse_asgi_exchange(folder)
                request = parsed.get('request') or {}
                requests.append({'sequence': parsed['record']['sequence'],
                                 'method': request.get('method'), 'rpc_id': request.get('id'),
                                 'version_headers': [v for k, v in parsed['record']['request_headers']
                                                     if k.lower() == 'a2a-version'],
                                 'http_status': parsed['record']['response_status'],
                                 'errors': [row['error'] for row in parsed.get('responses', []) if 'error' in row]})
            cases[name] = {'public_bindings': checked['client']['public_bindings'],
                           'answer_attempted': checked['client']['answer_attempted'],
                           'outcome': checked['outcome'], 'observation_gaps': checked['observation_gaps'],
                           'requests': requests}
        report['cases'] = cases
        for name in ('B5', 'B6'):
            rows = cases[name]['requests']
            assert cases[name]['answer_attempted'] is False
            assert sum(row['method'] == 'SendMessage' for row in rows) == 1
            rejected = [row for row in rows if row['method'] == 'GetTask' and not row['version_headers']]
            assert len(rejected) == 1 and rejected[0]['http_status'] == 200
            assert [row['code'] for row in rejected[0]['errors']] == [-32009]
        target = CASES / 'bridge-v1-B7'
        service = target / 'service'
        result, outer = load(target / 'result.json'), load(RUN / 'B7.json')
        report['b7_shutdown'] = {
            'service_routine': load(service / 'service-result.json'),
            'service_returncode': result['service_returncode'],
            'forced_service_stop': result['forced_service_stop'],
            'cleanup_errors': result['cleanup_errors'],
            'controller_cleanup': result['service_group_cleanup'],
            'later_outer_cleanup': outer['owned_groups']['service'],
            'terminal_snapshot_present': (service / 'terminal.snapshot.json').exists(),
            'root_cause_established': False,
        }
        # Read a byte-preserving copy, so SQLite cannot create a sidecar in the
        # retained archive even if its original database used WAL mode.
        copied = OUTPUT / 'archived-database-copy'
        (copied / 'state').mkdir(parents=True)
        copies = []
        for suffix in ('', '-wal', '-shm'):
            source = service / ('state/incidents.db' + suffix)
            if source.exists():
                dest = copied / ('state/incidents.db' + suffix)
                shutil.copyfile(source, dest)
                copies.append({'source': record(source), 'copy_before_read': record(dest)})
        archive_state = evidence.database_snapshot(copied / 'state/incidents.db', copied, 'run')
        write('archived-database-snapshot.json', archive_state)
        report['archived_database'] = {
            'copies': copies,
            'equals_last_live_final_snapshot': archive_state == load(service / 'final.snapshot.json')['database'],
            'scope': 'Logical archived state only; not the missing historical terminal observation or clean exit',
        }
        report['inputs_unchanged'] = inputs == [record(path) for path in sorted(set(paths))]
        assert report['inputs_unchanged'], 'Archived inputs changed'
        report['status'] = 'retained_gap_evidence_inspected'
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    write('result.json', report)
    print(json.dumps({'status': report['status'], 'inputs': len(inputs),
                      'inputs_unchanged': report.get('inputs_unchanged'),
                      'archived_state_matches': report.get('archived_database', {}).get('equals_last_live_final_snapshot'),
                      'error': report.get('error')}))
    return report['status'] == 'retained_gap_evidence_inspected'


if __name__ == '__main__':
    raise SystemExit(0 if main() else 1)
