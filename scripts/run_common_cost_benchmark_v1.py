"""Freeze and retain 1,650 balanced common-cost development allocations."""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'benchmark/common-cost-v1'
WORKER = ROOT / 'scripts/common_cost_worker_v1.py'
METHODS = [('legacy_direct', 'interoperability.refinement_oracle'),
           ('goal_pruned_direct', 'interoperability.direct_goal_pruned_v2'),
           ('original_refinement', 'interoperability.refinement'),
           ('shared_lift', 'interoperability.refinement_shared_lift_v2'),
           ('guard_pruned_direct', 'interoperability.direct_guard_pruned_v3')]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name('.' + path.name + '.pending-' + uuid.uuid4().hex)
    with pending.open('xb') as handle:
        handle.write(canonical(value) + b'\n')
        handle.flush()
        os.fsync(handle.fileno())
    # Atomic, no-clobber publication. Interrupted pending bytes stay retained.
    os.link(pending, path)
    pending.unlink()


def artifact_files(output):
    """Retain interrupted publications without self-inventorying the manifest."""
    output = Path(output)
    manifest = output / 'manifest.json'
    published = manifest.read_bytes() if manifest.is_file() else None
    files = []
    for path in sorted(output.rglob('*')):
        if not path.is_file() or path == manifest:
            continue
        # A post-link interruption can leave the manifest's pending alias.
        # Only an exact retained copy of its published bytes is self-content.
        if (path.parent == output and not path.is_symlink()
                and re.fullmatch(r'\.manifest\.json\.pending-[0-9a-f]{32}', path.name)
                and published is not None and path.read_bytes() == published):
            continue
        files.append(path)
    return files


def regular(root, relative):
    if type(relative) is not str or Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('public_cost_path_outside_snapshot')
    path = root / relative
    if path.is_symlink() or path.resolve() != path or not path.is_file():
        raise ValueError('public_cost_snapshot_path_missing_or_linked')
    return path


def verify_record(root, row):
    if identity(regular(root, row['path']).read_bytes()) != {key: row[key] for key in ('bytes', 'sha256')}:
        raise ValueError('frozen_common_cost_bytes_changed')


def verify_order(protocol, order):
    methods = [row['id'] for row in protocol['methods']]
    profiles = [row['id'] for row in protocol['profiles']]
    if (len(methods) != 5 or len(profiles) != 66 or len(set(methods)) != 5 or len(set(profiles)) != 66
            or protocol['declared_cells'] != 1650 or protocol['repeat_count'] != 5
            or len(order['cells']) != 1650 or len(order['profile_orders']) != 5):
        raise ValueError('exact_66_by_5_by_5_cost_allocation_required')
    rng = random.Random(order['seed'])
    expected_blocks = {}
    for profile in profiles:
        permutation, rotations = list(methods), list(range(5))
        rng.shuffle(permutation); rng.shuffle(rotations)
        expected_blocks[profile] = {'initial_permutation': permutation, 'rotation_for_repeat': rotations}
    if order['method_blocks'] != expected_blocks:
        raise ValueError('balanced_seeded_method_blocks_changed')
    expected = []
    for repeat in range(5):
        ids = list(profiles); rng.shuffle(ids)
        if order['profile_orders'][repeat] != ids:
            raise ValueError('seeded_repeat_profile_order_changed')
        for profile in ids:
            block = expected_blocks[profile]
            shift = block['rotation_for_repeat'][repeat]
            method_order = block['initial_permutation'][shift:] + block['initial_permutation'][:shift]
            seed = 1 + int(hashlib.sha256(f"{order['seed']}|{profile}|{repeat}|hash".encode()).hexdigest()[:16], 16) % (2**32 - 1)
            for position, method in enumerate(method_order):
                expected.append({'index': len(expected), 'id': f'r{repeat+1:02d}--{profile}--{method}',
                                 'profile_id': profile, 'method_id': method, 'repeat': repeat,
                                 'position': position, 'hash_seed': seed})
    if expected != order['cells']:
        raise ValueError('frozen_1650_cell_order_changed')
    return expected


