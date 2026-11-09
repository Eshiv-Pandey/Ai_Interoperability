"""Inert orchestration checks: mocked process launches, cleanup and application I/O."""
from contextlib import ExitStack
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import agentops_bridge_diagnostic_control_v1 as control
import resume_agentops_bridge_diagnostic_v11 as resume


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def clean_group(pgid=43210):
    return {'schema_version': 'agentops-owned-process-group/1', 'pgid': pgid,
            'initially_empty': True, 'final_empty': True, 'forced_cleanup': False,
            'members': [], 'final_members': [], 'snapshots': [], 'signals': [], 'errors': []}


def clean_groups():
    return {key: clean_group(43210 + index) for index, key in enumerate(('controller', 'client', 'service'))}


class ExitedProcess:
    def __init__(self, pid=43210, returncode=0):
        self.pid, self.returncode = pid, returncode
        self.waits = []

    def wait(self, timeout):
        self.waits.append(timeout)
        return self.returncode

    def poll(self):
        return self.returncode


class BridgeSupervisionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='agentops-supervision-fixture-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.replica, self.runtime = self.base / 'replica', self.base / 'runtime'
        self.replica.mkdir()
        self.runtime.mkdir()
        self.output = self.base / 'capture-output'
        self.output.mkdir()
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.stack = stack
        stack.enter_context(patch.object(control, 'ROOT', self.replica))
        stack.enter_context(patch.object(control.evidence, 'WORKSPACE', self.base))
        stack.enter_context(patch.object(resume, 'OUTPUT', self.output))
        # Default guards make every unintended application/process action fail.
        stack.enter_context(patch.object(control.subprocess, 'Popen', side_effect=AssertionError('No real launch permitted')))
        stack.enter_context(patch.object(control.wire, 'exchange', side_effect=AssertionError('No real request permitted')))
        stack.enter_context(patch.object(control, 'finish_owned_group', side_effect=AssertionError('No real group inspection permitted')))
        stack.enter_context(patch.object(resume, 'finish_owned_group', side_effect=AssertionError('No real group inspection permitted')))

    def case(self, case_id):
        folder = self.replica / 'runs/agentops-http-control' / ('bridge-diagnostic-v1-' + case_id)
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def owned_receipts(self, case_id):
        case = self.case(case_id)
        definition = resume.design.CASES[case_id]
        script = 'agentops_native_profile_client_v1.mjs' if definition['kind'] == 'native' else 'agentops_bridge_client_v1.mjs'
        client_argv = ['/usr/bin/node', str(self.replica / 'scripts' / script), '--config', str(case / 'client-config.json')]
        service_argv = [str(self.replica / 'external/runtime-agentops-linux-v7/venv/bin/python'), '-B',
                        str(self.replica / 'scripts/serve_agentops_bridge_diagnostic_v2.py'), '--output', str(case / 'service'),
                        '--port', str(resume.design.PORT)]
        config = resume.design.client_config(definition, case, self.runtime)
        if case_id in ('B6', 'B7'):
            config['bridge']['args'][0] = str(self.replica / 'scripts/agentops_mgcrea_embed_v1.mjs')
        write(case / 'client.started.json', {'pid': 43211, 'argv': client_argv})
        write(case / 'service-process.json', {'pid': 43212, 'argv': service_argv})
        write(case / 'client-config.json', config)
        return case, client_argv, service_argv, config

    def test_exited_client_leader_is_still_inspected_with_exact_bridge_argv(self):
        case, argv, _, config = self.owned_receipts('B7')
        (case / 'client.started.json').unlink()
        process = ExitedProcess()
        with patch.object(control.subprocess, 'Popen', return_value=process) as spawn, \
                patch.object(control, 'finish_owned_group', return_value=clean_group()) as finish:
            result = control.capture_client(argv, case, config)
        finish.assert_called_once_with(process.pid, [argv, [config['bridge']['command'], *config['bridge']['args']]])
        self.assertEqual(process.waits, [220, 10])
        self.assertTrue(result['owned_group']['initially_empty'])
        self.assertFalse(result['forced_kill'])
        self.assertTrue(spawn.call_args.kwargs['start_new_session'])

    def test_native_client_allowed_group_has_only_native_launch(self):
        case, argv, _, config = self.owned_receipts('N11')
        (case / 'client.started.json').unlink()
        with patch.object(control.subprocess, 'Popen', return_value=ExitedProcess()), \
                patch.object(control, 'finish_owned_group', return_value=clean_group()) as finish:
            control.capture_client(argv, case, config)
        self.assertEqual(finish.call_args.args[1], [argv])

    def test_exited_service_is_still_inspected(self):
        case, _, argv, _ = self.owned_receipts('N11')
        service = case / 'service'
        service.mkdir()
        process = ExitedProcess(43212)
        result = {'cleanup_errors': []}
        with patch.object(control, 'finish_owned_group', return_value=clean_group(43212)) as finish:
            control.stop_service(process, argv, service, result)
        finish.assert_called_once_with(process.pid, [argv])
        self.assertEqual(process.waits, [20, 10])
        self.assertEqual(result['service_returncode'], 0)
        self.assertFalse(result['forced_service_stop'])

    def test_exited_controller_still_checks_all_child_receipts(self):
        self.owned_receipts('N11')
        process = ExitedProcess()
        with patch.object(resume.subprocess, 'Popen', return_value=process), \
                patch.object(resume, 'finish_owned_group', side_effect=lambda pgid, allowed: clean_group(pgid)) as finish:
            receipt = resume.capture(self.replica, 'N11', self.runtime, self.replica / 'manifest.json')
        self.assertEqual([call.args[0] for call in finish.call_args_list], [43210, 43211, 43212])
        self.assertTrue(resume.groups_clean(receipt['owned_groups']))
        self.assertEqual(process.waits, [480, 10])

    def test_missing_child_receipt_is_unknown_and_never_authorizes_its_group(self):
        case, _, _, _ = self.owned_receipts('N11')
        (case / 'client.started.json').unlink()
        with patch.object(resume, 'finish_owned_group', side_effect=lambda pgid, allowed: clean_group(pgid)) as finish:
            groups, errors = resume.cleanup_case_groups(self.replica, 'N11', self.runtime, ExitedProcess(), ['controller'])
        self.assertEqual([call.args[0] for call in finish.call_args_list], [43210, 43212])
        self.assertEqual(groups['client']['status'], 'receipt_absent')
        self.assertTrue(errors)
        self.assertFalse(resume.groups_clean(groups))

    def test_changed_child_launch_receipt_is_rejected_before_group_inspection(self):
        case, argv, _, _ = self.owned_receipts('N11')
        write(case / 'client.started.json', {'pid': 99999, 'argv': [*argv, '--changed']})
        with patch.object(resume, 'finish_owned_group', side_effect=lambda pgid, allowed: clean_group(pgid)) as finish:
            groups, errors = resume.cleanup_case_groups(self.replica, 'N11', self.runtime, ExitedProcess(), ['controller'])
        self.assertNotIn(99999, [call.args[0] for call in finish.call_args_list])
        self.assertEqual(groups['client']['status'], 'identity_unconfirmed')
        self.assertTrue(any('frozen design' in error for error in errors))

    def test_embedded_bridge_allowed_argv_comes_from_matching_replica_config(self):
        _, argv, _, config = self.owned_receipts('B6')
        with patch.object(resume, 'finish_owned_group', side_effect=lambda pgid, allowed: clean_group(pgid)) as finish:
            groups, errors = resume.cleanup_case_groups(self.replica, 'B6', self.runtime, ExitedProcess(), ['controller'])
        self.assertEqual(errors, [])
        self.assertTrue(resume.groups_clean(groups))
        self.assertEqual(finish.call_args_list[1].args, (43211, [argv, [config['bridge']['command'], *config['bridge']['args']]]))

    def test_changed_bridge_config_never_authorizes_modified_command(self):
        case, _, _, config = self.owned_receipts('B6')
        config['bridge']['args'].append('--changed')
        write(case / 'client-config.json', config)
        with patch.object(resume, 'finish_owned_group', side_effect=lambda pgid, allowed: clean_group(pgid)) as finish:
            groups, errors = resume.cleanup_case_groups(self.replica, 'B6', self.runtime, ExitedProcess(), ['controller'])
        self.assertEqual([call.args[0] for call in finish.call_args_list], [43210, 43212])
        self.assertEqual(groups['client']['status'], 'identity_unconfirmed')
        self.assertTrue(any('configuration differs' in error for error in errors))

    def test_native_service_path_matches_actual_v7_constant(self):
        self.assertEqual(control.previous.native.RUNTIME.relative_to(control.previous.native.ROOT).as_posix(),
                         'external/runtime-agentops-linux-v7/venv/bin/python')

    def test_cleaned_orphan_is_not_accepted_as_normal_exit(self):
        groups = clean_groups()
        groups['client'].update(initially_empty=False, forced_cleanup=True)
        self.assertFalse(resume.groups_clean(groups))
        self.assertFalse(resume.groups_clean({'controller': clean_group()}))
        groups = clean_groups()
        groups['service']['errors'] = ['identity unknown']
        self.assertFalse(resume.groups_clean(groups))

    def matrix(self, *, strict=False, unclean_at=None, missing_bridge_exit_at=None):
        root = self.base / 'matrix-parent'
        output = root / 'output'
        prior = root / 'prior'
        seal_path = root / 'manifest.json'
        runtime_inputs = root / 'runtime-inputs'
        write(seal_path, {'schema_version': 'agentops-bridge-diagnostic-preparation/1',
                         'cases': list(resume.design.CASES.values()), 'launch_inputs': [],
                         'reuse_inputs': [], 'prerequisites': [], 'runtime_root': str(self.runtime)})
        write(prior / 'result.json', {'status': 'failed',
                                     'export_reference_failures': [], 'linux_workspace': str(self.replica)})
        write(prior / 'export-manifest.json', {'files': []})
        write(prior / 'execution.json', {'inputs': []})
        write(runtime_inputs / 'graph.json', {})
        write(runtime_inputs / 'materialization.json', {})
        calls = []

        def capture(replica, case_id, runtime_root, seal):
            self.assertEqual((replica, runtime_root), (self.replica, self.runtime))
            calls.append(case_id)
            outcome = {'status': 'recorded', 'service_strict_success': True, 'service_returncode': 0,
                       'client_returncode': 0, 'client_timed_out': False, 'client_forced_kill': False,
                       'forced_service_stop': False, 'cleanup_errors': [], 'source_unchanged_after': True,
                       'client_group_cleanup': clean_group(), 'service_group_cleanup': clean_group(),
                       'bridge_clean_exit': True, 'bridge_forced_kill': False}
            if case_id == unclean_at:
                outcome['client_group_cleanup'].update(initially_empty=False, forced_cleanup=True)
            if case_id == missing_bridge_exit_at:
                del outcome['bridge_clean_exit']
            case = self.case(case_id)
            write(case / 'result.json', outcome)
            write(case / 'case-check.json', {'strict_success': strict})
            return {'returncode': 0, 'timed_out': False, 'cleanup_errors': [], 'owned_groups': clean_groups()}

        with ExitStack() as stack:
            for name, value in (('ROOT', root), ('OUTPUT', output), ('PRIOR', prior), ('SEAL', seal_path), ('RUNTIME_INPUTS', runtime_inputs)):
                stack.enter_context(patch.object(resume, name, value))
            stack.enter_context(patch.object(resume.sys, 'platform', 'linux'))
            stack.enter_context(patch.object(resume.previous, 'require_native_filesystem'))
            stack.enter_context(patch.object(resume.previous, 'copy_exact'))
            stack.enter_context(patch.object(resume, 'verify_runtime', return_value={'fixture_verified': True}))
            stack.enter_context(patch.object(resume, 'validate_frozen', return_value=(json.loads(seal_path.read_text()), {})))
            stack.enter_context(patch.object(resume, 'export_evidence', return_value={'files': [], 'reference_failures': []}))
            stack.enter_context(patch.object(resume, 'capture', side_effect=capture))
            stack.enter_context(patch.object(resume, 'capture_sources', return_value={'status': 'captured'}))
            stack.enter_context(patch.object(resume, 'validate_diagnostics', return_value={'valid': True, 'complete': True}))
            stack.enter_context(patch('sys.stdout', new=io.StringIO()))
            resume.main(self.runtime)
        return calls, json.loads((output / 'result.json').read_text()), output

    def test_service_effect_alone_does_not_qualify_any_bridge_and_all_three_are_recorded(self):
        calls, result, output = self.matrix(strict=False)
        self.assertEqual(calls, ['N11'])
        self.assertEqual(len(result['cases']), 3)
        self.assertEqual(result['status'], 'matrix_attempts_recorded')
        for case_id in ('B6', 'B7'):
            self.assertEqual(result['cases'][case_id]['status'], 'skipped')
            self.assertTrue((output / (case_id + '.skipped.json')).is_file())

    def test_unclean_group_stops_before_second_case_and_records_all_remaining(self):
        calls, result, output = self.matrix(strict=True, unclean_at='N11')
        self.assertEqual(calls, ['N11'])
        self.assertEqual(len(result['cases']), 3)
        self.assertIn('Unclean/unknown cleanup', result['error'])
        for case_id in list(resume.design.CASES)[1:]:
            self.assertEqual(result['cases'][case_id]['status'], 'unexecuted')
            self.assertTrue((output / (case_id + '.unexecuted.json')).is_file())

    def test_missing_bridge_child_exit_stops_later_bridge_cases(self):
        calls, result, _ = self.matrix(strict=True, missing_bridge_exit_at='B6')
        self.assertEqual(calls, ['N11'] + ['B6'])
        self.assertEqual(len(result['cases']), 3)
        self.assertIn('Unclean/unknown cleanup', result['error'])
        self.assertEqual(result['cases']['B7']['status'], 'unexecuted')


if __name__ == '__main__':
    unittest.main()
