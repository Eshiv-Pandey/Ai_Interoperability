"""Independent audit of the retained V9 diagnostic-prelude NameError."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('fresh_V9_actual_failure_peer_receipt_required')
    base = args.base.resolve()
    retention_raw = (base / 'retention.json').read_bytes()
    retention = json.loads(retention_raw)
    if retention['status'] != 'retained' or retention['run_id'] != 42902256098 or retention['digest_matches_api'] is not True:
        raise ValueError('completed_expected_V9_retention_required')
    archive = base / 'artifact.zip'
    hasher = hashlib.sha256()
    with archive.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            hasher.update(block)
    identities, selected = {}, {}
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        for name in ('smoke/conventional/worker-failure.json', 'smoke/conventional/result.json',
                     'smoke/conventional/source-runner.py', 'smoke/conventional/plan.json',
                     'matrix/allocation-manifest.json', 'matrix/execution-results.json',
                     'independent-evaluation/result.json'):
            raw = bundle.read(name)
            if len(raw) > 4 * 1024 * 1024 or raw != (base / 'extracted' / name).read_bytes():
                raise ValueError('selected_capture_archive_extraction_identity_required')
            identities[name] = identity(raw)
            selected[name] = raw
    failure = json.loads(selected['smoke/conventional/worker-failure.json'])
    result = json.loads(selected['smoke/conventional/result.json'])
    plan = json.loads(selected['smoke/conventional/plan.json'])
    allocation = json.loads(selected['matrix/allocation-manifest.json'])
    execution = json.loads(selected['matrix/execution-results.json'])
    evaluated = json.loads(selected['independent-evaluation/result.json'])
    runner = selected['smoke/conventional/source-runner.py']
    tree = ast.parse(runner)
    bound = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.Assign):
            bound.update(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            bound.update(alias.asname or (alias.name.split('.')[0] if isinstance(node, ast.Import) else alias.name)
                         for alias in node.names)
    worker = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'worker')
    first_stage = next(node for node in worker.body if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                       and isinstance(node.value.func, ast.Name) and node.value.func.id == 'append')
    missing = [name for name in ('append', 'now') if name not in bound]
    absent_names = ('worker-stages.jsonl', 'actor-guard-denials.jsonl', 'actor-input-separation.json',
                    'public-certificate-admission.json', 'runtime-manifest.json', 'original-callable-code-checks.json',
                    'native-servers-started.json', 'native-wire-attempts.jsonl', 'observations/events.jsonl')
    present = [name for name in absent_names if 'smoke/conventional/' + name in names]
    checks = {
        'actual_archive_matches_completed_API_digest': archive.stat().st_size == retention['archive_bytes']
            and hasher.hexdigest() == retention['archive_sha256'] == retention['api_digest'].removeprefix('sha256:'),
        'actual_NameError_is_append_before_guard_admission': result['returncode'] == 3 and failure['error_type'] == 'NameError'
            and failure['reason'] == "name 'append' is not defined"
            and any(frame['function'] == 'worker' and frame['line'] == first_stage.lineno == 707 for frame in failure['frames']),
        'retained_actor_identity_matches_plan_and_allocation': identity(runner) == allocation['runner']
            == plan['owned_components']['scripts/ap2_reference_development_v9.py'],
        'both_append_and_now_missing_at_module_scope': missing == ['append', 'now'],
        'no_stage_certificate_guard_or_native_capture_retained': present == [],
        'all_104_matrix_slots_stayed_untouched': allocation['declared_cells'] == execution['declared_cells'] == len(execution['cells']) == 104
            and all(row['returncode'] is None and row['allocation_status'] == 'not_executed_before_workflow_finalization' for row in execution['cells'])
            and not any(name.startswith('matrix/attempts/') for name in names),
        'independent_evaluator_retains_104_missing_zero_verified': evaluated['totals']['missing_cells'] == 104
            and evaluated['totals']['verified_captures'] == evaluated['totals']['verified_purchases'] == 0,
        'diagnostic_contains_only_bounded_frames': failure['contents_arguments_locals_headers_and_environment_retained'] is False
            and 0 < len(failure['frames']) <= 24 and all(set(frame) == {'file', 'function', 'line'} for frame in failure['frames']),
    }
    report = {'schema_version': 'ap2-v9-actual-stage-prelude-failure-independent-peer-audit/1',
              'reviewed_utc': datetime.now(timezone.utc).isoformat(), 'run_id': retention['run_id'], 'head_sha': retention['head_sha'],
              'passed': all(checks.values()), 'controls': checks, 'retention_identity': identity(retention_raw),
              'archive_identity': {'bytes': archive.stat().st_size, 'sha256': hasher.hexdigest()},
              'selected_archive_and_extraction_identities': identities, 'actual_failure': failure,
              'actual_result': result, 'additional_source_confirmed_missing_globals': missing,
              'actual_first_stage_source_line': first_stage.lineno, 'capture_files_present': present,
              'actual_matrix_evaluation_totals': evaluated['totals'],
              'V8_external_operation_caller_resolved_by_V9': False,
              'cause_precision': 'The actual V9 failure is unresolved append at the first stage-journal statement, before certificate admission or guard installation. now is a separate source-confirmed missing dependency, not the observed exception. V9 provides no new guard/network observation and does not identify V8 external operation.',
              'new_application_or_provider_calls': 0, 'new_actor_or_bridge_processes_executed': 0,
              'frozen_V9_or_original_sources_mutated': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'controls': len(checks), 'observed_error': failure['reason'],
                      'additional_missing_now': 'now' in missing}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