def verify_package(package=PACKAGE):
    package = Path(package).resolve()
    protocol = read(package / 'protocol.json')
    if (protocol['schema_version'] != 'common-cost-protocol/1' or protocol['evaluation_clock'] != 100
            or protocol['caps'] != {'cpu_soft_seconds': 5, 'cpu_hard_seconds': 6, 'wall_seconds': 10,
                'address_space_bytes': 536870912, 'rss_hard_cap_claimed': False, 'solver_logical_allowance': 100000000}
            or protocol['checker']['module'] != 'interoperability.direct_goal_pruned_v2'
            or protocol['checker']['preserved_fixed_internal_budget'] != 2000000
            or protocol['child_flags'] != ['-S', '-P', '-B']
            or [(m['id'], m['module']) for m in protocol['methods']] != METHODS):
        raise ValueError('declared_common_cost_protocol_changed')
    verify_record(package, protocol['order'])
    for row in protocol['sources'] + protocol['profiles']:
        verify_record(package, row)
    for method in protocol['methods']:
        path = 'source/' + method['module'].replace('.', '/') + '.py'
        tree = ast.parse(regular(package, path).read_bytes())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'evaluate')
        if [arg.arg for arg in function.args.args] != ['profile', 'now', 'budget']:
            raise ValueError('frozen_method_evaluate_API_changed')
    checker_tree = ast.parse(regular(package, 'source/interoperability/direct_goal_pruned_v2.py').read_bytes())
    checker = next(node for node in checker_tree.body if isinstance(node, ast.FunctionDef) and node.name == 'check_certificate')
    if [arg.arg for arg in checker.args.args] != ['profile', 'result', 'now']:
        raise ValueError('frozen_checker_API_changed')
    order = read(package / 'order.json')
    return protocol, verify_order(protocol, order)


def prepare(output, package=PACKAGE):
    output, package = Path(output).resolve(), Path(package).resolve()
    if output.exists():
        raise FileExistsError('fresh_common_cost_allocation_required')
    protocol, cells = verify_package(package)
    output.mkdir(parents=True)
    files = [dict(path='protocol.json', **identity((package / 'protocol.json').read_bytes())), protocol['order'],
             *protocol['profiles'], *protocol['sources']]
    snapshot_records = []
    for row in files:
        source = regular(package, row['path']); target = output / 'snapshot' / row['path']
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(source.read_bytes())
        snapshot_records.append(dict(path='snapshot/' + row['path'], **identity(target.read_bytes())))
    for source in [WORKER, Path(__file__).resolve()]:
        target = output / 'driver' / source.name; target.parent.mkdir(exist_ok=True)
        target.write_bytes(source.read_bytes()); snapshot_records.append(dict(path='driver/' + source.name, **identity(target.read_bytes())))
    for key, filename in [('source_suite', 'prior-suite.json'), ('source_input_manifest', 'prior-input-manifest.json')]:
        row = protocol[key]; raw = regular(ROOT, row['original_path']).read_bytes()
        if identity(raw) != {k: row[k] for k in ('bytes', 'sha256')}:
            raise ValueError('prior_common_cost_provenance_changed')
        target = output / 'snapshot/provenance' / filename; target.parent.mkdir(exist_ok=True)
        target.write_bytes(raw); snapshot_records.append(dict(path=target.relative_to(output).as_posix(), **identity(raw)))
    methods = {row['id']: row for row in protocol['methods']}
    profiles = {row['id']: row for row in protocol['profiles']}
    for cell in cells:
        job = {'schema_version': 'common-cost-job/1', 'cell': cell, 'snapshot_root': str(output / 'snapshot'),
               'profile': profiles[cell['profile_id']], 'method': methods[cell['method_id']],
               'sources': protocol['sources'], 'checker': protocol['checker'],
               'caps': protocol['caps'], 'evaluation_clock': protocol['evaluation_clock']}
        path = output / 'cells' / cell['id'] / 'job.json'; write(path, job)
        snapshot_records.append(dict(path=path.relative_to(output).as_posix(), **identity(path.read_bytes())))
    allocation = {'schema_version': 'common-cost-allocation/1', 'created_utc': datetime.now(timezone.utc).isoformat(),
                  'declared_cells': 1650, 'cells': cells, 'frozen_files': snapshot_records,
                  'protocol_identity': identity((package / 'protocol.json').read_bytes()),
                  'order_identity': identity((package / 'order.json').read_bytes()),
                  'runtime': {'python': sys.version, 'platform': sys.platform, 'executable': sys.executable,
                              'executable_identity': identity(Path(sys.executable).read_bytes())},
                  'all_input_source_order_and_job_hashes_frozen_before_execution': True,
                  'new_application_or_provider_runs': 0}
    write(output / 'allocation.json', allocation)
    return allocation


