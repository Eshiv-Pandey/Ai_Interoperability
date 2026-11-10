"""Focused constructed audit of the exact production V8 public-CA exception."""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('fresh_guard_peer_control_required')
    source = ROOT / 'scripts/ap2_reference_development_v8.py'
    raw = source.read_bytes()
    tree = ast.parse(raw)
    worker = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'worker')
    declaration = next(node for node in worker.body if isinstance(node, ast.Assign)
                       and any(isinstance(target, ast.Name) and target.id == 'public_CA_bundles' for target in node.targets))
    hook = next(node for node in worker.body if isinstance(node, ast.FunctionDef) and node.name == 'public_only_actor')
    exact_guard = ast.fix_missing_locations(ast.Module(body=[deepcopy(declaration), deepcopy(hook)], type_ignores=[]))
    cases = {}
    with tempfile.TemporaryDirectory(prefix='ap2-v8-ca-guard-peer-') as temporary:
        base = Path(temporary).resolve()
        site = base / 'nonexecuted-site-packages'
        state = {'private_root': None, 'bridge_client_dispatched': False}
        namespace = {'Path': Path, 'os': os, 'ROOT': ROOT, 'site_packages': site, 'audit_state': state,
                     'denials': {'private_reads_blocked': 0}, 'plan': {}, 'output': base}
        exec(compile(exact_guard, str(source), 'exec'), namespace)
        public = namespace['public_CA_bundles']
        expected = {site / 'certifi/cacert.pem', site / 'grpc/_cython/_credentials/roots.pem'}
        scenarios = [
            ('installed_certifi_public_CA_allowed', site / 'certifi/cacert.pem', True),
            ('installed_grpc_public_CA_allowed', site / 'grpc/_cython/_credentials/roots.pem', True),
            ('same_certifi_basename_elsewhere_denied', base / 'elsewhere/cacert.pem', False),
            ('third_CA_bundle_path_denied', site / 'other/roots.pem', False),
            ('saved_private_PEM_denied', base / 'saved-signing-key.pem', False),
            ('saved_private_KEY_denied', base / 'saved-signing-key.key', False),
            ('saved_Gemini_key_name_denied', base / 'gemini-api-key.txt', False),
            ('dotenv_denied', base / '.env', False),
            ('private_evaluator_denied', ROOT / 'benchmark/ap2-native-bridge-development-v8/evaluator.json', False),
        ]
        for label, path, expected_allowed in scenarios:
            try:
                namespace['public_only_actor']('open', (str(path), 'r', None))
                allowed, reason = True, None
            except PermissionError as error:
                allowed, reason = False, str(error)
            cases[label] = {'passed': allowed == expected_allowed, 'allowed': allowed, 'reason': reason}
        state['private_root'] = base / 'owned-private-profile'
        try:
            namespace['public_only_actor']('open', (str(state['private_root'] / 'merchant_signing_key.pem'), 'r', None))
            allowed = True
        except PermissionError:
            allowed = False
        cases['owned_profile_signing_behavior_preserved'] = {'passed': allowed, 'allowed': allowed}
        cases['exactly_two_installed_public_paths'] = {'passed': public == expected and len(public) == 2,
                                                     'relative_paths': sorted(path.relative_to(site).as_posix() for path in public)}
    report = {'schema_version': 'ap2-v8-public-CA-guard-constructed-peer-control/1',
              'reviewed_utc': datetime.now(timezone.utc).isoformat(), 'runner_sha256': hashlib.sha256(raw).hexdigest(),
              'passed': all(row['passed'] for row in cases.values()), 'controls': cases,
              'actual_application_or_provider_calls': 0, 'actual_key_or_evaluator_file_reads': 0,
              'actual_actor_or_bridge_processes_executed': 0,
              'scope': 'Executes only extracted exact production CA-set declaration and audit-hook function with supplied synthetic open-event paths. Installs no audit hook and opens no represented key/evaluator/CA file. Source-bound controls are not an OS sandbox.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'controls': len(cases)}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
