"""Independently reconcile captured matrix bytes; never import or run solvers."""
from pathlib import Path, PurePosixPath
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse
import hashlib
import json


ROOT = Path(__file__).resolve().parents[4]
BOOT = 'import sys; sys.path.insert(0, sys.argv[1]); from interoperability.benchmark import _worker; _worker(sys.argv[2])'
LEGACY = 'interoperability.refinement_oracle'
PRUNED = 'interoperability.direct_goal_pruned_v2'


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('Nonfinite JSON value: ' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def audit(run, output):
    run, output = run.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError('Preserve previous independent audit')
    plan_name = 'plan-v2.json' if run.name == 'v1' else 'plan.json'
    if not (run / 'result.json').is_file():
        raise ValueError('Matrix must finish before this audit is run')
    started = datetime.now(timezone.utc).isoformat()
    cache = {}
    for path in sorted(run.rglob('*')):
        if 'independent-review' in path.relative_to(run).parts or path.name == 'independent-audit.json':
            continue
        if path.is_symlink():
            raise ValueError('Nonregular evidence path: ' + str(path))
        if path.is_file():
            cache[path.resolve()] = path.read_bytes()
    def raw(path):
        path = path.resolve()
        return cache[path] if path in cache else path.read_bytes()
    def load(path):
        return decode(raw(path))
    def record(path, base=run):
        data = raw(path)
        return {'path': path.resolve().relative_to(base.resolve()).as_posix(), 'bytes': len(data), 'sha256': digest(data)}
    before = [record(path) for path in cache]
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)
    def verify(base, item):
        relative = PurePosixPath(item['path'])
        if relative.is_absolute() or '..' in relative.parts or str(relative) != item['path']:
            raise ValueError('Unsafe manifest path: ' + item['path'])
        require(record(base / item['path'], base) == item, 'Changed captured file: ' + str(base / item['path']))
    plan, execution, matrix = (load(run / name) for name in (plan_name, 'execution.json', 'result.json'))
    require(execution['plan'] == matrix['plan'] == record(run / plan_name), 'Matrix executed-plan hash differs')
    require(plan['budgets'] == [32, 256, 4096, 100000] and plan['case_count'] == 66, 'Unexpected matrix allocation')
    require(matrix['status'] == 'passed' and not matrix['errors'], 'Matrix did not finish successfully; all retained outcomes are still audited')
    require(matrix['frozen_inputs_package_and_plan_unchanged'] is True, 'Matrix reports changed frozen inputs')
    require(plan['created_at_utc'] <= execution['started_at_utc'] <= matrix['finished_at_utc'], 'Matrix chronology differs')
    for item in plan['files'] + [plan['driver']] + [a['plan'] for a in plan['allocations']]:
        verify(run, item)
    if run.name == 'v1':
        verify(run, plan['supersedes_unexecuted_plan'])
        old = load(run / 'plan.json')
        verify(run, old['driver'])
        require(plan['files'] == old['files'] and plan['allocations'] == old['allocations'], 'Static correction changed v1 inputs or allocations')
    else:
        verify(ROOT, plan['previous_plan'])
        for item in plan['identical_previous_inputs']:
            verify(run, item)
            verify(run.parent / 'v1', item)
    source_unchanged = True
    for item in plan['original_package']:
        current = record(ROOT / item['path'], ROOT)
        source_unchanged &= current == item
    if 'generator_original' in plan:
        item = plan['generator_original']
        source_unchanged &= record(ROOT / item['path'], ROOT) == item
    require(source_unchanged, 'Originally pinned current package/generator files changed')
    declared, suite = load(run / 'inputs/manifest.json'), load(run / 'inputs/suite.json')
    for item in declared['files']:
        verify(run / 'inputs', item)
    profiles = {item['profile_id']: item for item in declared['cases']}
    require(len(profiles) == len(declared['cases']) == len(suite['cases']) == 66, 'Profile accounting differs')
    require(suite['evaluation_clock'] == 100 and suite['split'] == 'development', 'Suite clock or split differs')
    for item, entry in zip(declared['cases'], suite['cases']):
        verify(run / 'inputs', item['input'])
        require(entry == {'path': item['input']['path'], 'family': item['family']}, 'External suite label differs')
    methods = {'baseline': LEGACY, 'candidate': 'interoperability.refinement'}
    if run.name == 'v2':
        methods = {'baseline': LEGACY, 'direct_pruned': PRUNED, 'candidate': 'interoperability.refinement'}
    checker_module = PRUNED if run.name == 'v2' else LEGACY
    budgets, all_statuses, all_codes = {}, Counter(), Counter()
    total_jobs = total_certificates = rejected_certificates = 0
    worker_stderr, contradictions, legacy_differences = [], [], []
    artifacts = [record(run / name) for name in (plan_name, 'execution.json', 'result.json', 'inputs/manifest.json')]
    prior_finish = execution['started_at_utc']
    for allocation in plan['allocations']:
        budget = allocation['budget']; label = 'budget-' + str(budget); bundle = run / label
        allocated = load(run / allocation['plan']['path']); invocation = (run / allocation['plan']['path']).parent
        require(allocated['budget'] == budget and allocated['maximum_attempts'] == 1, label + ': allocation differs')
        for kind in ('benchmark', 'verify'):
            receipt = load(invocation / (kind + '.receipt.json'))
            start = load(invocation / (kind + '.started.json'))
            require(receipt['argv'] == allocated[kind + '_argv'] and receipt['cwd'] == str(run)
                    and receipt['environment_overrides'] == allocated['environment_overrides'], label + ': invocation differs')
            require(all(receipt[k] == v for k, v in start.items() if k not in ('returncode', 'timed_out')), label + ': started receipt differs')
            require(receipt['returncode'] == 0 and receipt['timed_out'] is False, label + ': invocation failed')
            require(prior_finish <= receipt['started_at_utc'] <= receipt['finished_at_utc'], label + ': invocation ordering differs')
            prior_finish = receipt['finished_at_utc']
            for item in receipt['streams']:
                verify(run, item)
            verify(run, matrix['budgets'][str(budget)][kind])
        manifest, executed, summary = (load(bundle / name) for name in ('manifest.json', 'execution.json', 'summary.json'))
        listed = {item['path'] for item in manifest['files']}
        actual = {p.relative_to(bundle).as_posix() for p in cache if p.is_relative_to(bundle) and p != bundle / 'manifest.json'}
        require(len(listed) == len(manifest['files']) and listed == actual, label + ': bundle inventory differs')
        require(manifest['bytes'] == sum(item['bytes'] for item in manifest['files']), label + ': bundle byte count differs')
        for item in manifest['files']:
            verify(bundle, item)
        for item in executed['captured_inputs']:
            verify(bundle, item)
        require(executed['work_budget'] == budget and executed['evaluation_clock'] == 100 and executed['timeout_seconds'] == 30,
                label + ': worker configuration differs')
        require(executed['schema_adapter'] == {'baseline': LEGACY, 'reference': LEGACY, 'checker': checker_module, 'supports_budget': True},
                label + ': advertised checker differs')
        require({a['name']: a['module'] for a in executed['algorithms']} == methods, label + ': advertised methods differ')
        require(executed['live_application_runs'] == executed['live_model_calls'] == 0, label + ': unexpected live execution')
        for path in (run / 'source/interoperability').glob('*.py'):
            require(raw(bundle / 'source/interoperability' / path.name) == raw(path), label + ': frozen code differs ' + path.name)
        require(raw(bundle / 'inputs/original-suite.json') == raw(run / 'inputs/suite.json'), label + ': suite bytes differ')
        rows = [decode(line) for line in raw(bundle / 'results.jsonl').splitlines()]
        require(len(rows) == 66 and {row['case_id'] for row in rows} == set(profiles), label + ': result cases differ')
        used_jobs, invocations = set(), defaultdict(list)
        counts = {name: Counter() for name in ('reference', *methods)}
        reasons = {name: Counter() for name in counts}
        families, comparisons = {}, []
        def worker(job_name, aggregate, profile, profile_hash, role, result=None):
            job = bundle / 'jobs' / job_name; used_jobs.add(job_name)
            request, process, reply = (load(job / name) for name in ('input.json', 'process.json', 'reply.json'))
            require({**reply, 'process': process} == aggregate, label + ': worker aggregate differs ' + job_name)
            require(request['runtime_manifest'] == profile and request['now'] == 100, label + ': unequal worker input ' + job_name)
            require(request['reply_path'] == str(job / 'reply.json'), label + ': reply path differs ' + job_name)
            require(process['argv'] == [plan['python']['executable'], '-I', '-S', '-B', '-c', BOOT, str(bundle / 'source'), str(job / 'input.json')],
                    label + ': worker launch differs ' + job_name)
            require(process['returncode'] == 0 and process['timed_out'] is False and reply['status'] == 'returned', label + ': worker failed ' + job_name)
            require(reply['input_unchanged'] is True and reply['input_sha256_before'] == reply['input_sha256_after'] == profile_hash,
                    label + ': worker input changed ' + job_name)
            if role == 'certificate':
                require(request['kind'] == 'certificate' and request['module'] == checker_module and request['entrypoint'] == 'check_certificate'
                        and request['result'] == result and 'keyword_arguments' not in request, label + ': certificate dispatch differs ' + job_name)
            else:
                module = LEGACY if role == 'reference' else methods[role]
                require(request['kind'] == 'evaluate' and request['module'] == module and request['entrypoint'] == 'evaluate'
                        and request['keyword_arguments'] == {'budget': budget}, label + ': evaluation dispatch differs ' + job_name)
                require(reply['result']['stats']['budget'] == budget and 0 <= reply['result']['stats']['work_units'] <= budget,
                        label + ': work budget violated ' + job_name)
            require(set(p.name for p in job.iterdir()) == {'input.json', 'process.json', 'reply.json', 'stdout.bin', 'stderr.bin'},
                    label + ': job inventory differs ' + job_name)
            all_statuses[reply['status']] += 1; all_codes[str(process['returncode'])] += 1
            if raw(job / 'stderr.bin'):
                worker_stderr.append(str(job.relative_to(run)))
            return aggregate
        previous_rows = {}
        if run.name == 'v2':
            previous_rows = {row['case_id']: row for row in [decode(line) for line in (run.parent / 'v1' / label / 'results.jsonl').read_bytes().splitlines()]}
            for name in ('refinement_oracle.py', 'refinement.py', 'benchmark.py', 'oracle.py'):
                require(raw(bundle / 'source/interoperability' / name) == (run.parent / 'v1' / label / 'source/interoperability' / name).read_bytes(),
                        label + ': legacy source differs from v1 ' + name)
        for index, row in enumerate(rows):
            cid = row['case_id']; external = profiles[cid]; profile = load(run / 'inputs' / external['input']['path']); hashed = digest(canonical(profile))
            require(row['model_sha256'] == hashed and row['family'] == external['family'] and row['evaluation_clock'] == 100,
                    label + ': row identity differs ' + cid)
            require(raw(bundle / row['input_snapshot']) == raw(run / 'inputs' / external['input']['path']), label + ': copied profile bytes differ ' + cid)
            require(set(row['algorithms']) == set(methods) and row['reference_valid'] is True, label + ': method or reference accounting differs ' + cid)
            ref = worker(f'case-{index:04d}-reference', row['reference'], profile, hashed, 'reference')
            ref_decision = ref['result']['decision']; counts['reference'][ref_decision] += 1
            reasons['reference'][ref['result']['reason']] += 1; invocations['reference'].append(ref)
            comparison = {'case_id': cid, 'family': external['family'], 'scenario': external['scenario'],
                          'external_authored_expectation': external['expected_decision_with_sufficient_budget'], 'reference': ref_decision, 'methods': {}}
            for name in methods:
                arm = row['algorithms'][name]
                ex = worker(f'case-{index:04d}-{name}', arm['execution'], profile, hashed, name)
                decision = ex['result']['decision']; counter = counts[name]
                require(arm['status'] == 'recorded' and arm['valid_result'] is True and decision in ('supported', 'unsupported', 'unknown'),
                        label + ': invalid recorded result ' + cid + '/' + name)
                counter[decision] += 1; reasons[name][ex['result']['reason']] += 1; invocations[name].append(ex)
                require(arm['decision_agreement'] == (decision == ref_decision), label + ': agreement flag differs ' + cid)
                counter['decision_agreements'] += decision == ref_decision
                counter['conclusive_on_reference_unknown'] += decision != 'unknown' and ref_decision == 'unknown'
                counter['abstained_on_reference_decided'] += decision == 'unknown' and ref_decision != 'unknown'
                counter['false_support'] += decision == 'supported' and ref_decision == 'unsupported'
                counter['false_refusal'] += decision == 'unsupported' and ref_decision == 'supported'
                if decision != 'unknown':
                    counter['conclusive'] += 1
                    cert = worker(f'case-{index:04d}-{name}-certificate', arm['certificate_check'], profile, hashed, 'certificate', ex['result'])
                    invocations[name + '-certificate'].append(cert)
                    counter['certificates_valid'] += cert['result'] is True
                    counter['certificates_invalid'] += cert['result'] is False
                    require(arm['certificate_valid'] is cert['result'], label + ': certificate flag differs ' + cid)
                    if decision != external['expected_decision_with_sufficient_budget']:
                        contradictions.append({'budget': budget, 'case_id': cid, 'method': name, 'decision': decision})
                else:
                    require(arm.get('certificate_valid') is None and 'certificate_check' not in arm, label + ': unknown has a certificate ' + cid)
                families.setdefault(external['family'], {}).setdefault(name, Counter())[decision] += 1
                comparison['methods'][name] = {'decision': decision, 'reason': ex['result']['reason'], 'certificate_valid': arm.get('certificate_valid')}
                if previous_rows and name in ('baseline', 'candidate'):
                    old = previous_rows[cid]['algorithms'][name]['execution']['result']
                    def semantic(result):
                        return {k: ({x: y for x, y in value.items() if x != 'elapsed_ns'} if k == 'stats' else value)
                                for k, value in result.items()}
                    if semantic(old) != semantic(ex['result']) or previous_rows[cid]['model_sha256'] != hashed:
                        legacy_differences.append({'budget': budget, 'case_id': cid, 'method': name})
            comparisons.append(comparison)
        require(used_jobs == {p.name for p in (bundle / 'jobs').iterdir()}, label + ': unaccounted worker directories')
        total_jobs += len(used_jobs)
        def timing(actual, values, name):
            require(actual['invocations'] == len(values), label + ': timing call count differs ' + name)
            for field in ('evaluation_ns', 'worker_body_ns', 'worker_wall_ns'):
                samples = [v['process'][field] if field == 'worker_wall_ns' else v[field] for v in values]
                observed = actual[field]
                require(observed['observed'] == len(samples) and observed['missing'] == 0 and observed['total'] == sum(samples)
                        and sorted(observed['samples']) == sorted(samples), label + ': timing differs ' + name + '/' + field)
        timing(summary['reference_timing'], invocations['reference'], 'reference')
        timing(summary['all_invocation_timing'], [v for values in invocations.values() for v in values], 'all')
        summaries = {}
        for name in methods:
            observed, counter = summary['algorithms'][name], counts[name]
            for field in ('supported', 'unsupported', 'unknown', 'conclusive', 'certificates_valid', 'certificates_invalid', 'decision_agreements',
                          'conclusive_on_reference_unknown', 'abstained_on_reference_decided', 'false_support', 'false_refusal'):
                require(observed[field] == counter[field], label + ': summary differs ' + name + '/' + field)
            require(observed['scheduled'] == observed['eligible'] == observed['returned_valid'] == 66 and observed['errors'] == 0
                    and observed['certificate_check_errors'] == 0, label + ': summary worker status differs ' + name)
            require(observed['certified_coverage'] == counter['certificates_valid'] / 66, label + ': certified coverage differs ' + name)
            timing(observed['certificate_timing'], invocations[name + '-certificate'], name + '/certificate')
            timing(observed['evaluation_and_certificate_timing'], invocations[name] + invocations[name + '-certificate'], name + '/combined')
            summaries[name] = {**dict(counter), 'reasons': dict(reasons[name]), 'certified_coverage': counter['certificates_valid'] / 66}
            total_certificates += len(invocations[name + '-certificate']); rejected_certificates += counter['certificates_invalid']
            for field in ('supported', 'unsupported', 'unknown', 'conclusive', 'certificates_valid', 'decision_agreements'):
                require(matrix['budgets'][str(budget)]['algorithms'][name][field] == counter[field], label + ': outer matrix count differs')
        for family, values in families.items():
            for name, counter in values.items():
                require(matrix['budgets'][str(budget)]['families'][family][name]['decisions'] == dict(counter), label + ': family aggregate differs')
        require(summary['status'] == 'passed' and summary['cases'] == 66 and summary['reference_errors'] == 0
                and summary['snapshot_inputs_unchanged'] is True and summary['original_inputs_unchanged'] is True, label + ': summary status differs')
        pairwise = Counter()
        if 'direct_pruned' in methods:
            for row in comparisons:
                pairwise[row['methods']['candidate']['decision'] + '/' + row['methods']['direct_pruned']['decision']] += 1
        budgets[str(budget)] = {'cases': 66, 'jobs': len(used_jobs), 'certificate_checks': sum(len(invocations[n + '-certificate']) for n in methods),
                               'manifest_files_verified': len(listed), 'manifest_bytes_verified': manifest['bytes'], 'methods': summaries,
                               'reference_decisions': dict(counts['reference']), 'reference_reasons': dict(reasons['reference']),
                               'candidate_by_pruned_decision': dict(pairwise), 'family_decisions': families, 'case_comparisons': comparisons}
        artifacts.extend(record(bundle / name) for name in ('manifest.json', 'execution.json', 'summary.json', 'results.jsonl'))
    require(prior_finish <= matrix['finished_at_utc'], 'Final invocation exceeds matrix finish')
    require(not contradictions, 'Conclusive result contradicts external authored expectation')
    require(not legacy_differences, 'Legacy method changed outcome on identical v1 input')
    after = []
    for path in sorted(run.rglob('*')):
        if 'independent-review' in path.relative_to(run).parts or path.name == 'independent-audit.json':
            continue
        if path.is_file():
            data = path.read_bytes()
            after.append({'path': path.relative_to(run).as_posix(), 'bytes': len(data), 'sha256': digest(data)})
    require(before == after, 'Retained matrix changed during audit')
    report = {'schema_version': 'recipe-scaling-independent-audit/2', 'status': 'verified' if not errors else 'failed',
              'reviewer': 'Separately assigned AI; independent standard-library byte and record reconciliation, not human review',
              'started_at_utc': started, 'finished_at_utc': datetime.now(timezone.utc).isoformat(),
              'run': str(run), 'plan': record(run / plan_name), 'auditor': record(Path(__file__), ROOT),
              'files_inspected': len(before), 'inventory_sha256': digest(canonical(before)), 'measured_artifacts_unchanged': before == after,
              'originally_pinned_current_source_files_unchanged': source_unchanged,
              'solver_reruns': 0, 'certificate_checker_reruns': 0, 'application_runs': 0,
              'worker_jobs_reconciled': total_jobs, 'recorded_worker_statuses': dict(all_statuses), 'recorded_returncodes': dict(all_codes),
              'recorded_certificate_checks': total_certificates, 'recorded_certificate_rejections': rejected_certificates,
              'nonempty_worker_stderr': worker_stderr, 'profile_count': 66,
              'external_authored_expectations': dict(Counter(p['expected_decision_with_sufficient_budget'] for p in profiles.values())),
              'family_counts': dict(Counter(p['family'] for p in profiles.values())), 'expectation_contradictions': contradictions,
              'legacy_v1_differences': legacy_differences, 'budgets': budgets, 'evidence': artifacts, 'validation_errors': errors,
              'limits': ['Recorded worker and certificate-check results reconciled; no solver or checker was re-executed.',
                         'External authored expectations are development labels, not independent application ground truth.',
                         'The 66 profiles are related parameterized variants, not independent held-out templates.',
                         'Reference and baseline share the legacy oracle; a reference unknown is not a semantic error.',
                         'Equal integer budgets count method-specific operations, not identical primitive work.',
                         'Timings may be contended and one execution per budget proves no speed or reliability advantage.',
                         'No scientific novelty, domain qualification, human acceptance, or project percentage follows.']}
    if errors:
        print(json.dumps({'status': 'failed_prewrite', 'errors': errors[:40], 'error_count': len(errors)}, indent=2))
        return 1
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False); stream.write('\n')
    print(json.dumps({'status': report['status'], 'output': str(output), 'files': len(before), 'jobs': total_jobs,
                      'certificate_checks': total_certificates, 'budgets': {b: v['methods'] for b, v in budgets.items()}}, indent=2))
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(audit(args.run, args.output))