def verify_allocation(output):
    output = Path(output).resolve(); allocation = read(output / 'allocation.json')
    if allocation['schema_version'] != 'common-cost-allocation/1' or allocation['declared_cells'] != 1650:
        raise ValueError('common_cost_allocation_contract_changed')
    for row in allocation['frozen_files']:
        verify_record(output, row)
    protocol, cells = verify_package(output / 'snapshot')
    if (allocation['cells'] != cells or identity((output / 'snapshot/protocol.json').read_bytes()) != allocation['protocol_identity']
            or identity((output / 'snapshot/order.json').read_bytes()) != allocation['order_identity']):
        raise ValueError('common_cost_frozen_allocation_changed')
    return allocation, protocol


def child_caps(caps):
    import resource
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (caps['cpu_soft_seconds'], caps['cpu_hard_seconds']))
    resource.setrlimit(resource.RLIMIT_AS, (caps['address_space_bytes'],) * 2)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.setitimer(signal.ITIMER_REAL, caps['wall_seconds'])


def owned_process(command, environment, folder, caps):
    """One terminal wait4 owner; never poll/wait/communicate on Popen."""
    if sys.platform != 'linux' or not hasattr(os, 'wait4'):
        raise ValueError('common_cost_execution_requires_hosted_linux_wait4')
    import threading
    if threading.active_count() != 1:
        raise ValueError('common_cost_preexec_requires_single_threaded_parent')
    tick = time.perf_counter_ns(); killed_for_wall = False; interruption = None; cleanup_error = None
    with (folder / 'stdout.bin').open('xb') as stdout, (folder / 'stderr.bin').open('xb') as stderr:
        process = subprocess.Popen(command, cwd=folder, env=environment, stdin=subprocess.DEVNULL,
                                   stdout=stdout, stderr=stderr, start_new_session=True,
                                   preexec_fn=lambda: child_caps(caps))
        try:
            while True:
                # WNOWAIT holds the direct child PID until group cleanup;
                # terminal rusage is reaped exactly once, only with wait4.
                observed = os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                if observed is not None:
                    break
                if not killed_for_wall and time.perf_counter_ns() - tick >= caps['wall_seconds'] * 1000000000:
                    killed_for_wall = True
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                time.sleep(0.002)
        except BaseException as error:
            interruption = type(error).__name__
        finally:
            # Also close any unexpected group descendants on a normal or
            # signal exit, while the unreaped PID still identifies our group.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError as error:
                cleanup_error = type(error).__name__
                try:
                    os.kill(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            while True:
                try:
                    pid, status, usage = os.wait4(process.pid, 0)
                    break
                except InterruptedError:
                    continue
        process.returncode = os.waitstatus_to_exitcode(status)
    return {'returncode': process.returncode, 'wait_status': status,
            'pid': process.pid, 'owned_process_group': process.pid, 'wall_cap_kill_requested': killed_for_wall,
            'outer_wall_ns': time.perf_counter_ns() - tick,
            'cpu_user_ns': round(usage.ru_utime * 1000000000), 'cpu_system_ns': round(usage.ru_stime * 1000000000),
            'cpu_total_ns': round((usage.ru_utime + usage.ru_stime) * 1000000000),
            'peak_rss_bytes': int(usage.ru_maxrss) * 1024,
            'resource_source': 'sole terminal os.wait4 per-child rusage after termination',
            'owned_group_cleanup_requested_before_terminal_reap': True,
            'parent_interruption_type': interruption,
            'group_cleanup_error_type': cleanup_error,
            'caps_applied_before_exec': caps}


def closed_row(folder, cell):
    after = folder / 'after.json'; before = folder / 'before.json'
    if after.exists():
        try:
            row = read(after)
            if type(row) is not dict or row.get('cell') != cell or not before.exists():
                raise ValueError('closing_common_cost_receipt_identity_changed')
            return row
        except (OSError, ValueError, KeyError, TypeError):
            return {'cell': cell, 'status': 'failure', 'decision': None, 'certificate_valid': None,
                    'resources': None, 'failure_kind': 'malformed_or_unbound_closing_receipt',
                    'retained_closing_identity': identity(after.read_bytes())}
    return {'cell': cell, 'status': 'stopped_without_closing_receipt' if before.exists() else 'not_started',
            'decision': None, 'certificate_valid': None, 'resources': None}


def summarize(rows, methods):
    counts = {method: dict(Counter(row['status'] for row in rows if row['cell']['method_id'] == method)) for method in methods}
    indexed = {(r['cell']['profile_id'], r['cell']['repeat'], r['cell']['method_id']): r for r in rows}
    groups = defaultdict(list)
    profile_verdicts = defaultdict(set)
    probes = defaultdict(set)
    for row in rows:
        if row.get('hash_seed_probe') is not None:
            probes[(row['cell']['profile_id'], row['cell']['repeat'])].add(row['hash_seed_probe'])
        if row['status'] == 'certified':
            groups[(row['cell']['profile_id'], row['cell']['repeat'])].append(row)
            profile_verdicts[row['cell']['profile_id']].add(row['decision'])
    contradictions = [dict(profile_id=p, verdicts=sorted(v)) for p, v in profile_verdicts.items() if len(v) > 1]
    complete_all_method = sum(len(group) == 5 and len({row['decision'] for row in group}) == 1 for group in groups.values())
    pairs = {}
    profiles = sorted({r['cell']['profile_id'] for r in rows})
    for left, right in itertools.combinations(methods, 2):
        complete = []
        for profile in profiles:
            left_rows, right_rows = [], []
            for repeat in range(5):
                a, b = indexed[(profile, repeat, left)], indexed[(profile, repeat, right)]
                if (a['status'] != 'certified' or b['status'] != 'certified' or a['decision'] != b['decision']
                        or not a.get('solver_logical_cap_nonbinding') or not b.get('solver_logical_cap_nonbinding')
                        or not a.get('resources') or not b.get('resources')):
                    break
                left_rows.append(a); right_rows.append(b)
            if (len(left_rows) != 5 or len({r['decision'] for r in left_rows + right_rows}) != 1
                    or profile in {row['profile_id'] for row in contradictions}
                    or any(r['resources']['cpu_total_ns'] >= 5000000000
                           or r['resources']['outer_wall_ns'] >= 10000000000 for r in left_rows + right_rows)):
                continue
            item = {'profile_id': profile, 'paired_repeats': 5}
            for field in ['cpu_total_ns', 'outer_wall_ns', 'peak_rss_bytes']:
                a = statistics.median(r['resources'][field] for r in left_rows)
                b = statistics.median(r['resources'][field] for r in right_rows)
                item[field] = {'left_median': a, 'right_median': b, 'left_over_right': a / b if b > 0 else None}
            complete.append(item)
        pairs[left + '__' + right] = {'complete_same_decision_certified_profile_count': len(complete),
                                     'required_paired_repeats_per_profile': 5, 'per_profile': complete}
    return {'allocated_cells': len(rows), 'by_method_status_counts': counts,
            'hash_seed_probe_disagreements': [{'profile_id': p, 'repeat': r} for (p, r), values in probes.items() if len(values) > 1],
            'certified_contradictions': contradictions, 'all_five_method_certified_same_decision_profile_repeat_blocks': complete_all_method,
            'paired_costs': pairs, 'comparison_unit': '66 related authored profiles; five dependent timing replicates',
            'adverse_allocations_excluded_from_cost_ratios_but_retained_in_status_denominator': True,
            'no_novelty_or_superiority_assumed': True}


def finalize(output):
    output = Path(output).resolve(); allocation = read(output / 'allocation.json')
    if allocation.get('schema_version') != 'common-cost-allocation/1' or len(allocation.get('cells', [])) != 1650:
        raise ValueError('retained_1650_cost_allocation_required')
    integrity_error = None
    try:
        allocation, protocol = verify_allocation(output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        integrity_error = type(error).__name__
    rows = [closed_row(output / 'cells' / cell['id'], cell) for cell in allocation['cells']]
    summary = summarize(rows, [m[0] for m in METHODS])
    if integrity_error:
        summary['paired_costs'] = {}
        summary['source_integrity_error_type'] = integrity_error
        summary['certified_cost_cohorts_usable'] = False
    else:
        summary['certified_cost_cohorts_usable'] = True
    result_path = output / 'results.json'
    if result_path.exists():
        result = read(result_path)
        if (result['cells'] != rows or result['summary'] != summary
                or result['frozen_integrity_verified'] is not (integrity_error is None)
                or result['allocation_identity'] != identity((output / 'allocation.json').read_bytes())):
            raise ValueError('completed_common_cost_results_changed')
    else:
        result = {'schema_version': 'common-cost-results/1', 'cells': rows, 'summary': summary,
                  'frozen_integrity_verified': integrity_error is None,
                  'allocation_identity': identity((output / 'allocation.json').read_bytes())}
        write(result_path, result)
    if not (output / 'manifest.json').exists():
        write(output / 'manifest.json', {'files': [dict(path=p.relative_to(output).as_posix(), **identity(p.read_bytes()))
              for p in artifact_files(output)]})
    return result


def execute(output):
    output = Path(output).resolve(); allocation, protocol = verify_allocation(output)
    if sys.platform != 'linux' or sys.version_info[:3] != (3, 13, 1):
        raise ValueError('pinned_linux_python_3_13_1_required_for_common_cost_execution')
    if allocation['runtime']['executable_identity'] != identity(Path(sys.executable).read_bytes()):
        raise ValueError('frozen_common_cost_python_executable_changed')
    write(output / 'execution-start.json', {'created_utc': datetime.now(timezone.utc).isoformat(),
          'allocation_identity': identity((output / 'allocation.json').read_bytes()), 'one_serial_hosted_runner': True})
    records = {row['path']: row for row in allocation['frozen_files']}
    common_records = [row for row in allocation['frozen_files'] if row['path'].startswith('driver/')
                      or row['path'].startswith('snapshot/source/') or row['path'] in {'snapshot/protocol.json', 'snapshot/order.json'}]
    profiles = {p['id']: p for p in protocol['profiles']}
    try:
        for cell in allocation['cells']:
            folder = output / 'cells' / cell['id']; job = folder / 'job.json'
            # The complete allocation was verified before starting. Recheck
            # common code/order plus this exact profile/job before dispatch.
            for record in common_records + [records[job.relative_to(output).as_posix()],
                    records['snapshot/' + profiles[cell['profile_id']]['path']]]:
                verify_record(output, record)
            command = [sys.executable, *protocol['child_flags'], str(output / 'driver/common_cost_worker_v1.py'), '--job', str(job)]
            environment = {key: os.environ[key] for key in ('PATH', 'LD_LIBRARY_PATH') if key in os.environ}
            environment.update(PYTHONHASHSEED=str(cell['hash_seed']), LANG='C.UTF-8', LC_ALL='C.UTF-8', TZ='UTC')
            write(folder / 'before.json', {'cell': cell, 'job_identity': identity(job.read_bytes()), 'argv': command,
                  'hash_seed': cell['hash_seed'], 'caps': protocol['caps'], 'started_utc': datetime.now(timezone.utc).isoformat()})
            resources = None
            try:
                resources = owned_process(command, environment, folder, protocol['caps'])
                row = {'cell': cell, 'status': 'failure', 'decision': None, 'certificate_valid': None, 'resources': resources}
                if resources['parent_interruption_type'] or resources['group_cleanup_error_type']:
                    row.update(status='stopped', failure_kind='parent_interruption_or_group_cleanup_error')
                elif resources['wall_cap_kill_requested'] or resources['returncode'] == -signal.SIGALRM:
                    row.update(status='timeout', timeout_kind='wall')
                elif resources['returncode'] == -signal.SIGXCPU:
                    row.update(status='timeout', timeout_kind='cpu_soft')
                elif resources['returncode'] == -signal.SIGKILL:
                    row.update(status='failure', failure_kind='SIGKILL_cpu_hard_or_external_cause_unattributed')
                elif resources['returncode'] == 0:
                    reply = read(folder / 'reply.json') if (folder / 'reply.json').exists() else None
                    if type(reply) is not dict or reply.get('cell') != cell or reply.get('caps_observed') != protocol['caps']:
                        raise ValueError('missing_or_invalid_common_cost_worker_reply')
                    row.update({key: value for key, value in reply.items() if key not in {'schema_version', 'cell', 'resources'}})
                    if row['status'] == 'certified' and (row['certificate_valid'] is not True or row['decision'] not in {'supported', 'unsupported'}):
                        raise ValueError('invalid_common_cost_certified_reply')
                else:
                    row['failure_kind'] = 'nonzero_or_missing_invalid_worker_reply'
                write(folder / 'after.json', row)
                if row['status'] == 'stopped':
                    break
            except Exception as error:
                write(folder / 'after.json', {'cell': cell, 'status': 'failure', 'decision': None,
                      'certificate_valid': None, 'resources': resources, 'failure_kind': 'launch_or_receipt_exception',
                      'error_type': type(error).__name__})
                if resources is None:
                    break
            if (cell['index'] + 1) % 50 == 0:
                print(json.dumps({'closed_allocations': cell['index'] + 1, 'declared_cells': 1650}), flush=True)
    finally:
        result = finalize(output)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare-only', action='store_true')
    mode.add_argument('--execute-prepared', action='store_true')
    mode.add_argument('--finalize-only', action='store_true')
    mode.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    if args.prepare_only:
        value = prepare(args.output)
        print(json.dumps({'declared_cells': value['declared_cells'], 'execution_started': False}))
    elif args.execute_prepared:
        value = execute(args.output); print(json.dumps(value['summary'], sort_keys=True))
    elif args.finalize_only:
        value = finalize(args.output); print(json.dumps(value['summary'], sort_keys=True))
    else:
        output = args.output.resolve(); verify_allocation(output)
        manifest = read(output / 'manifest.json')
        for row in manifest['files']:
            verify_record(output, row)
        names = {p.relative_to(output).as_posix() for p in artifact_files(output)}
        if names != {r['path'] for r in manifest['files']}:
            raise ValueError('common_cost_artifact_membership_changed')
        value = read(output / 'results.json')
        rows = [closed_row(output / 'cells' / c['id'], c) for c in read(output / 'allocation.json')['cells']]
        expected = summarize(rows, [m[0] for m in METHODS]); expected['certified_cost_cohorts_usable'] = True
        if value['cells'] != rows or value['summary'] != expected or not value['frozen_integrity_verified']:
            raise ValueError('common_cost_derived_results_changed')
        print(json.dumps({'declared_cells': len(rows), 'artifact_verified': True}))
    if not args.prepare_only:
        if args.verify_only:
            return 0
        return 1 if any(row['status'] in {'not_started', 'stopped', 'stopped_without_closing_receipt'} for row in value['cells']) else 0
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
