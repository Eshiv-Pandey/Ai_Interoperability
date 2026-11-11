"""Independently audit retained common-cost bytes without executing benchmark code.

Reads saved GitHub metadata, the API-digest-bound ZIP, allocation and every raw
closure. Certificate acceptance remains the captured unchanged checker's receipt;
this auditor does not import a worker, solver, checker or original coordinator.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import random
import re
import stat
import statistics
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'Eshiv-Pandey/Ai_Interoperability'
RUN_ID = 42927208534
HEAD_SHA = 'd058c2a05e278b71ad5969e49ecdd344576cf166'
METHODS = [('legacy_direct', 'interoperability.refinement_oracle'),
           ('goal_pruned_direct', 'interoperability.direct_goal_pruned_v2'),
           ('original_refinement', 'interoperability.refinement'),
           ('shared_lift', 'interoperability.refinement_shared_lift_v2'),
           ('guard_pruned_direct', 'interoperability.direct_guard_pruned_v3')]
CAPS = {'cpu_soft_seconds': 5, 'cpu_hard_seconds': 6, 'wall_seconds': 10,
        'address_space_bytes': 536870912, 'rss_hard_cap_claimed': False,
        'solver_logical_allowance': 100000000}
PINNED = {
    'snapshot/protocol.json': {'bytes': 24245, 'sha256': 'a17634b4ceb67d64bfc2506d5830b26a2d5108ad60a1bbe7825546d5fe4fca0e'},
    'snapshot/order.json': {'bytes': 397900, 'sha256': '0127c1298d519b551d0aa1b3cd016b25e1e2d94a05f93b2eef318f25b80fb9e8'},
    'driver/common_cost_worker_v1.py': {'bytes': 9515, 'sha256': '5f7695f3775488c5e208641d3b5e1a0c65bf80e5e4bc2ed2c6826f398c5d6510'},
    'driver/run_common_cost_benchmark_v1.py': {'bytes': 27403, 'sha256': 'efbecfa83b6cd047a357195e1e2d02eba7af2bb7a9e89f32781f01d2ab5c7837'},
}
STATUSES = {'certified', 'unknown', 'failure', 'timeout', 'stopped',
            'stopped_without_closing_receipt', 'not_started'}
RESOURCE_FIELDS = ('cpu_user_ns', 'cpu_system_ns', 'cpu_total_ns', 'outer_wall_ns', 'peak_rss_bytes')
PHASES = {'profile_source_load_and_guard', 'solver_import_and_evaluate',
          'solver_result_serialization', 'independent_checker_import_and_check', 'solver_result_output'}
DIRECT_UNKNOWN = {'evidence_not_fresh', 'indeterminate_observables_or_relations',
                  'incomplete_model_or_relation_coverage', 'work_budget_exhausted'}
REFINEMENT_UNKNOWN = {'evidence_not_fresh', 'indeterminate_observables', 'unresolved_relation_or_recipe',
                      'incomplete_model_or_relation_coverage', 'work_budget_exhausted'}
REASONS = {
    'legacy_direct': {'supported': {'concrete_recipe_path'}, 'unsupported': {'complete_relational_product_exhausted'}, 'unknown': DIRECT_UNKNOWN},
    'goal_pruned_direct': {'supported': {'concrete_recipe_path'}, 'unsupported': {'goal_relevant_relational_product_exhausted'}, 'unknown': DIRECT_UNKNOWN},
    'original_refinement': {'supported': {'public_recipe_witness'}, 'unsupported': {'certified_refinement_exhaustion'}, 'unknown': REFINEMENT_UNKNOWN},
    'shared_lift': {'supported': {'public_recipe_witness'}, 'unsupported': {'certified_refinement_exhaustion'}, 'unknown': REFINEMENT_UNKNOWN},
    'guard_pruned_direct': {'supported': {'concrete_recipe_path'}, 'unsupported': {'guard_pruned_goal_relevant_product_exhausted'}, 'unknown': DIRECT_UNKNOWN},
}


def need(condition, label):
    if not condition:
        raise ValueError(label)


def parse(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, 'duplicate_JSON_key')
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError('nonfinite_JSON_value:' + value)
    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def file_identity(path):
    digest, size = hashlib.sha256(), 0
    with Path(path).open('rb') as stream:
        while block := stream.read(1024 * 1024):
            size += len(block); digest.update(block)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def id_fields(row):
    need(type(row) is dict and type(row.get('bytes')) is int and row['bytes'] >= 0
         and type(row.get('sha256')) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']),
         'invalid_byte_identity')
    return {key: row[key] for key in ('bytes', 'sha256')}


def member_name(name):
    need(type(name) is str and name and '\\' not in name and '\x00' not in name
         and not PurePosixPath(name).is_absolute() and not PureWindowsPath(name).drive
         and '..' not in PurePosixPath(name).parts and PurePosixPath(name).as_posix() == name,
         'noncanonical_archive_member')
    return name


def utc(value):
    need(type(value) is str, 'UTC_timestamp_required')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    need(result.tzinfo is not None and result.utcoffset().total_seconds() == 0, 'UTC_timestamp_required')
    return result


class Capture:
    """All ZIP members and extracted copies verified before selected parsing."""
    def __init__(self, base):
        self.base = Path(base).resolve()
        need(self.base.is_dir() and not self.base.is_symlink(), 'retained_capture_directory_required')
        self.metadata = {}
        for name in ('github-run.json', 'github-artifacts.json', 'retention.json', 'plan.json', 'extracted-manifest.json'):
            path = self.base / name
            need(path.is_file() and not path.is_symlink(), 'retained_metadata_file_required:' + name)
            self.metadata[name] = parse(path.read_bytes())
        run, receipt, plan = (self.metadata[n] for n in ('github-run.json', 'retention.json', 'plan.json'))
        need(run['id'] == RUN_ID and type(run['id']) is int and run['status'] == 'completed'
             and run['run_attempt'] == 1 and run['head_sha'] == HEAD_SHA
             and run['event'] == 'workflow_dispatch'
             and run['path'] == '.github/workflows/common-cost-benchmark-v1.yml'
             and run['html_url'] == f'https://github.com/{REPOSITORY}/actions/runs/{RUN_ID}',
             'saved_completed_run_or_frozen_workflow_identity_changed')
        artifact_name = f'common-cost-development-v1-{RUN_ID}-1'
        need(plan['run_id'] == RUN_ID and plan['repository'] == REPOSITORY
             and plan['application_rerun'] is False and plan['artifact_name'] in (None, artifact_name)
             and re.fullmatch(rf'retained-{RUN_ID}-[1-9][0-9]*', self.base.name),
             'retention_plan_identity_changed')
        need(receipt['status'] == 'retained' and receipt['run_id'] == RUN_ID
             and receipt['head_sha'] == HEAD_SHA and receipt['workflow_conclusion'] == run['conclusion']
             and receipt['artifact_name'] == artifact_name, 'retention_receipt_run_binding_changed')
        archive = self.base / 'artifact.zip'
        need(archive.is_file() and not archive.is_symlink(), 'retained_regular_archive_required')
        actual = file_identity(archive)
        need(actual['bytes'] <= 300000000 and actual == {'bytes': receipt['archive_bytes'], 'sha256': receipt['archive_sha256']}
             and receipt['api_digest'] == 'sha256:' + actual['sha256'] and receipt['digest_matches_api'] is True,
             'retained_archive_or_API_digest_changed')
        selected = [a for a in self.metadata['github-artifacts.json']['artifacts'] if a['id'] == receipt['artifact_id']]
        need(len(selected) == 1, 'saved_API_artifact_selection_not_unique')
        artifact = selected[0]
        need(artifact['name'] == artifact_name and artifact['digest'] == receipt['api_digest']
             and artifact['size_in_bytes'] == actual['bytes'] and artifact['expired'] is False
             and artifact['workflow_run']['id'] == RUN_ID and artifact['workflow_run']['head_sha'] == HEAD_SHA,
             'saved_API_artifact_not_bound_to_run_and_archive')
        self.archive_identity, self.run, self.receipt = actual, run, receipt
        self.files = {}
        with zipfile.ZipFile(archive) as source:
            seen, expanded = set(), 0
            for item in source.infolist():
                name = item.filename.rstrip('/') if item.is_dir() else item.filename
                member_name(name)
                need(name.casefold() not in seen and not stat.S_ISLNK(item.external_attr >> 16),
                     'duplicate_or_linked_archive_member')
                seen.add(name.casefold()); expanded += item.file_size
                need(expanded <= 2000000000 and item.file_size <= 64 * 1024 * 1024, 'archive_expansion_bound_exceeded')
                if item.is_dir():
                    continue
                raw = source.read(item)
                need(len(raw) == item.file_size, 'archive_member_size_changed')
                path = self.base / 'extracted' / name
                need(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(self.base / 'extracted')
                     and path.read_bytes() == raw, 'extracted_file_differs_from_archive:' + name)
                self.files[name] = identity(raw)
        inventory = self.metadata['extracted-manifest.json']['files']
        need(len(inventory) == len(self.files) == receipt['extracted_files']
             and len({r['path'] for r in inventory}) == len(inventory), 'retained_extraction_inventory_count_changed')
        need({r['path']: id_fields(r) for r in inventory} == self.files, 'retained_extraction_inventory_changed')
        extracted = self.base / 'extracted'
        disk_names = {p.relative_to(extracted).as_posix() for p in extracted.rglob('*') if p.is_file()}
        need(disk_names == set(self.files), 'extracted_membership_changed')
        self.evidence = [dict(path=(self.base / n).as_posix(), **file_identity(self.base / n))
                         for n in (*self.metadata.keys(), 'artifact.zip')]

    def raw(self, name):
        member_name(name); need(name in self.files, 'required_archive_member_missing:' + name)
        raw = (self.base / 'extracted' / name).read_bytes()
        need(identity(raw) == self.files[name], 'verified_member_changed_during_audit:' + name)
        return raw

    def json(self, name):
        return parse(self.raw(name))

    def verify(self, name, row):
        need(name in self.files and self.files[name] == id_fields(row), 'frozen_or_manifest_file_changed:' + name)


def verify_order(protocol, order):
    """Rebuild the independently declared permutations and all serial positions."""
    ids = [p['id'] for p in protocol['profiles']]
    methods = [m[0] for m in METHODS]
    need(ids == [f'scale-{i:04d}' for i in range(1, 67)] and order['seed'] == 2026111101,
         'exact_authored_profiles_or_order_seed_changed')
    rng = random.Random(2026111101); blocks = {}
    for profile in ids:
        permutation, rotations = list(methods), list(range(5))
        rng.shuffle(permutation); rng.shuffle(rotations)
        blocks[profile] = {'initial_permutation': permutation, 'rotation_for_repeat': rotations}
    need(order['method_blocks'] == blocks and len(order['profile_orders']) == 5, 'balanced_order_blocks_changed')
    cells = []
    for repeat in range(5):
        profiles = list(ids); rng.shuffle(profiles)
        need(order['profile_orders'][repeat] == profiles, 'repeat_profile_order_changed')
        for profile in profiles:
            permutation = blocks[profile]['initial_permutation']; shift = blocks[profile]['rotation_for_repeat'][repeat]
            seed = 1 + int(hashlib.sha256(f'2026111101|{profile}|{repeat}|hash'.encode()).hexdigest()[:16], 16) % (2**32 - 1)
            for position, method in enumerate(permutation[shift:] + permutation[:shift]):
                cells.append({'index': len(cells), 'id': f'r{repeat+1:02d}--{profile}--{method}',
                              'profile_id': profile, 'method_id': method, 'repeat': repeat,
                              'position': position, 'hash_seed': seed})
    need(len(cells) == 1650 and order['cells'] == cells, 'exact_1650_serial_order_changed')
    return cells


def verify_protocol_allocation(capture):
    for name, row in PINNED.items(): capture.verify(name, row)
    protocol = capture.json('snapshot/protocol.json'); order = capture.json('snapshot/order.json')
    need(protocol['schema_version'] == 'common-cost-protocol/1' and protocol['caps'] == CAPS
         and protocol['evaluation_clock'] == 100 and protocol['child_flags'] == ['-S', '-P', '-B']
         and protocol['declared_cells'] == 1650 and protocol['profile_count'] == 66
         and protocol['method_count'] == 5 and protocol['repeat_count'] == 5
         and [(m['id'], m['module']) for m in protocol['methods']] == METHODS
         and protocol['checker']['module'] == 'interoperability.direct_goal_pruned_v2'
         and protocol['checker']['preserved_fixed_internal_budget'] == 2000000,
         'pinned_physical_cost_protocol_changed')
    cells = verify_order(protocol, order)
    expected = dict(PINNED)
    for row in protocol['sources'] + protocol['profiles']:
        name = 'snapshot/' + member_name(row['path']); capture.verify(name, row); expected[name] = id_fields(row)
    need(len(protocol['sources']) == 8, 'eight_file_source_closure_required')
    for _, module in METHODS:
        name = 'snapshot/source/' + module.replace('.', '/') + '.py'
        tree = ast.parse(capture.raw(name))
        functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'evaluate']
        need(len(functions) == 1 and [a.arg for a in functions[0].args.args] == ['profile', 'now', 'budget'],
             'preserved_solver_API_changed')
    tree = ast.parse(capture.raw('snapshot/source/interoperability/direct_goal_pruned_v2.py'))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'check_certificate']
    need(len(functions) == 1 and [a.arg for a in functions[0].args.args] == ['profile', 'result', 'now'],
         'preserved_checker_API_changed')
    language = ast.parse(capture.raw('snapshot/source/interoperability/refinement_oracle.py'))
    budgets = [ast.literal_eval(n.value) for n in language.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == 'CHECK_BUDGET' for t in n.targets)]
    need(budgets == [2000000], 'preserved_checker_budget_changed')
    for key, filename in [('source_suite', 'prior-suite.json'), ('source_input_manifest', 'prior-input-manifest.json')]:
        name = 'snapshot/provenance/' + filename
        capture.verify(name, protocol[key]); expected[name] = id_fields(protocol[key])
    suite = capture.json('snapshot/provenance/prior-suite.json')
    prior = capture.json('snapshot/provenance/prior-input-manifest.json')
    need(suite['evaluation_clock'] == 100 and suite['split'] == 'development'
         and len(suite['cases']) == len(prior['cases']) == 66, 'prior_development_provenance_changed')
    prior_cases = {row['profile_id']: row for row in prior['cases']}
    need(len(prior_cases) == 66, 'prior_profile_identity_duplicate')
    for row, old in zip(protocol['profiles'], suite['cases']):
        model = capture.json('snapshot/' + row['path'])
        need(row['path'] == old['path'] and row['family'] == old['family']
             and model['id'] == row['id'] and model['schema_version'] == 'recipe-continuation/1'
             and id_fields(row) == id_fields(prior_cases[row['id']]['input']), 'all_66_prior_profile_join_changed')
    allocation = capture.json('allocation.json')
    need(allocation['schema_version'] == 'common-cost-allocation/1' and allocation['declared_cells'] == 1650
         and allocation['cells'] == cells and allocation['protocol_identity'] == PINNED['snapshot/protocol.json']
         and allocation['order_identity'] == PINNED['snapshot/order.json']
         and allocation['all_input_source_order_and_job_hashes_frozen_before_execution'] is True
         and allocation['new_application_or_provider_runs'] == 0, 'allocation_contract_changed')
    utc(allocation['created_utc'])
    runtime = allocation['runtime']
    need(runtime['platform'] == 'linux' and runtime['python'].startswith('3.13.1 ')
         and PurePosixPath(runtime['executable']).is_absolute(), 'pinned_hosted_runtime_receipt_changed')
    id_fields(runtime['executable_identity'])
    profiles, methods = ({p['id']: p for p in protocol['profiles']}, {m['id']: m for m in protocol['methods']})
    snapshot_root = None
    for cell in cells:
        name = 'cells/' + cell['id'] + '/job.json'; job = capture.json(name)
        root = job['snapshot_root']
        need(type(root) is str and PurePosixPath(root).is_absolute() and '..' not in PurePosixPath(root).parts
             and PurePosixPath(root).name == 'snapshot', 'original_hosted_snapshot_root_invalid')
        if snapshot_root is None: snapshot_root = root
        need(root == snapshot_root and job == {'schema_version': 'common-cost-job/1', 'cell': cell,
             'snapshot_root': root, 'profile': profiles[cell['profile_id']], 'method': methods[cell['method_id']],
             'sources': protocol['sources'], 'checker': protocol['checker'], 'caps': CAPS, 'evaluation_clock': 100},
             'frozen_per_cell_job_changed')
        expected[name] = capture.files[name]
    frozen = allocation['frozen_files']
    need(len(frozen) == len(expected) and len({r['path'] for r in frozen}) == len(frozen)
         and {r['path']: id_fields(r) for r in frozen} == expected, 'complete_preexecution_frozen_inventory_changed')
    for row in frozen: capture.verify(row['path'], row)
    cell_ids = {c['id'] for c in cells}
    need(all(len(PurePosixPath(n).parts) >= 3 and PurePosixPath(n).parts[1] in cell_ids
             for n in capture.files if n.startswith('cells/')), 'undeclared_extra_cell_directory')
    return protocol, allocation, snapshot_root


def verify_manifest(capture):
    manifest = capture.json('manifest.json'); rows = manifest['files']
    need(len({r['path'] for r in rows}) == len(rows), 'duplicate_artifact_manifest_member')
    names = set(capture.files) - {'manifest.json'}
    manifest_raw = capture.raw('manifest.json'); aliases = []
    for name in list(names):
        if re.fullmatch(r'\.manifest\.json\.pending-[0-9a-f]{32}', name) and capture.raw(name) == manifest_raw:
            names.remove(name); aliases.append(name)
    need(names == {r['path'] for r in rows}, 'artifact_manifest_membership_changed')
    for row in rows: capture.verify(row['path'], row)
    return aliases


def resource_check(resources):
    need(type(resources) is dict and resources['caps_applied_before_exec'] == CAPS
         and resources['resource_source'] == 'sole terminal os.wait4 per-child rusage after termination'
         and resources['owned_group_cleanup_requested_before_terminal_reap'] is True
         and type(resources['pid']) is int and resources['pid'] > 0
         and resources['owned_process_group'] == resources['pid']
         and type(resources['wall_cap_kill_requested']) is bool, 'lifetime_resource_ownership_receipt_changed')
    for field in RESOURCE_FIELDS:
        need(type(resources[field]) is int and resources[field] >= 0, 'invalid_lifetime_resource_value:' + field)
    need(abs(resources['cpu_user_ns'] + resources['cpu_system_ns'] - resources['cpu_total_ns']) <= 1,
         'CPU_user_system_total_inconsistent')
    status = resources['wait_status']; code = resources['returncode']
    need(type(status) is int and status >= 0 and type(code) is int and status & 127 != 127,
         'nonterminal_or_invalid_wait_status')
    expected = -(status & 127) if status & 127 else (status >> 8) & 255
    need(code == expected, 'wait_status_returncode_mismatch')
    for key in ('parent_interruption_type', 'group_cleanup_error_type'):
        need(resources[key] is None or type(resources[key]) is str, 'invalid_parent_cleanup_error_receipt')


def reply_check(reply, cell):
    need(type(reply) is dict and reply.get('schema_version') == 'common-cost-worker/1'
         and reply.get('cell') == cell and reply.get('caps_observed') == CAPS, 'unbound_worker_reply')
    need(reply['status'] in {'certified', 'unknown', 'failure', 'timeout'}, 'invalid_worker_status')
    phases = reply['phase_resources']
    need(type(phases) is dict and set(phases).issubset(PHASES), 'invalid_worker_phase_names')
    for values in phases.values():
        need(set(values) == {'cpu_ns', 'wall_ns'}
             and all(type(v) is int and v >= 0 for v in values.values()), 'invalid_phase_resource_values')
    for field in ('worker_entry_to_pre_reply_cpu_ns', 'worker_entry_to_pre_reply_wall_ns', 'peak_rss_before_reply_bytes'):
        need(type(reply[field]) is int and reply[field] >= 0, 'invalid_inner_resource_value')
    if 'interpreter_flags' in reply:
        need(reply['interpreter_flags'] == {'no_site': 1, 'safe_path': True, 'isolated': 0, 'ignore_environment': 0}
             and type(reply['hash_seed_probe']) is int, 'seed_honoring_worker_flags_changed')
    if reply['status'] == 'certified':
        need(reply['certificate_valid'] is True and reply['decision'] in {'supported', 'unsupported'}
             and reply['checker_internal_cap_nonbinding_for_accepted_proof'] is True
             and set(phases) == PHASES, 'invalid_captured_certified_checker_receipt')
    if reply['status'] == 'unknown':
        need(reply['decision'] == 'unknown' and reply['certificate_valid'] is None, 'unknown_misrepresented_as_verdict')
    if reply.get('failure_kind') == 'checker_rejected_or_internal_soft_cap':
        need(reply['status'] == 'failure' and reply['certificate_valid'] is False,
             'checker_rejection_misrepresented_as_certification')


def optional_json(capture, name):
    if name not in capture.files: return None, None
    try: return capture.json(name), None
    except (ValueError, UnicodeDecodeError) as error: return None, type(error).__name__


def logical_headroom(method, decision, meter, result_verified):
    """A counter below its allowance cannot override an exhaustion reason."""
    if type(meter) is not dict:
        return None, 'indeterminate_missing_meter', False
    reason, budget, work = meter.get('reason'), meter.get('budget'), meter.get('work_units')
    reason_valid = reason in REASONS[method].get(decision, set())
    if reason == 'work_budget_exhausted':
        return False, 'binding_work_budget_exhausted_reason', reason_valid
    if type(budget) is not int or budget != CAPS['solver_logical_allowance'] or type(work) is not int or work < 0:
        return None, 'indeterminate_invalid_or_different_allowance_counter', reason_valid
    if work >= budget:
        return False, 'binding_counter_reached_allowance', reason_valid
    if not result_verified:
        return None, 'indeterminate_meter_not_bound_to_retained_result', reason_valid
    if not reason_valid:
        return None, 'indeterminate_unrecognized_reason_for_method_and_decision', False
    return True, 'nonbinding_verified_counter_and_no_exhaustion_reason', True


def audit_cell(capture, cell, allocation, snapshot_root):
    prefix = 'cells/' + cell['id'] + '/'
    before_name, after_name = prefix + 'before.json', prefix + 'after.json'
    refs = [dict(path=n, **capture.files[n]) for n in sorted(capture.files) if n.startswith(prefix)]
    before = None
    if before_name in capture.files:
        before = capture.json(before_name)
        hosted_root = str(PurePosixPath(snapshot_root).parent)
        job_name = prefix + 'job.json'
        need(before['cell'] == cell and before['job_identity'] == capture.files[job_name]
             and before['caps'] == CAPS and before['hash_seed'] == cell['hash_seed']
             and before['argv'] == [allocation['runtime']['executable'], '-S', '-P', '-B',
                  hosted_root + '/driver/common_cost_worker_v1.py', '--job', hosted_root + '/' + job_name]
             and utc(before['started_utc']) >= utc(allocation['created_utc']), 'opening_receipt_identity_changed')
    if after_name not in capture.files:
        row = {'cell': cell, 'status': 'stopped_without_closing_receipt' if before is not None else 'not_started',
               'decision': None, 'certificate_valid': None, 'resources': None}
    else:
        after, error = optional_json(capture, after_name)
        if error or type(after) is not dict or after.get('cell') != cell or before is None:
            row = {'cell': cell, 'status': 'failure', 'decision': None, 'certificate_valid': None, 'resources': None,
                   'failure_kind': 'malformed_or_unbound_closing_receipt',
                   'retained_closing_identity': capture.files[after_name]}
        else:
            row = after
            need(row.get('status') in STATUSES and 'decision' in row and 'certificate_valid' in row and 'resources' in row,
                 'invalid_bound_closing_receipt')
    reply, reply_error = optional_json(capture, prefix + 'reply.json')
    result, result_error = optional_json(capture, prefix + 'solver-result.json')
    resources = row['resources']
    if resources is not None:
        resource_check(resources)
        need(prefix + 'stdout.bin' in capture.files and prefix + 'stderr.bin' in capture.files,
             'launched_child_raw_output_missing')
        expected = {'cell': cell, 'status': 'failure', 'decision': None, 'certificate_valid': None, 'resources': resources}
        if resources['parent_interruption_type'] or resources['group_cleanup_error_type']:
            expected.update(status='stopped', failure_kind='parent_interruption_or_group_cleanup_error')
        elif resources['wall_cap_kill_requested'] or resources['returncode'] == -14:
            expected.update(status='timeout', timeout_kind='wall')
        elif resources['returncode'] == -24:
            expected.update(status='timeout', timeout_kind='cpu_soft')
        elif resources['returncode'] == -9:
            expected.update(failure_kind='SIGKILL_cpu_hard_or_external_cause_unattributed')
        elif resources['returncode'] != 0:
            expected.update(failure_kind='nonzero_or_missing_invalid_worker_reply')
        elif reply_error or type(reply) is not dict or reply.get('cell') != cell or reply.get('caps_observed') != CAPS:
            need(row['failure_kind'] == 'launch_or_receipt_exception' and type(row['error_type']) is str,
                 'invalid_zero_exit_reply_not_retained_as_failure')
            expected.update(failure_kind=row['failure_kind'], error_type=row['error_type'])
        else:
            reply_check(reply, cell)
            expected.update({k: v for k, v in reply.items() if k not in {'schema_version', 'cell', 'resources'}})
        need(row == expected, 'closing_status_or_reply_projection_changed')
        if type(reply) is dict and reply.get('cell') == cell and reply.get('caps_observed') == CAPS:
            reply_check(reply, cell)
            need(resources['peak_rss_bytes'] >= reply['peak_rss_before_reply_bytes'], 'lifetime_RSS_below_pre_reply_RSS')
    elif after_name in capture.files and row.get('failure_kind') != 'malformed_or_unbound_closing_receipt':
        need(row['status'] == 'failure' and row.get('failure_kind') == 'launch_or_receipt_exception'
             and row['decision'] is None and row['certificate_valid'] is None, 'resource_free_closure_not_a_launch_failure')
    result_verified = False
    if type(reply) is dict and 'solver_result_identity' in reply:
        id_fields(reply['solver_result_identity'])
        raw_ok = prefix + 'solver-result.json' in capture.files and capture.files[prefix + 'solver-result.json'] == reply['solver_result_identity']
        if row['status'] in {'certified', 'unknown'}:
            need(raw_ok and not result_error and type(result) is dict, 'conclusive_or_unknown_solver_result_not_retained_exactly')
        if raw_ok:
            need(not result_error and type(result) is dict and canonical(result) == capture.raw(prefix + 'solver-result.json'),
                 'solver_result_serialization_changed')
            stats = result.get('stats', {})
            need(type(stats) is dict and reply['method_meter'] == {'budget': stats.get('budget'),
                 'work_units': stats.get('work_units'), 'reason': result.get('reason')}, 'method_meter_not_bound_to_raw_result')
            nonbinding = (type(stats.get('work_units')) is int and stats.get('budget') == CAPS['solver_logical_allowance']
                          and stats['work_units'] < stats['budget'])
            need(reply['solver_logical_cap_nonbinding'] is nonbinding, 'logical_headroom_flag_changed')
            if row['status'] in {'certified', 'unknown'}:
                need(result['decision'] == row['decision'], 'raw_result_and_closing_decisions_disagree')
            result_verified = True
    if row['status'] in {'certified', 'unknown'}:
        need(result_verified and resources is not None, 'certified_or_unknown_cell_without_raw_result_and_lifetime_cost')
    budget = None if type(reply) is not dict else reply.get('method_meter')
    result_decision = result.get('decision') if result_verified else (None if type(reply) is not dict else reply.get('decision'))
    independent_headroom, headroom_reason, reason_valid = logical_headroom(cell['method_id'], result_decision, budget, result_verified)
    raw_headroom = None if type(reply) is not dict else reply.get('solver_logical_cap_nonbinding')
    diagnostics = {'cell': cell, 'status': row['status'], 'decision': row['decision'],
        'certificate_valid': row['certificate_valid'], 'resources': resources,
        'failure_kind': row.get('failure_kind'), 'timeout_kind': row.get('timeout_kind'),
        'unknown_reason': row.get('unknown_reason'), 'method_meter': budget,
        'solver_logical_cap_nonbinding': row.get('solver_logical_cap_nonbinding'),
        'raw_worker_logical_headroom_label': raw_headroom,
        'independent_solver_logical_cap_nonbinding': independent_headroom,
        'independent_logical_headroom_reason': headroom_reason,
        'logical_headroom_raw_label_disagrees': raw_headroom is not None and raw_headroom is not independent_headroom,
        'static_method_reason_catalogue_match': reason_valid,
        'checker_internal_cap_nonbinding_for_accepted_proof': row.get('checker_internal_cap_nonbinding_for_accepted_proof'),
        'raw_result_meter_verified': result_verified, 'raw_reply_parse_error': reply_error,
        'raw_result_parse_error': result_error,
        'phase_resources': None if type(reply) is not dict else reply.get('phase_resources'),
        'solver_result_identity_reported_by_worker': None if type(reply) is not dict else reply.get('solver_result_identity'),
        'retained_raw_files': refs,
        'cpu_limit_nonbinding_from_lifetime_observation': None if resources is None else resources['cpu_total_ns'] < 5000000000,
        'wall_limit_nonbinding_from_outer_observation': None if resources is None else resources['outer_wall_ns'] < 10000000000}
    return row, diagnostics, before


def reconstruct_summary(rows, conservative=False):
    methods = [m[0] for m in METHODS]
    indexed = {(r['cell']['profile_id'], r['cell']['repeat'], r['cell']['method_id']): r for r in rows}
    need(len(rows) == len(indexed) == 1650, 'complete_unique_cell_census_required')
    verdicts, groups, probes = defaultdict(set), defaultdict(list), defaultdict(set)
    for row in rows:
        cell = row['cell']; key = (cell['profile_id'], cell['repeat'])
        if row.get('hash_seed_probe') is not None: probes[key].add(row['hash_seed_probe'])
        if row['status'] == 'certified':
            verdicts[cell['profile_id']].add(row['decision']); groups[key].append(row)
    contradictions = [dict(profile_id=p, verdicts=sorted(v)) for p, v in verdicts.items() if len(v) > 1]
    quarantine = {c['profile_id'] for c in contradictions}
    pairs, details = {}, {}
    for left, right in itertools.combinations(methods, 2):
        cohort, exclusions = [], []
        for profile in sorted({r['cell']['profile_id'] for r in rows}):
            paired = [(indexed[(profile, repeat, left)], indexed[(profile, repeat, right)]) for repeat in range(5)]
            cells = [r for pair in paired for r in pair]; reasons = set()
            if profile in quarantine: reasons.add('profile_wide_certified_supported_unsupported_contradiction')
            if any(r['status'] != 'certified' for r in cells): reasons.add('not_all_five_paired_repeats_certified')
            if any(a['decision'] != b['decision'] for a, b in paired): reasons.add('paired_decision_disagreement')
            if len({r['decision'] for r in cells}) != 1: reasons.add('decision_changes_across_paired_repeats')
            if any(not r.get('solver_logical_cap_nonbinding') for r in cells): reasons.add('logical_allowance_headroom_not_established')
            if conservative and any(r.get('method_meter', {}).get('reason') == 'work_budget_exhausted' for r in cells):
                reasons.add('work_budget_exhausted_reason')
            if conservative and any(not r.get('static_method_reason_catalogue_match') for r in cells):
                reasons.add('method_result_reason_not_valid_for_conclusive_decision')
            if any(not r.get('resources') for r in cells): reasons.add('lifetime_resource_observation_missing')
            if any(r.get('resources') and r['resources']['cpu_total_ns'] >= 5000000000 for r in cells): reasons.add('CPU_soft_limit_binding_or_exceeded')
            if any(r.get('resources') and r['resources']['outer_wall_ns'] >= 10000000000 for r in cells): reasons.add('outer_wall_limit_binding_or_exceeded')
            if reasons:
                exclusions.append({'profile_id': profile, 'reasons': sorted(reasons)})
                continue
            item = {'profile_id': profile, 'paired_repeats': 5}
            for field in ('cpu_total_ns', 'outer_wall_ns', 'peak_rss_bytes'):
                a = statistics.median(pair[0]['resources'][field] for pair in paired)
                b = statistics.median(pair[1]['resources'][field] for pair in paired)
                item[field] = {'left_median': a, 'right_median': b, 'left_over_right': a / b if b > 0 else None}
            cohort.append(item)
        key = left + '__' + right
        pairs[key] = {'complete_same_decision_certified_profile_count': len(cohort),
                      'required_paired_repeats_per_profile': 5, 'per_profile': cohort}
        details[key] = {'left_method': left, 'right_method': right, **pairs[key], 'excluded_profiles': exclusions,
                       'ratio_direction': 'left profile median divided by right profile median; CPU/wall/RSS separately'}
    summary = {'allocated_cells': 1650,
        'by_method_status_counts': {m: dict(Counter(r['status'] for r in rows if r['cell']['method_id'] == m)) for m in methods},
        'hash_seed_probe_disagreements': [{'profile_id': p, 'repeat': r} for (p, r), values in probes.items() if len(values) > 1],
        'certified_contradictions': contradictions,
        'all_five_method_certified_same_decision_profile_repeat_blocks': sum(len(g) == 5 and len({r['decision'] for r in g}) == 1 for g in groups.values()),
        'paired_costs': pairs, 'comparison_unit': '66 related authored profiles; five dependent timing replicates',
        'adverse_allocations_excluded_from_cost_ratios_but_retained_in_status_denominator': True,
        'no_novelty_or_superiority_assumed': True, 'certified_cost_cohorts_usable': True}
    need(len(pairs) == 10, 'all_ten_method_pair_cohorts_required')
    return summary, details


def analyze_capture(capture):
    protocol, allocation, snapshot_root = verify_protocol_allocation(capture)
    aliases = verify_manifest(capture)
    if 'execution-start.json' in capture.files:
        start = capture.json('execution-start.json')
        need(start['allocation_identity'] == capture.files['allocation.json'] and start['one_serial_hosted_runner'] is True
             and utc(start['created_utc']) >= utc(allocation['created_utc']), 'execution_start_allocation_binding_changed')
    rows, cells, openings = [], [], []
    for cell in allocation['cells']:
        row, diagnostics, before = audit_cell(capture, cell, allocation, snapshot_root)
        rows.append(row); cells.append(diagnostics)
        if before is not None: openings.append((cell['index'], utc(before['started_utc'])))
    need([i for i, _ in openings] == list(range(len(openings))), 'serial_dispatch_openings_not_a_contiguous_prefix')
    need(all(a[1] <= b[1] for a, b in zip(openings, openings[1:])), 'serial_opening_timestamps_reversed')
    need(not openings or 'execution-start.json' in capture.files, 'launched_cells_without_execution_start')
    frozen_summary, _ = reconstruct_summary(rows)
    stored = capture.json('results.json')
    need(stored['schema_version'] == 'common-cost-results/1' and stored['cells'] == rows
         and stored['summary'] == frozen_summary and stored['frozen_integrity_verified'] is True
         and stored['allocation_identity'] == capture.files['allocation.json'], 'stored_derived_results_differ_from_independent_raw_reconstruction')
    independent_rows = [dict(row, solver_logical_cap_nonbinding=cell['independent_solver_logical_cap_nonbinding'],
                             static_method_reason_catalogue_match=cell['static_method_reason_catalogue_match'])
                        for row, cell in zip(rows, cells)]
    summary, pairs = reconstruct_summary(independent_rows, conservative=True)
    totals = []
    for method, _ in METHODS:
        selected = [c for c in cells if c['cell']['method_id'] == method]
        counts = Counter(c['status'] for c in selected)
        by_status = {}
        for status in sorted(counts):
            group = [c for c in selected if c['status'] == status]
            observed = [c['resources'] for c in group if c['resources'] is not None]
            by_status[status] = {'allocated_cells': len(group), 'cells_with_lifetime_resources': len(observed),
                'cpu_total_ns_sum': sum(r['cpu_total_ns'] for r in observed),
                'outer_wall_ns_sum': sum(r['outer_wall_ns'] for r in observed),
                'observed_peak_rss_bytes_max': max((r['peak_rss_bytes'] for r in observed), default=None)}
        totals.append({'method_id': method, 'allocated_cells': len(selected), 'all_status_counts': {s: counts[s] for s in sorted(STATUSES)},
            'captured_certified_supported': sum(c['status'] == 'certified' and c['decision'] == 'supported' for c in selected),
            'captured_certified_unsupported': sum(c['status'] == 'certified' and c['decision'] == 'unsupported' for c in selected),
            'failure_kinds': dict(Counter(c['failure_kind'] for c in selected if c['failure_kind'] is not None)),
            'timeout_kinds': dict(Counter(c['timeout_kind'] for c in selected if c['timeout_kind'] is not None)),
            'unknown_reasons': dict(Counter(c['unknown_reason'] for c in selected if c['unknown_reason'] is not None)),
            'raw_worker_logical_headroom_true_cells': sum(c['raw_worker_logical_headroom_label'] is True for c in selected),
            'independent_logical_headroom_established_cells': sum(c['independent_solver_logical_cap_nonbinding'] is True for c in selected),
            'independent_logical_headroom_classifications': dict(Counter(c['independent_logical_headroom_reason'] for c in selected)),
            'by_status_observed_costs': by_status})
    return {'summary': summary, 'method_totals': totals, 'paired_profile_costs': pairs, 'cells': cells,
            'frozen_runner_summary_verified': frozen_summary,
            'independent_cost_cohorts_differ_from_frozen_runner': summary['paired_costs'] != frozen_summary['paired_costs'],
            'logical_headroom_raw_label_discrepancies': [{'cell': c['cell'], 'decision': c['decision'],
                'status': c['status'], 'meter': c['method_meter'], 'raw_label': c['raw_worker_logical_headroom_label'],
                'independent_label': c['independent_solver_logical_cap_nonbinding'],
                'reason': c['independent_logical_headroom_reason']} for c in cells if c['logical_headroom_raw_label_disagrees']],
            'launched_opening_receipts': len(openings), 'manifest_self_pending_aliases_retained': aliases,
            'profile_families': {p['id']: p['family'] for p in protocol['profiles']}}


def audit(base, output):
    output = Path(output).resolve(); base = Path(base).resolve()
    need(not output.exists() and not output.is_relative_to(base), 'fresh_analysis_output_outside_capture_required')
    capture = Capture(base); analysis = analyze_capture(capture)
    # No output is created until all capture, source, receipt and cohort checks pass.
    output.mkdir(parents=True)
    with (output / 'cells.jsonl').open('x', encoding='utf-8') as stream:
        for row in analysis.pop('cells'): stream.write(canonical(row).decode() + '\n')
    evidence = {'saved_metadata_and_archive': capture.evidence, 'archive_members':
                [dict(path=n, **capture.files[n]) for n in sorted(capture.files)]}
    (output / 'evidence-files.json').write_bytes(canonical(evidence) + b'\n')
    result = {'schema_version': 'common-cost-independent-read-audit/1',
        'status': 'passed_read_only_archive_receipt_and_physical_cost_audit',
        'created_utc': datetime.now(timezone.utc).isoformat(), 'run_id': RUN_ID, 'run_attempt': 1,
        'head_sha': HEAD_SHA, 'workflow_conclusion': capture.run['conclusion'], 'archive_identity': capture.archive_identity,
        'archive_members_verified': len(capture.files), 'frozen_preexecution_files_verified': 1730,
        'new_worker_solver_checker_application_or_provider_executions': 0,
        'certificate_semantics_reexecuted': False,
        'statically_inspected_method_result_reasons': {m: {d: sorted(v) for d, v in decisions.items()} for m, decisions in REASONS.items()},
        'captured_certificate_acceptance_source': 'unchanged independent checker receipt, bound to raw result and lifetime resource closure',
        'comparison_unit': '66 related authored development profiles; five dependent timing repeats per method',
        'limits': ['Authored development inputs are related and are not held out.',
                   'Accepted checker receipts are audited without new semantic certificate execution.',
                   'Recorded interpreter executable identity has no archived executable bytes for separate byte verification.',
                   'Frozen worker headroom labels use only counter < allowance; independent analysis also requires a retained result with a known nonexhaustion reason.',
                   'Linux peak RSS is observed worker lifetime RSS; RLIMIT_AS is the enforced address-space cap.',
                   'Unknown, failed, timed out, stopped and unstarted allocations remain in the census and are excluded from cost ratios.',
                   'Paired profile medians apply only to all-five-repeat same-decision certified nonbinding cohorts; no novelty or superiority assumed.'],
        **analysis, 'auditor_source_identity': dict(path=Path(__file__).as_posix(), **file_identity(__file__)),
        'exports': [dict(path=n, **file_identity(output / n)) for n in ('cells.jsonl', 'evidence-files.json')]}
    with (output / 'result.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False); stream.write('\n')
    return {'status': result['status'], 'allocated_cells': 1650, 'launched_opening_receipts': result['launched_opening_receipts'],
            'certified_contradictions': result['summary']['certified_contradictions'],
            'paired_cohort_profile_counts': {k: v['complete_same_decision_certified_profile_count'] for k, v in result['paired_profile_costs'].items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.base, args.output), sort_keys=True))
