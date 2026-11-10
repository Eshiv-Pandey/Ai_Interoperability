"""One capped pure-profile solve and independent certificate-check attempt."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time


class CpuTimeout(BaseException):
    pass


class WallTimeout(BaseException):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def regular(root, relative):
    path = root / relative
    if (type(relative) is not str or Path(relative).is_absolute() or '..' in Path(relative).parts
            or path.is_symlink() or path.resolve() != path or not path.is_file()):
        raise ValueError('frozen_worker_path_missing_linked_or_outside_root')
    return path


def imported_package(root, alias):
    spec = importlib.util.spec_from_file_location(alias, root / '__init__.py',
                                                  submodule_search_locations=[str(root)])
    package = importlib.util.module_from_spec(spec)
    sys.modules[alias] = package
    spec.loader.exec_module(package)
    return package


def deny_capabilities(event, values):
    if (event.startswith('socket.') or event in {'http.client.connect', 'urllib.Request',
            'subprocess.Popen', 'os.system', 'os.fork', 'os.forkpty', 'os.posix_spawn'}
            or event.startswith('os.spawn') or event.startswith('os.exec')):
        raise PermissionError('common_cost_pure_worker_network_or_descendant_denied')


def run(job_path):
    signal.signal(signal.SIGXCPU, lambda *_: (_ for _ in ()).throw(CpuTimeout()))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(WallTimeout()))
    entry_cpu, entry_wall = time.process_time_ns(), time.perf_counter_ns()
    phases = {}
    reply = {'schema_version': 'common-cost-worker/1', 'status': 'failure',
             'decision': None, 'certificate_valid': None, 'phase_resources': phases}

    def phase(name, callback):
        cpu, wall = time.process_time_ns(), time.perf_counter_ns()
        try:
            return callback()
        finally:
            phases[name] = {'cpu_ns': time.process_time_ns() - cpu,
                            'wall_ns': time.perf_counter_ns() - wall}

    def load():
        job = json.loads(Path(job_path).read_bytes())
        caps = job['caps']
        if (sys.platform != 'linux' or resource.getrlimit(resource.RLIMIT_CPU) !=
                (caps['cpu_soft_seconds'], caps['cpu_hard_seconds'])
                or resource.getrlimit(resource.RLIMIT_AS) != (caps['address_space_bytes'],) * 2
                or not 0 < signal.getitimer(signal.ITIMER_REAL)[0] <= caps['wall_seconds']
                or sys.flags.isolated or sys.flags.ignore_environment or not sys.flags.no_site
                or not sys.flags.safe_path):
            raise ValueError('common_caps_or_seed_honoring_interpreter_flags_not_active')
        if os.environ.get('PYTHONHASHSEED') != str(job['cell']['hash_seed']):
            raise ValueError('declared_common_hash_seed_not_active')
        reply.update(cell=job['cell'], caps_observed=caps)
        root = Path(job['snapshot_root']).resolve()
        for row in job['sources']:
            if identity(regular(root, row['path']).read_bytes()) != {k: row[k] for k in ('bytes', 'sha256')}:
                raise ValueError('frozen_common_source_changed')
        raw = regular(root, job['profile']['path']).read_bytes()
        if identity(raw) != {k: job['profile'][k] for k in ('bytes', 'sha256')}:
            raise ValueError('frozen_common_profile_changed')
        model = json.loads(raw)
        if model['id'] != job['cell']['profile_id'] or model['schema_version'] != 'recipe-continuation/1':
            raise ValueError('common_profile_identity_or_schema_changed')
        reply.update(cell=job['cell'], profile_identity=identity(raw), caps_observed=caps,
                     hash_seed_probe=hash('common-cost-hash-seed-probe'),
                     interpreter_flags={'no_site': sys.flags.no_site, 'safe_path': sys.flags.safe_path,
                                        'isolated': sys.flags.isolated, 'ignore_environment': sys.flags.ignore_environment})
        sys.addaudithook(deny_capabilities)
        return job, root, raw, model

    job = None
    try:
        job, root, raw, model = phase('profile_source_load_and_guard', load)
        before = canonical(model)
        source = root / 'source/interoperability'

        def solve():
            imported_package(source, '_common_cost_solver')
            module = importlib.import_module('_common_cost_solver.' + job['method']['module'].split('.')[-1])
            if Path(module.__file__).resolve() != source / (job['method']['module'].split('.')[-1] + '.py'):
                raise ValueError('solver_import_outside_frozen_package')
            return module.evaluate(model, job['evaluation_clock'], budget=job['caps']['solver_logical_allowance'])

        result = phase('solver_import_and_evaluate', solve)
        if canonical(model) != before:
            raise ValueError('solver_mutated_profile')
        result_raw = phase('solver_result_serialization', lambda: canonical(result))
        if type(result) is not dict or result.get('decision') not in {'supported', 'unsupported', 'unknown'}:
            raise ValueError('invalid_solver_result')
        stats = result.get('stats', {})
        reply.update(decision=result['decision'], solver_result_identity=identity(result_raw),
                     method_meter={'budget': stats.get('budget'), 'work_units': stats.get('work_units'),
                                   'reason': result.get('reason')},
                     solver_logical_cap_nonbinding=(type(stats.get('work_units')) is int
                         and stats.get('budget') == job['caps']['solver_logical_allowance']
                         and stats['work_units'] < stats['budget']))
        if result['decision'] == 'unknown':
            reply['status'] = 'unknown'
            reply['unknown_reason'] = result.get('reason')
        else:
            def check():
                # A different freshly loaded package namespace provides no
                # access to the solver's invocation-local relation caches.
                imported_package(source, '_common_cost_checker')
                checker = importlib.import_module('_common_cost_checker.direct_goal_pruned_v2')
                language = importlib.import_module('_common_cost_checker.refinement_oracle')
                if language.CHECK_BUDGET != job['checker']['preserved_fixed_internal_budget']:
                    raise ValueError('preserved_common_checker_soft_cap_changed')
                check_model, check_result = json.loads(raw), json.loads(result_raw)
                accepted = checker.check_certificate(check_model, check_result, job['evaluation_clock'])
                if canonical(check_model) != before or canonical(check_result) != result_raw:
                    raise ValueError('checker_mutated_profile_or_solver_result')
                return accepted
            accepted = phase('independent_checker_import_and_check', check)
            if type(accepted) is not bool:
                raise ValueError('invalid_common_checker_reply')
            reply['certificate_valid'] = accepted
            reply['checker_internal_cap_nonbinding_for_accepted_proof'] = True if accepted else None
            reply['status'] = 'certified' if accepted else 'failure'
            if not accepted:
                reply['failure_kind'] = 'checker_rejected_or_internal_soft_cap'
        def publish_result():
            path = Path(job_path).parent / 'solver-result.json'
            with path.open('xb') as handle:
                handle.write(result_raw)
                handle.flush()
            return None
        phase('solver_result_output', publish_result)
    except CpuTimeout:
        reply.update(status='timeout', timeout_kind='cpu', decision=None)
    except WallTimeout:
        reply.update(status='timeout', timeout_kind='wall', decision=None)
    except MemoryError:
        reply.update(status='failure', failure_kind='address_space_or_memory_exhaustion', decision=None)
    except Exception as error:
        reply.update(status='failure', failure_kind='worker_exception', error_type=type(error).__name__, decision=None)
    finally:
        # A grace second below the inherited CPU hard limit permits a small
        # closing reply. Full exit CPU/RSS/output costs come from parent wait4.
        signal.setitimer(signal.ITIMER_REAL, 0)
        reply['worker_entry_to_pre_reply_cpu_ns'] = time.process_time_ns() - entry_cpu
        reply['worker_entry_to_pre_reply_wall_ns'] = time.perf_counter_ns() - entry_wall
        reply['peak_rss_before_reply_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        reply['measurement_limit'] = 'Inner observations exclude final reply; wait4 lifetime CPU/RSS and outer wall are primary'
        with (Path(job_path).parent / 'reply.json').open('x', encoding='utf-8') as handle:
            json.dump(reply, handle, sort_keys=True, allow_nan=False)
            handle.write('\n')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    raise SystemExit(run(parser.parse_args().job))
