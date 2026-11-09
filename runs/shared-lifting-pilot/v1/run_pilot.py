"""Prepare, then execute once, the reviewed 12-case engineering pilot.

Preparation copies and hashes inputs/source/receipts without launching workers.
Execution requires that prospective plan, refuses existing outputs, and runs
four sequential bundles plus their versioned verifiers. No replay or live run.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback


ALLOCATION = Path(__file__).resolve().parent
ROOT = ALLOCATION.parents[2]
BUDGETS = (32, 256, 4096, 100000)
CLOCK, WORKER_TIMEOUT = 100, 30
ENTRYPOINT = 'interoperability.shared_lifting_comparison_v3'
ARMS = {
    'baseline': 'interoperability.refinement_oracle',
    'direct_pruned': 'interoperability.direct_goal_pruned_v2',
    'candidate': 'interoperability.refinement',
    'shared_lift': 'interoperability.refinement_shared_lift_v2',
}
CHECKER = 'interoperability.direct_goal_pruned_v2'
RECIPE_SUITE = 'examples/benchmark-development/recipe-v1.json'
RECIPE_MANIFEST = 'examples/refinement-development/manifest.json'
STRESS = 'runs/refinement-scaling/v2/inputs/profiles/scale-0031.json'
STRESS_MANIFEST = 'runs/refinement-scaling/v2/inputs/manifest.json'
SHARED_RECEIPT = 'runs/refinement-shared-lift-software/v2/validation-1'
HARNESS_RECEIPT = 'runs/shared-lifting-comparison-software/validation-1'
REVIEW = 'runs/refinement-shared-lift-software/v2/source-review-v1.json'
HARNESS_REVIEW = 'runs/shared-lifting-comparison-software/source-review-v1.json'
RECEIPTS = tuple(SHARED_RECEIPT + '/' + name for name in
                 ('request.json', 'result.json', 'stdout.log', 'stderr.log', 'capture.py')) + (
    REVIEW, HARNESS_REVIEW,
) + tuple(HARNESS_RECEIPT + '/' + name for name in
          ('plan.json', 'result.json', '0-stdout.bin', '0-stderr.bin',
           '1-stdout.bin', '1-stderr.bin', 'run_tests.py'))
BOOT = (
    'import sys; sys.path.insert(0,sys.argv[1]); '
    'from interoperability.shared_lifting_comparison_v3 import main; '
    'raise SystemExit(main(sys.argv[2:]))'
)
CLAIM_LIMIT = (
    'Engineering pilot: all 11 existing authored recipe-development cases plus '
    'one deliberately selected motivating stress case. No held-out or '
    'representative workload, novelty, speed advantage or domain qualification.'
)


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_bytes())


def record(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def snapshot(original, relative, originals, snapshots):
    source = (ROOT / original).resolve()
    if not source.is_relative_to(ROOT) or (ROOT / original).is_symlink():
        raise ValueError('Refusing source outside workspace or symbolic link: ' + original)
    raw = source.read_bytes()
    target = ALLOCATION / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(raw)
    value = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    originals[original] = value
    snapshots[relative] = value
    return target


def require_record(path, expected):
    if record(path) != {key: expected[key] for key in ('bytes', 'sha256')}:
        raise ValueError('Bytes differ from retained receipt: ' + str(path))


def verify_prerequisites():
    shared = read(ROOT / SHARED_RECEIPT / 'result.json')
    if not (shared['passed'] is True and shared['test_count'] == 23
            and shared['captured_source_unchanged'] is True
            and shared['workspace_source_unchanged'] is True
            and shared['preserved_dependencies_unchanged'] is True):
        raise ValueError('Shared-lift focused receipt did not pass unchanged')
    for name, expected in shared['sources_after'].items():
        require_record(ROOT / name, expected)
    harness = read(ROOT / HARNESS_RECEIPT / 'result.json')
    if not (harness['status'] == 'passed' and harness['original_sources_unchanged'] is True
            and harness['captured_sources_unchanged'] is True
            and [row['tests_reported'] for row in harness['executions']] == [3, 5]
            and all(row['returncode'] == 0 and not row['timed_out'] for row in harness['executions'])):
        raise ValueError('Resource/harness focused receipt did not pass unchanged')
    tested = read(ROOT / HARNESS_RECEIPT / 'plan.json')['sources']
    for expected in tested:
        require_record(ROOT / expected['path'], expected)
    package_names = {path.relative_to(ROOT).as_posix()
                     for path in (ROOT / 'src/interoperability').rglob('*.py')}
    if package_names != {row['path'] for row in tested if row['path'].startswith('src/interoperability/')}:
        raise ValueError('Current package file set differs from tested package')
    review = read(ROOT / REVIEW)
    if review['status'] != 'no_blocking_source_findings' or review['blocking_findings']:
        raise ValueError('Independent source review has unresolved blockers')
    reviewed = review['reviewed_source']
    if record(ROOT / reviewed['path'])['sha256'] != reviewed['sha256']:
        raise ValueError('Candidate differs from independently reviewed source')
    harness_review = read(ROOT / HARNESS_REVIEW)
    if (harness_review['status'] != 'no_blocking_source_findings'
            or harness_review['blocking_findings']
            or {row['path'] for row in harness_review['reviewed_sources']} != {
                'src/interoperability/benchmark_resources_v1.py',
                'src/interoperability/shared_lifting_comparison_v3.py'}):
        raise ValueError('Final resource/comparison source review is missing or blocked')
    for reviewed in harness_review['reviewed_sources']:
        if record(ROOT / reviewed['path'])['sha256'] != reviewed['sha256']:
            raise ValueError('Harness differs from independently reviewed final source')


def prepare():
    if set(ALLOCATION.iterdir()) != {Path(__file__).resolve()}:
        raise ValueError('Preparation allocation already consumed; refuse existing outputs')
    verify_prerequisites()
    originals, snapshots = {}, {}
    originals[Path(__file__).relative_to(ROOT).as_posix()] = record(Path(__file__))
    suite = read(ROOT / RECIPE_SUITE)
    if (suite['schema_version'] != 'admission-benchmark-suite/1'
            or suite['split'] != 'development' or suite['evaluation_clock'] != CLOCK
            or len(suite['cases']) != 11):
        raise ValueError('Require the unchanged entire 11-case recipe development suite')
    manifest = read(ROOT / RECIPE_MANIFEST)
    expected = {row['file']: row for row in manifest['profiles']}
    membership = [((ROOT / RECIPE_SUITE).parent / row['path']).resolve().relative_to(
        ROOT / 'examples/refinement-development').as_posix() for row in suite['cases']]
    if (manifest['schema_version'] != 'recipe-development-fixtures/1'
            or manifest['scope'] != 'authored-development-only' or manifest['held_out'] is not False
            or manifest['now'] != CLOCK or len(manifest['profiles']) != 11 or len(expected) != 11
            or len(set(membership)) != 11 or set(membership) != set(expected)):
        raise ValueError('Suite does not have exactly the declared 11-profile manifest membership')
    original_suite = snapshot(RECIPE_SUITE, 'inputs/' + RECIPE_SUITE, originals, snapshots)
    snapshot(RECIPE_MANIFEST, 'inputs/' + RECIPE_MANIFEST, originals, snapshots)
    cases, suite_cases, ids = [], [], set()
    for entry in suite['cases']:
        source = ((ROOT / RECIPE_SUITE).parent / entry['path']).resolve()
        if not source.is_relative_to(ROOT / 'examples/refinement-development'):
            raise ValueError('Recipe suite case is outside its declared development directory')
        relative = source.relative_to(ROOT).as_posix()
        expected_profile = expected[source.relative_to(ROOT / 'examples/refinement-development').as_posix()]
        require_record(source, expected_profile)
        copied = snapshot(relative, 'inputs/' + relative, originals, snapshots)
        require_record(copied, expected_profile)
        model = read(copied)
        if (model['id'] != expected_profile['profile_id'] or model['id'] in ids
                or model['schema_version'] != 'recipe-continuation/1'):
            raise ValueError('Duplicate case ID or wrong input schema')
        ids.add(model['id'])
        cases.append({'id': model['id'], 'family': entry['family'],
                      'cohort': 'entire_existing_recipe_development_suite',
                      'original': relative, 'snapshot': copied.relative_to(ALLOCATION).as_posix(),
                      **record(copied)})
        suite_cases.append({'path': relative, 'family': entry['family']})
    stress_manifest = read(ROOT / STRESS_MANIFEST)
    selected = [row for row in stress_manifest['cases'] if row['profile_id'] == 'scale-0031']
    if len(selected) != 1 or selected[0]['input']['path'] != 'profiles/scale-0031.json':
        raise ValueError('Frozen stress input record is missing or ambiguous')
    require_record(ROOT / STRESS, selected[0]['input'])
    snapshot(STRESS_MANIFEST, 'inputs/stress-source-manifest.json', originals, snapshots)
    copied = snapshot(STRESS, 'inputs/stress/scale-0031.json', originals, snapshots)
    stress = read(copied)
    if stress['id'] != 'scale-0031' or stress['id'] in ids or stress['schema_version'] != 'recipe-continuation/1':
        raise ValueError('Unexpected motivating stress input')
    cases.append({'id': stress['id'], 'family': selected[0]['family'],
                  'cohort': 'deliberately_selected_motivating_stress',
                  'selection_reason': 'Repeated lifting in this previously observed case motivated caching',
                  'original': STRESS, 'snapshot': copied.relative_to(ALLOCATION).as_posix(), **record(copied)})
    suite_cases.append({'path': 'stress/scale-0031.json', 'family': selected[0]['family']})
    combined = {'schema_version': suite['schema_version'], 'id': 'shared-lifting-engineering-pilot-v1',
                'split': 'development', 'evaluation_clock': CLOCK, 'cases': suite_cases}
    write(ALLOCATION / 'inputs/suite.json', combined)
    snapshots['inputs/suite.json'] = record(ALLOCATION / 'inputs/suite.json')
    for source in sorted((ROOT / 'src/interoperability').rglob('*.py')):
        original = source.relative_to(ROOT).as_posix()
        snapshot(original, 'source/' + source.relative_to(ROOT / 'src').as_posix(), originals, snapshots)
    for original in RECEIPTS:
        snapshot(original, 'receipts/' + original, originals, snapshots)
    commands = []
    base = [sys.executable, '-I', '-S', '-B', '-c', BOOT, str(ALLOCATION / 'source')]
    for budget in BUDGETS:
        bundle = ALLOCATION / f'budget-{budget}'
        commands.append({'label': f'budget-{budget}-run', 'budget': budget, 'kind': 'run',
                         'argv': base + ['run', '--suite', str(ALLOCATION / 'inputs/suite.json'),
                                         '--output', str(bundle), '--work-budget', str(budget),
                                         '--timeout-seconds', str(WORKER_TIMEOUT)]})
        commands.append({'label': f'budget-{budget}-verify', 'budget': budget, 'kind': 'verify',
                         'argv': base + ['verify', str(bundle)]})
    plan = {
        'schema_version': 'shared-lifting-engineering-pilot-plan/1', 'created_at': now(),
        'status': 'prepared_not_executed', 'clock': CLOCK, 'budgets': list(BUDGETS),
        'cases': cases, 'case_count': 12, 'algorithms': ARMS, 'checker': CHECKER,
        'reference': ARMS['baseline'], 'entrypoint': ENTRYPOINT, 'commands': commands,
        'source_root': str(ALLOCATION / 'source/interoperability'),
        'original_suite_snapshot': original_suite.relative_to(ALLOCATION).as_posix(),
        'originals': originals, 'snapshots': snapshots,
        'runtime': {'executable': sys.executable, 'python': sys.version, 'platform': platform.platform()},
        'worker_timeout_seconds': WORKER_TIMEOUT, 'workers': 'Sequential; no concurrent bundles or workers',
        'coordinator_timeout_seconds': None,
        'coordinator_timeout_reason': 'Individual workers are bounded; do not kill a coordinator and orphan its worker',
        'end_to_end_definition': 'Recorded solver worker wall plus required certificate worker wall; reference separate',
        'missing_measurements': 'Retain null samples and missing counts; never substitute zero',
        'process_memory_definition': (
            'OS per-process high-water mark observed after result serialization and input post-check, '
            'before final reply output. Includes interpreter/import/input overhead, excludes the parent '
            'and other workers. Maximum across sequential workers, never summed or called solver-only memory.'),
        'claim_limit': CLAIM_LIMIT, 'matrix_66_cases': False, 'replay_planned': False,
        'live_or_wsl_runs': False,
    }
    write(ALLOCATION / 'plan.json', plan)
    write(ALLOCATION / 'plan-seal.json', {'plan': record(ALLOCATION / 'plan.json'), 'sealed_at': now()})
    print(json.dumps({'status': 'prepared_not_executed', 'plan': str(ALLOCATION / 'plan.json'),
                      'plan_sha256': record(ALLOCATION / 'plan.json')['sha256']}), flush=True)


def guards(plan):
    changes = []
    for category, root, entries in (('originals', ROOT, plan['originals']),
                                    ('snapshots', ALLOCATION, plan['snapshots'])):
        for name, expected in entries.items():
            try:
                actual = record(root / name)
            except OSError as error:
                actual = {'error': str(error)}
            if actual != expected:
                changes.append({'category': category, 'path': name, 'expected': expected, 'actual': actual})
    expected_names = set(plan['snapshots'])
    actual_names = {path.relative_to(ALLOCATION).as_posix()
                    for folder in ('inputs', 'source', 'receipts')
                    for path in (ALLOCATION / folder).rglob('*') if path.is_file()}
    if actual_names != expected_names:
        changes.append({'category': 'snapshot_inventory', 'added': sorted(actual_names - expected_names),
                        'missing': sorted(expected_names - actual_names)})
    expected_sources = {name for name in plan['originals'] if name.startswith('src/interoperability/')}
    actual_sources = {path.relative_to(ROOT).as_posix()
                      for path in (ROOT / 'src/interoperability').rglob('*.py')}
    if expected_sources != actual_sources:
        changes.append({'category': 'original_source_inventory',
                        'added': sorted(actual_sources - expected_sources),
                        'missing': sorted(expected_sources - actual_sources)})
    try:
        if record(ALLOCATION / 'plan.json') != read(ALLOCATION / 'plan-seal.json')['plan']:
            changes.append({'category': 'plan', 'error': 'Plan seal mismatch'})
    except (OSError, ValueError, KeyError, TypeError) as error:
        changes.append({'category': 'plan', 'error': str(error)})
    return {'checked_at': now(), 'unchanged': not changes, 'changes': changes}


def invoke(command):
    directory = ALLOCATION / 'commands' / command['label']
    directory.mkdir(parents=True, exist_ok=False)
    receipt = {**command, 'cwd': str(ALLOCATION), 'started_at': now(),
               'returncode': None, 'outer_timeout_seconds': None}
    tick = time.perf_counter_ns()
    with (directory / 'stdout.bin').open('xb') as stdout, (directory / 'stderr.bin').open('xb') as stderr:
        try:
            receipt['returncode'] = subprocess.run(command['argv'], cwd=ALLOCATION,
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, check=False).returncode
        except OSError as error:
            receipt['error'] = type(error).__name__ + ': ' + str(error)
    receipt.update(finished_at=now(), coordinator_wall_ns=time.perf_counter_ns() - tick,
                   stdout=record(directory / 'stdout.bin'), stderr=record(directory / 'stderr.bin'))
    write(directory / 'process.json', receipt)
    return receipt


def observation(execution):
    execution = execution or {}
    resource = execution.get('resources') or {}
    result = execution.get('result')
    return {'status': execution.get('status', 'missing'),
            'decision': result.get('decision') if isinstance(result, dict) else None,
            'reason': result.get('reason') if isinstance(result, dict) else None,
            'solver_stats': result.get('stats') if isinstance(result, dict) else None,
            'evaluation_ns': execution.get('evaluation_ns'),
            'worker_wall_ns': (execution.get('process') or {}).get('worker_wall_ns'),
            'memory': resource.get('memory', {'status': 'missing', 'peak_resident_bytes': None,
                                             'reason': 'No resource observation retained'}),
            'resource_timings': resource.get('timings'),
            'input_unchanged': execution.get('input_unchanged')}


def budget_report(plan, budget):
    directory = ALLOCATION / f'budget-{budget}'
    rows_path = directory / 'results.jsonl'
    rows, errors = {}, []
    if rows_path.exists():
        for index, line in enumerate(rows_path.read_bytes().splitlines()):
            try:
                row = json.loads(line)
                if row['case_id'] in rows:
                    raise ValueError('Duplicate case ID')
                rows[row['case_id']] = row
            except (ValueError, KeyError, TypeError) as error:
                errors.append({'line': index + 1, 'error': str(error)})
    cases = []
    for case in plan['cases']:
        row = rows.get(case['id'], {})
        reference = row.get('reference') or {}
        view = {'id': case['id'], 'cohort': case['cohort'], 'family': case['family'],
                'reference': observation(reference), 'reference_valid': row.get('reference_valid', False),
                'algorithms': {}}
        for name in ARMS:
            arm = row.get('algorithms', {}).get(name, {})
            execution = arm.get('execution') or {}
            check = arm.get('certificate_check')
            view['algorithms'][name] = {
                'valid_result': arm.get('valid_result'), 'certificate_valid': arm.get('certificate_valid'),
                'evaluation': observation(execution), 'certificate': observation(check) if check is not None else None}
        cases.append(view)
    # Reuse the engine's reconciled coverage/timing and the new verifier's
    # resource summaries instead of maintaining a second aggregation policy.
    summary_path = directory / 'summary.json'
    summary = read(summary_path) if summary_path.exists() else None
    verify_path = ALLOCATION / 'commands' / f'budget-{budget}-verify' / 'stdout.bin'
    try:
        verified = read(verify_path)
    except (OSError, ValueError):
        verified = None
    expected_ids = {case['id'] for case in plan['cases']}
    return {'budget': budget, 'expected_cases': 12, 'recorded_cases': len(rows),
            'missing_cases': sorted(expected_ids - set(rows)), 'unexpected_cases': sorted(set(rows) - expected_ids),
            'record_read_errors': errors, 'benchmark_summary': summary, 'cases': cases,
            'certified_coverage_over_12_planned_cases': {
                name: summary['algorithms'][name]['certificates_valid'] / 12 for name in ARMS} if summary else None,
            'resource_summary': verified.get('resource_summary') if verified else None,
            'verification': verified,
            'end_to_end_worker_wall_ns': {
                name: summary['algorithms'][name]['evaluation_and_certificate_timing']['worker_wall_ns']
                for name in ARMS} if summary else None,
            'reference_timing_separate': summary.get('reference_timing') if summary else None}


def execute():
    plan = read(ALLOCATION / 'plan.json')
    if (plan['schema_version'] != 'shared-lifting-engineering-pilot-plan/1'
            or plan['budgets'] != list(BUDGETS) or plan['case_count'] != 12
            or plan['clock'] != CLOCK or plan['algorithms'] != ARMS):
        raise ValueError('Unexpected prospective plan')
    if any((ALLOCATION / name).exists() for name in
           ('started.json', 'result.json', 'refused-execution.json', 'commands',
            *(f'budget-{budget}' for budget in BUDGETS))):
        raise ValueError('Execution allocation already consumed; refuse existing outputs')
    initial = guards(plan)
    if not initial['unchanged']:
        write(ALLOCATION / 'refused-execution.json', {'refused_at': now(), 'guards': initial})
        raise ValueError('Frozen plan/source/input/receipt guard failed before execution: ' + json.dumps(initial))
    write(ALLOCATION / 'started.json', {'started_at': now(), 'plan': record(ALLOCATION / 'plan.json'), 'guards': initial})
    calls, checks, failure = [], [], None
    try:
        for command in plan['commands']:
            before = guards(plan)
            if not before['unchanged']:
                raise ValueError('Source/input/receipt changed before ' + command['label'])
            print('Starting ' + command['label'], flush=True)
            receipt = invoke(command)
            after = guards(plan)
            write(ALLOCATION / 'commands' / command['label'] / 'guards.json', {'before': before, 'after': after})
            calls.append(receipt)
            checks.append(after)
            print(command['label'] + ' returned ' + str(receipt['returncode']), flush=True)
            if not after['unchanged']:
                raise ValueError('Source/input/receipt changed after ' + command['label'])
    except Exception as error:
        failure = {'type': type(error).__name__, 'error': str(error), 'traceback': traceback.format_exc()}
    reports = []
    for budget in BUDGETS:
        try:
            reports.append(budget_report(plan, budget))
        except Exception as error:
            reports.append({'budget': budget, 'expected_cases': 12, 'report_error': str(error),
                            'traceback': traceback.format_exc(), 'raw_bundle': f'budget-{budget}'})
    final_guard = guards(plan)
    complete = len(calls) == 8 and all(row['returncode'] == 0 for row in calls)
    passed = complete and failure is None and final_guard['unchanged'] and all(
        not report.get('report_error') and report.get('recorded_cases') == 12
        and not report.get('record_read_errors') and not report.get('missing_cases')
        and not report.get('unexpected_cases') for report in reports)
    result = {
        'schema_version': 'shared-lifting-engineering-pilot-result/1', 'status': 'passed' if passed else 'failed',
        'finished_at': now(), 'plan': record(ALLOCATION / 'plan.json'), 'commands': calls,
        'not_invoked_commands': [row['label'] for row in plan['commands'] if row['label'] not in {c['label'] for c in calls}],
        'failure': failure, 'final_guards': final_guard, 'budgets': reports,
        'source_hashes': {name: row for name, row in plan['snapshots'].items() if name.startswith('source/')},
        'checker': {'dispatch': CHECKER, 'delegated_original_checker': 'interoperability.refinement_oracle'},
        'end_to_end_definition': plan['end_to_end_definition'],
        'coordinator_time_excluded_from_algorithm_end_to_end': True,
        'memory_scope': plan['process_memory_definition'], 'claim_limit': CLAIM_LIMIT,
        'all_four_bundles_verified': len([row for row in calls if row['kind'] == 'verify' and row['returncode'] == 0]) == 4,
    }
    write(ALLOCATION / 'result.json', result)
    print(json.dumps({'status': result['status'], 'result': str(ALLOCATION / 'result.json')}), flush=True)
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'execute'))
    args = parser.parse_args()
    if args.phase == 'prepare':
        prepare()
        return 0
    return execute()


if __name__ == '__main__':
    raise SystemExit(main())
