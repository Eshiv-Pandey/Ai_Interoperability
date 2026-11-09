"""Verify the sealed protocol-v9 preparation without executing AgentOps."""
import argparse
import base64
import csv
import io
import json
import re
from pathlib import Path
from pathlib import PurePosixPath

import agentops_protocol_preparation_v2 as preparation_contract
import check_agentops_socket_resume_v8 as prior
import resume_agentops_protocol_v9 as resume
from check_agentops_linux_workspace_v5 import load, relative_file, require, verify_rows

ROOT = resume.ROOT
MODULE_PREFIX = 'external/runtime-agentops-linux-v7/venv/lib/python3.13/site-packages/'

def verify_software_preparation(root):
    """Accept a successful test run only for the exact current preparation bytes."""
    directory = root / preparation_contract.PREPARATION_RELATIVE
    receipt = load(directory / 'result.json')
    require(receipt.get('schema_version') == 'agentops-protocol-software-preparation/2',
            'Software preparation schema')
    require(type(receipt.get('returncode')) is int and receipt['returncode'] == 0
            and receipt.get('inputs_unchanged') is True
            and receipt.get('application_execution_performed') is False,
            'Successful unchanged offline software preparation')
    argv = receipt.get('argv')
    require(type(argv) is list and len(argv) == 10
            and type(argv[0]) is str and bool(argv[0])
            and argv[1:] == ['-B', '-m', 'unittest', 'discover', '-s', 'tests',
                             '-p', 'test_agentops_protocol*.py', '-v'],
            'Exact protocol test discovery command')
    preparation_contract.verify_records(root, receipt.get('inputs', []),
                                         preparation_contract.SOFTWARE_INPUT_PATHS)
    begin, end = prior.interval(receipt)
    require(begin <= end, 'Software preparation interval')
    stderr = (directory / 'tests.stderr.bin').read_text(encoding='utf-8')
    summary = re.search(r'(?:^|\n)Ran ([1-9][0-9]*) tests? in [0-9.]+s\r?\n\r?\nOK\s*\Z', stderr)
    require(summary is not None, 'Completed passing protocol test summary')
    require((directory / 'tests.stdout.bin').is_file(), 'Preserved protocol test stdout')
    return int(summary.group(1))


def verify_distribution_records(exported, inventory, rows):
    wanted = {MODULE_PREFIX + row['module']: row for row in rows}
    owners = {name: [] for name in wanted}
    for package in inventory['packages']:
        records = [row for row in package['metadata_files'] if PurePosixPath(row['path']).name == 'RECORD']
        for record_row in records:
            entries = list(csv.reader(io.StringIO(
                relative_file(exported, record_row['path']).read_text(encoding='utf-8'))))
            for name, source in wanted.items():
                try:
                    relative = PurePosixPath(name).relative_to(package['location']).as_posix()
                except ValueError:
                    continue
                matches = [entry for entry in entries if entry and entry[0] == relative]
                if not matches:
                    continue
                require(len(matches) == 1 and len(matches[0]) == 3, 'Ambiguous runtime RECORD entry')
                expected_hash = 'sha256=' + base64.urlsafe_b64encode(
                    bytes.fromhex(source['sha256'])).decode().rstrip('=')
                require(matches[0][1:] == [expected_hash, str(source['bytes'])],
                        'Runtime source differs from installed RECORD: ' + name)
                owners[name].append(package['name'])
    require(all(len(value) == 1 for value in owners.values()), 'Runtime source lacks one RECORD owner')


def check():
    prior_result = load(resume.PRIOR / 'result.json')
    seal = load(ROOT / preparation_contract.SEAL_RELATIVE)
    inspection = preparation_contract.validate_seal(ROOT, seal, prior_result)
    require(prior_result['status'] == 'native_and_http_controls_passed'
            and prior_result['export_reference_failures'] == [], 'Passed v8 prerequisite')
    require(prior.check(resume.PRIOR)['status'] == 'artifact_integrity_and_semantics_verified',
            'Read-only v8 prerequisite recheck')
    constructed_tests = verify_software_preparation(ROOT)

    export_manifest = load(resume.PRIOR / 'export-manifest.json')
    expected_runtime = inspection['modules']
    inventory = load(resume.PRIOR / 'workspace' / prior.NATIVE / 'prepared-runtime.stdout.bin')
    verify_distribution_records(resume.PRIOR / 'workspace', inventory, expected_runtime)
    retained = {row['path']: row for row in export_manifest['files']}
    retained_rows = [retained[MODULE_PREFIX + row['module']] for row in expected_runtime
                     if MODULE_PREFIX + row['module'] in retained]
    verify_rows(resume.PRIOR / 'workspace', retained_rows)

    require(seal.get('application_execution_performed') is False
            and seal.get('live_model_calls') == 0
            and seal.get('research_gate_credit_added') == 0, 'Preparation scope')
    require(not resume.OUTPUT.exists(), 'Protocol-v9 attempt already exists')
    return {
        'status': 'preparation_and_prior_integrity_verified',
        'launch_inputs': len(seal['launch_inputs']),
        'prerequisites': len(seal['prerequisites']),
        'runtime_sources': len(seal['runtime_sources']),
        'constructed_tests': constructed_tests,
        'prior_export_files': len(export_manifest['files']),
        'runtime_sources_already_exported': len(retained_rows),
        'v9_attempt_exists': False,
        'application_execution_performed': False,
        'scientific_gate_credit_added': 0,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserve the earlier preparation check')
    report = {'schema_version': 'agentops-protocol-preparation-check/1', 'status': 'failed'}
    try:
        report.update(check())
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['status'] == 'preparation_and_prior_integrity_verified' else 1)
