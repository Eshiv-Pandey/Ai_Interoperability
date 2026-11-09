"""Recompute retained v10 evidence without launching any application or client."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import check_agentops_bridge_group_v1 as checker

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'runs/agentops-native-eligibility/bridge-resume-audit-v1'
RETAINED = ROOT / 'runs/agentops-native-eligibility/bridge-parent-check-v10.json'
RUN = ROOT / 'runs/agentops-native-eligibility/linux-bridge-v10'


def record(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def write(name, value):
    with (OUTPUT / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    OUTPUT.mkdir(exist_ok=False)
    # Recovered description of the prior ad-hoc comparison, not raw tool bytes.
    write('initial-comparison-failure.json', {
        'source': 'Recovered from the visible preceding tool invocation and output',
        'raw_process_capture': False,
        'comparison': "actual == {k:v for k,v in retained.items() if k != 'schema_version'}",
        'error': 'AssertionError: Current retained-data recomputation differs',
        'correction': 'checker.check returns schema_version; compare both complete objects.',
        'evidence_modified': False, 'application_requests': 0,
    })
    paths = [RETAINED, RUN / 'result.json', RUN / 'export-manifest.json',
             Path(checker.__file__), Path(__file__)]
    before = [record(path) for path in paths]
    report = {'schema_version': 'agentops-bridge-resume-audit/1', 'status': 'failed',
              'started_at_utc': datetime.now(timezone.utc).isoformat(),
              'inputs': before, 'application_requests': 0, 'live_model_calls': 0,
              'scientific_gate_credit_added': 0}
    try:
        retained = json.loads(RETAINED.read_bytes())
        actual = checker.check(RUN)
        write('recomputed-parent-check.json', actual)
        differences = [key for key in sorted(set(retained) | set(actual))
                       if retained.get(key) != actual.get(key)]
        report['differing_top_level_keys'] = differences
        report['inputs_unchanged'] = before == [record(path) for path in paths]
        if differences or not report['inputs_unchanged']:
            raise ValueError('Retained evidence comparison failed')
        report.update(status='retained_evidence_recomputed_equal',
                      files_checked=actual['files_checked'], counts=actual['counts'],
                      all_evidence_complete=actual['all_evidence_complete'],
                      recomputed_report=record(OUTPUT / 'recomputed-parent-check.json'))
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    write('result.json', report)
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ('inputs', 'recomputed_report')}, indent=2))
    return report['status'] == 'retained_evidence_recomputed_equal'


if __name__ == '__main__':
    raise SystemExit(0 if main() else 1)
