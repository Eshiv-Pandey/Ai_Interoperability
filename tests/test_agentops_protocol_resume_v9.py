"""Offline coordinator safety checks; no WSL or AgentOps execution."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import resume_agentops_protocol_v9 as resume


class FakeProcess:
    def __init__(self, *, wait_error=None, pid=4321):
        self.pid = pid
        self.returncode = None
        self.wait_error = wait_error

    def poll(self):
        return self.returncode

    def wait(self, timeout):
        if timeout == 600 and self.wait_error is not None:
            error, self.wait_error = self.wait_error, None
            raise error
        self.returncode = 0 if timeout == 600 else -9
        return self.returncode


class ResumeSafetyTests(unittest.TestCase):
    def setUp(self):
        (ROOT / 'tmp').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'tmp')
        self.base = Path(self.temp.name)
        self.output = self.base / 'output'
        self.output.mkdir()
        self.replica = self.base / 'agentops-research-v7-constructed'
        self.replica.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_started_receipt_failure_still_kills_controller_and_writes_terminal_receipt(self):
        process = FakeProcess()
        real_write = resume.evidence.write_json

        def write(path, value):
            if path.name == 'sync.started.json':
                raise OSError('constructed receipt failure')
            return real_write(path, value)

        with patch.object(resume, 'OUTPUT', self.output), \
                patch.object(resume.evidence, 'clean_environment', return_value={}), \
                patch.object(resume.subprocess, 'Popen', return_value=process), \
                patch.object(resume.evidence, 'write_json', side_effect=write), \
                patch.object(resume.signal, 'SIGKILL', 9, create=True), \
                patch.object(resume.os, 'killpg', create=True) as kill:
            receipt = resume.capture(self.replica, 'sync')
        kill.assert_called_once_with(process.pid, 9)
        self.assertIn('OSError: constructed receipt failure', receipt['capture_error'])
        self.assertEqual(receipt['returncode'], -9)
        self.assertTrue((self.output / 'sync.json').is_file())

    def test_cleanup_identity_mismatch_is_retained_and_controller_is_still_killed(self):
        process = FakeProcess(wait_error=subprocess.TimeoutExpired(['constructed'], 600))
        with patch.object(resume, 'OUTPUT', self.output), \
                patch.object(resume.evidence, 'clean_environment', return_value={}), \
                patch.object(resume.subprocess, 'Popen', return_value=process), \
                patch.object(resume, 'cleanup_owned_service', side_effect=ValueError('constructed mismatch')), \
                patch.object(resume.signal, 'SIGKILL', 9, create=True), \
                patch.object(resume.os, 'killpg', create=True) as kill:
            receipt = resume.capture(self.replica, 'sync')
        kill.assert_called_once_with(process.pid, 9)
        self.assertTrue(receipt['timed_out'])
        self.assertEqual(receipt['returncode'], -9)
        self.assertIn('service: ValueError: constructed mismatch', receipt['cleanup_errors'])

    def test_existing_output_is_refused_before_prerequisite_reads(self):
        with patch.object(resume, 'OUTPUT', self.output), \
                patch.object(resume.sys, 'platform', 'linux'), \
                patch.object(resume.evidence, 'load_json') as load:
            with self.assertRaisesRegex(FileExistsError, 'Preserve'):
                resume.main()
        load.assert_not_called()

    def test_changed_parent_row_is_rejected(self):
        path = self.base / 'input.txt'
        path.write_text('original', encoding='utf-8')
        row = resume.previous.record(path, self.base)
        changed = copy.deepcopy(row)
        changed['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Changed file: input.txt'):
            resume.verify_unchanged([changed], self.base)

    def test_cases_are_ordered_and_unclean_sync_blocks_stream(self):
        calls = []
        for case in ('sync', 'stream'):
            folder = self.replica / f'runs/agentops-http-control/protocol-v1-{case}'
            folder.mkdir(parents=True)
            (folder / 'result.json').write_text(json.dumps({
                'status': 'protocol_and_effect_checks_passed',
                'forced_service_stop': False,
                'cleanup_errors': [],
                'service_returncode': 0,
            }), encoding='utf-8')
            (folder / 'service-process.json').write_text('{}', encoding='utf-8')

        def clean_capture(replica, case):
            calls.append(case)
            return {'returncode': 0, 'timed_out': False}

        result = {'cases': {}}
        with patch.object(resume, 'capture', side_effect=clean_capture):
            resume.run_cases(self.replica, result)
        self.assertEqual(calls, ['sync', 'stream'])
        self.assertEqual(set(result['cases']), {'sync', 'stream'})

        calls.clear()

        def unclean_capture(replica, case):
            calls.append(case)
            return {'returncode': -9, 'timed_out': True, 'cleanup_errors': ['constructed']}

        with patch.object(resume, 'capture', side_effect=unclean_capture):
            with self.assertRaisesRegex(ValueError, 'second launch not permitted'):
                resume.run_cases(self.replica, {'cases': {}})
        self.assertEqual(calls, ['sync'])


if __name__ == '__main__':
    unittest.main()
