"""Describe retained cost phases; execute no admission solver or checker."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'runs/common-cost-development/v1/read-audit-42927208534-3/result.json'
CELLS = AUDIT.with_name('cells.jsonl')
PHASES = ('profile_source_load_and_guard', 'solver_import_and_evaluate',
          'solver_result_serialization', 'independent_checker_import_and_check', 'solver_result_output')


def record(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def analyze():
    audit = json.loads(AUDIT.read_bytes())
    if audit['status'] != 'passed_read_only_archive_receipt_and_physical_cost_audit':
        raise ValueError('Completed independent cost audit required')
    exports = {row['path']: row for row in audit['exports']}
    actual = record(CELLS)
    if {k: actual[k] for k in ('bytes', 'sha256')} != {k: exports['cells.jsonl'][k] for k in ('bytes', 'sha256')}:
        raise ValueError('Audited cell export changed')
    with CELLS.open(encoding='utf-8') as stream:
        rows = [json.loads(line) for line in stream]
    if len(rows) != 1650:
        raise ValueError('All 1650 allocations must remain present')
    indexed = {(row['cell']['profile_id'], row['cell']['repeat'], row['cell']['method_id']): row for row in rows}
    if len(indexed) != 1650:
        raise ValueError('Duplicate profile/repeat/method cell')
    pair = audit['paired_profile_costs']['goal_pruned_direct__original_refinement']
    profiles = [row['profile_id'] for row in pair['per_profile']]
    if len(profiles) != 54:
        raise ValueError('Expected preserved 54-profile certified cohort')
    physical = {}
    for field in ('cpu_total_ns', 'outer_wall_ns', 'peak_rss_bytes'):
        ratios = [row[field]['right_median'] / row[field]['left_median'] for row in pair['per_profile']]
        physical[field] = {'median_original_over_goal_pruned_direct': statistics.median(ratios),
            'observed_profile_ratio_min': min(ratios), 'observed_profile_ratio_max': max(ratios),
            'original_lower_equal_higher': [sum(r < 1 for r in ratios), sum(r == 1 for r in ratios), sum(r > 1 for r in ratios)]}
    methods = {}
    for method in ('goal_pruned_direct', 'original_refinement', 'shared_lift'):
        records = []
        for profile in profiles:
            cells = [indexed[(profile, repeat, method)] for repeat in range(5)]
            if any(row['status'] != 'certified' or row['certificate_valid'] is not True for row in cells):
                raise ValueError('Uncertified row in preserved cost cohort')
            item = {'profile_id': profile}
            for phase in PHASES:
                observations = [row['phase_resources'][phase] for row in cells]
                if any(type(o[key]) is not int or o[key] < 0 for o in observations for key in ('cpu_ns', 'wall_ns')):
                    raise ValueError('Malformed phase measurement')
                item[phase] = {key: statistics.median(o[key] for o in observations) for key in ('cpu_ns', 'wall_ns')}
            item['full_child_cpu_ns'] = statistics.median(row['resources']['cpu_total_ns'] for row in cells)
            # Different clocks and their quantization are preserved, not silently clamped.
            item['full_minus_recorded_phase_cpu_ns'] = statistics.median(
                row['resources']['cpu_total_ns'] - sum(row['phase_resources'][p]['cpu_ns'] for p in PHASES) for row in cells)
            records.append(item)
        methods[method] = {'profile_count': 54,
            'descriptive_median_across_profile_phase_medians': {
                phase: {key: statistics.median(item[phase][key] for item in records) for key in ('cpu_ns', 'wall_ns')}
                for phase in PHASES},
            'median_full_child_cpu_ns': statistics.median(item['full_child_cpu_ns'] for item in records),
            'median_full_minus_recorded_phase_cpu_ns': statistics.median(item['full_minus_recorded_phase_cpu_ns'] for item in records),
            'per_profile': records}
    return {'schema_version': 'retained-common-cost-phase-description/1',
        'inputs': [record(AUDIT), record(CELLS), record(Path(__file__))],
        'allocated_cells_retained': 1650, 'comparison_profiles': 54, 'paired_repeats': 5,
        'physical_original_vs_goal_pruned_direct': physical, 'phase_description': methods,
        'comparison_unit': 'related authored profile; five dependent timing repeats',
        'limits': ['Solver phase combines import and evaluation; checker phase combines import and checking.',
                   'Full-minus-phase CPU also includes startup, worker imports, unmetered glue, closing output and clock differences.',
                   'Phase CPU can be zero because of measurement resolution; it is not a proof of zero computation.',
                   'Subtracting these phases cannot establish a warmed long-lived-process result.',
                   'Observed profile ranges are descriptive, not confidence intervals.',
                   'No novelty, held-out advantage or full-study completion inferred.'],
        'new_solver_checker_application_or_provider_calls': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'runs/common-cost-development/v1'):
        raise ValueError('Fresh analysis output under the preserved cost run required')
    result = analyze()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'output': output.relative_to(ROOT).as_posix(),
        'physical': result['physical_original_vs_goal_pruned_direct'],
        'phase_medians': {m: {k: v for k, v in data.items() if k != 'per_profile'} for m, data in result['phase_description'].items()}}))
