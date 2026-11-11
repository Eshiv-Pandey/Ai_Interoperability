"""Review one retained Workflow V2 allocation; no runtime/provider execution."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUN = 43055395848
HEAD = '04dfdf2a3b1d1c75ad991e610df61815a329669e'
ARCHIVE_SHA = 'f0b5fe3dc6e8b40ae9c3f323fbebf1126f61e8b7d774d5369973a2a26367dad8'
CASES = ('agentops-h09-workflow-select-target', 'agentops-h10-workflow-override-conflict')


def need(condition, message):
    if not condition:
        raise ValueError(message)


def identity(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(262144):
            digest.update(block)
    return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def load(path):
    return json.loads(path.read_bytes())


def rows(path):
    return [json.loads(line) for line in path.read_bytes().splitlines() if line.strip()]


def review(base, output):
    need(not output.exists() and output.is_relative_to(ROOT / 'runs'), 'fresh workspace review output required')
    receipt, run, api = (load(base / name) for name in ('retention.json', 'github-run.json', 'github-artifacts.json'))
    archive = identity(base / 'artifact.zip')
    need(receipt['run_id'] == run['id'] == RUN and receipt['head_sha'] == run['head_sha'] == HEAD
         and run['status'] == 'completed' and run['run_attempt'] == 1, 'retained allocation identity differs')
    need(archive == {'bytes': receipt['archive_bytes'], 'sha256': ARCHIVE_SHA}
         and receipt['api_digest'] == 'sha256:' + ARCHIVE_SHA, 'retained archive identity differs')
    selected = [item for item in api['artifacts'] if item['id'] == receipt['artifact_id']]
    need(len(selected) == 1 and selected[0]['digest'] == receipt['api_digest'], 'API/archive digest differs')
    inventory = load(base / 'extracted-manifest.json')['files']
    indexed = {item['path']: {key: item[key] for key in ('bytes', 'sha256')} for item in inventory}
    need(len(indexed) == len(inventory) == receipt['extracted_files'], 'member inventory differs')
    with zipfile.ZipFile(base / 'artifact.zip') as zipped:
        members = [item for item in zipped.infolist() if not item.is_dir()]
        need(len(members) == len(indexed) and len({item.filename for item in members}) == len(members), 'ZIP membership differs')
        for item in members:
            need(item.filename in indexed, 'unexpected ZIP member')
            digest, count = hashlib.sha256(), 0
            with zipped.open(item) as stream:
                while block := stream.read(262144):
                    count += len(block)
                    digest.update(block)
            need({'bytes': count, 'sha256': digest.hexdigest()} == indexed[item.filename], 'ZIP member bytes differ')
            path = base / 'extracted' / item.filename
            need(not path.is_symlink() and path.resolve().is_relative_to(base / 'extracted'), 'unsafe extracted member')
            need(identity(path) == indexed[item.filename], 'extracted member bytes differ')
    capture = base / 'extracted'
    sdk = load(capture / 'runtime-source/identity.json')
    need(sdk['version'] == '2.10.0' and sdk['all_locked_source_members_matched'] is True, 'SDK source identity differs')
    for item in sdk['source_members']:
        need(identity(capture / 'runtime-source' / item['path']) == {key: item[key] for key in ('bytes', 'sha256')}, 'installed SDK source member differs')
    output.mkdir(parents=True)
    argv = [sys.executable, '-B', str(ROOT / 'scripts/analyze_agentops_workflow_reference_v2.py'),
            '--capture', str(capture), '--output', str(output / 'same-byte-analysis.json')]
    with (output / 'stdout.log').open('xb') as stdout, (output / 'stderr.log').open('xb') as stderr:
        completed = subprocess.run(argv, stdout=stdout, stderr=stderr, timeout=60)
    need(completed.returncode == 0, 'frozen same-byte analyzer failed')
    analysis = load(output / 'same-byte-analysis.json')
    need(analysis == load(capture / 'analysis.json'), 'frozen analysis was not reproduced exactly')
    outcomes = []
    for case_id, report in zip(CASES, analysis['cases']):
        need(case_id == report['case_id'], 'case denominator/order differs')
        case, models = capture / case_id, rows(capture / case_id / 'model-journal.jsonl')
        source = next(part['text'] for row in models if row['stage'] == 'investigate'
                      for part in row['response'].get('content', {}).get('parts', []) if 'text' in part)
        investigation = json.loads(source)
        governed = next(row['observed_input'] for row in models if row['stage'] == 'evidence_review')
        try:
            json.loads(governed)
        except json.JSONDecodeError as error:
            malformed = {'message': error.msg, 'position': error.pos,
                         'context': governed[max(0, error.pos - 15):error.pos + 45]}
        else:
            raise ValueError('expected retained malformed handoff is absent')
        worker = load(case / 'actor-receipt.json')
        need(load(case / 'state-before.json') == load(case / 'state-after.json'), 'business state changed')
        outcomes.append({'case_id': case_id, 'worker_status': worker['status'],
            'fixture_callbacks': report['model_calls'], 'raw_events': report['raw_official_events'],
            'raw_read_tool_terminal_pairs': report['chronological_raw_tool_terminal_pairs'],
            'optional_after_tool_observations': report['observer_after_hook_count'],
            'denied_socket_operations': report['denied_socket_operation_attempts'],
            'final_output': report['reported_final_output'], 'frozen_questions': report['questions'],
            'business_state_unchanged': True, 'official_runner_closed': worker['official_runner_closed'],
            'valid_investigation_target': investigation['target'], 'malformed_governed_review_input': malformed,
            'executing_stage_object_identity': [{'stage': item['stage'], 'type': item['actual_agent_type'],
                'is_exported': item['actual_agent_is_exported_node'], 'is_compiled': item['actual_agent_is_compiled_node']}
                for item in report['actual_original_stage_bindings']],
            'task_success_qualified': False})
    diagnosis_root = ROOT / 'runs/agentops-workflow-reference-development/v1/pinned-sdk-source-diagnosis-v1/source'
    diagnosis_sources = {name: identity(diagnosis_root / name) for name in (
        'google/adk/workflow/_workflow.py', 'google/adk/workflow/_dynamic_node_scheduler.py',
        'google/adk/workflow/utils/_workflow_graph_utils.py')}
    result = {'schema_version': 'agentops-workflow-retained-raw-review/2',
        'reviewed_at_utc': datetime.now(timezone.utc).isoformat(), 'run_id': RUN, 'head_sha': HEAD,
        'archive_identity': archive, 'verified_archive_members': len(indexed),
        'verified_installed_SDK_source_members': len(sdk['source_members']),
        'same_byte_analysis_reproduced': True, 'analysis_identity': identity(output / 'same-byte-analysis.json'),
        'frozen_analysis_status': analysis['status'], 'frozen_analysis_questions': analysis['questions'],
        'case_denominator': 2, 'cases': outcomes, 'source_derived_diagnosis': {
            'handoff': 'Governed review inputs contain illegal JSON backslash escapes before PII redaction markers; preceding investigation outputs are valid JSON with exact source-derived targets.',
            'clone': 'Pinned SDK build_node clones agents; default replay scheduler clones again before NodeRunner. Actual executing agents legitimately differ from exported and compiled objects.',
            'source_members': diagnosis_sources,
            'expanded_actual_instruction_tool_callback_witnesses_retained_by_V2': False,
            'V2_frozen_questions_regraded': False},
        'review_kind': 'AI integration review of retained raw evidence and pinned source; no human semantic grading',
        'original_application_or_SDK_executed': False, 'provider_calls': 0,
        'held_out_qualification': False, 'human_gold': False, 'whole_study_complete': False}
    (output / 'review.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')
    (output / 'reviewer-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'archive_members': len(indexed), 'same_byte_analysis_reproduced': True,
                      'frozen_analysis_questions': analysis['questions'], 'case_denominator': 2, 'provider_calls': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    review(args.base.resolve(), args.output.resolve())
