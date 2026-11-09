"""Mocked handle authority and Job accounting; never create native processes."""
from contextlib import ExitStack
import ctypes
from ctypes import wintypes as w
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability import windows_owned_job_v1 as owned


class Kernel:
    def __init__(self):
        self.calls = []
        self.error = 5
        self.running = True
        self.active = 0
        self.pids = []
        self.assigned = False
        self.assign_ok = True
        self.create_ok = True
        self.resume_result = 1
        self.terminate_ok = True
        self.terminate_effect = True
        self.close_fail = set()
        self.query_fail = set()
        self.set_limits_ok = True
        self.wait_override = None
        self.exit_code = 0
        for name in ("CreateJobObjectW", "SetInformationJobObject", "QueryInformationJobObject", "CreateProcessW",
                     "AssignProcessToJobObject", "ResumeThread", "TerminateProcess", "TerminateJobObject",
                     "WaitForSingleObject", "GetExitCodeProcess", "CloseHandle"):
            setattr(self, name, Mock(side_effect=getattr(self, "_" + name)))

    def _CreateJobObjectW(self, *args):
        self.calls.append(("create_job", 201))
        return 201

    def _SetInformationJobObject(self, handle, kind, value, size):
        self.calls.append(("limits", handle))
        self.limit_flags = ctypes.cast(value, ctypes.POINTER(owned._ExtendedLimits)).contents.BasicLimitInformation.LimitFlags
        return self.set_limits_ok

    def _CreateProcessW(self, executable, command, *args):
        self.calls.append(("create_process", executable))
        self.flags = args[3]
        if self.create_ok:
            info = ctypes.cast(args[-1], ctypes.POINTER(owned._ProcessInfo)).contents
            info.hProcess, info.hThread, info.dwProcessId, info.dwThreadId = 101, 102, 501, 502
        return self.create_ok

    def _AssignProcessToJobObject(self, job, process):
        self.calls.append(("assign", job, process))
        if self.assign_ok:
            self.assigned, self.active, self.pids = True, 1, [501]
        return self.assign_ok

    def _ResumeThread(self, thread):
        self.calls.append(("resume", thread))
        return self.resume_result

    def _TerminateProcess(self, process, code):
        self.calls.append(("terminate_process", process))
        if self.terminate_ok and self.terminate_effect:
            self.running, self.exit_code = False, code
            self.pids = [pid for pid in self.pids if pid != 501]
            self.active = len(self.pids)
        return self.terminate_ok

    def _TerminateJobObject(self, job, code):
        self.calls.append(("terminate_job", job))
        if self.terminate_ok and self.terminate_effect:
            self.running, self.exit_code, self.active, self.pids = False, code, 0, []
        return self.terminate_ok

    def _WaitForSingleObject(self, process, wait):
        self.calls.append(("wait", process))
        return self.wait_override if self.wait_override is not None else (258 if self.running else 0)

    def _GetExitCodeProcess(self, process, output):
        self.calls.append(("exit_code", process))
        ctypes.cast(output, ctypes.POINTER(w.DWORD)).contents.value = self.exit_code
        return True

    def _QueryInformationJobObject(self, job, kind, output, size, returned):
        self.calls.append(("query", job, kind))
        if kind in self.query_fail:
            self.error = 5
            return False
        if kind == 1:
            ctypes.cast(output, ctypes.POINTER(owned._Accounting)).contents.ActiveProcesses = self.active
            return True
        if kind != 3:
            raise AssertionError("unexpected Job query class")
        capacity = (size - 8) // ctypes.sizeof(ctypes.c_size_t)
        selected = self.pids[:capacity]
        payload = struct.pack("<II", len(self.pids), len(selected)) + b"".join(
            pid.to_bytes(ctypes.sizeof(ctypes.c_size_t), "little") for pid in selected)
        ctypes.memmove(output, payload, len(payload))
        self.error = 234 if len(selected) != len(self.pids) else 0
        return len(selected) == len(self.pids)

    def _CloseHandle(self, handle):
        self.calls.append(("close", handle))
        return handle not in self.close_fail


class OwnedJobTests(unittest.TestCase):
    def setUp(self):
        self.kernel = Kernel()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(owned.sys, "platform", "win32"))
        self.stack.enter_context(patch.object(owned.ctypes, "WinDLL", return_value=self.kernel, create=True))
        self.stack.enter_context(patch.object(owned.ctypes, "get_last_error", side_effect=lambda: self.kernel.error, create=True))
        self.stack.enter_context(patch.dict(sys.modules, {"msvcrt": SimpleNamespace(get_osfhandle=lambda fd: fd + 10)}))
        self.null = MagicMock()
        self.null.__enter__.return_value = self.null
        self.null.fileno.return_value = 2
        self.stack.enter_context(patch.object(owned, "open", return_value=self.null, create=True))
        self.inherited = {12: False, 13: False, 14: False}
        self.restoration_failure = None

        def set_inheritable(handle, value):
            if handle == self.restoration_failure and value is False:
                raise OSError("synthetic restoration failure")
            self.inherited[handle] = value

        self.stack.enter_context(patch.object(owned.os, "get_handle_inheritable", side_effect=self.inherited.__getitem__, create=True))
        self.stack.enter_context(patch.object(owned.os, "set_handle_inheritable", side_effect=set_inheritable, create=True))
        self.job = owned.WindowsJob()
        self.argv = [str(Path(sys.executable).resolve()), "-I", "-S", "-B", "synthetic.py"]
        self.cwd = str(ROOT.resolve())
        self.stdout = SimpleNamespace(fileno=lambda: 3)
        self.stderr = SimpleNamespace(fileno=lambda: 4)

    def launch(self):
        return self.job.launch(self.argv, self.cwd, self.stdout, self.stderr)

    def ready_process(self):
        self.launch()
        self.kernel.calls.clear()

    def observed_empty(self):
        self.kernel.running, self.kernel.active, self.kernel.pids = False, 0, []

    def test_suspended_creation_assignment_then_resume_and_stdio_restoration(self):
        self.assertEqual(self.launch(), 501)
        names = [call[0] for call in self.kernel.calls]
        self.assertLess(names.index("create_process"), names.index("assign"))
        self.assertLess(names.index("assign"), names.index("resume"))
        self.assertTrue(self.kernel.flags & 0x4)
        self.assertTrue(self.kernel.flags & 0x08000000)
        self.assertEqual(self.kernel.limit_flags, 0x2000)
        self.assertEqual(self.inherited, {12: False, 13: False, 14: False})
        self.assertEqual((self.job.job, self.job.process, self.job.thread), (201, 101, None))

    def test_assign_failure_retains_created_process_and_thread_when_exact_termination_fails(self):
        self.kernel.assign_ok, self.kernel.terminate_ok = False, False
        with self.assertRaises(OSError) as caught:
            self.launch()
        self.kernel.ResumeThread.assert_not_called()
        self.kernel.TerminateProcess.assert_called_once_with(101, 1)
        self.kernel.TerminateJobObject.assert_not_called()
        self.assertEqual((self.job.job, self.job.process, self.job.thread), (201, 101, 102))
        self.assertFalse(self.job.closed)
        self.assertIs(caught.exception.owned_job, self.job)
        self.assertTrue(caught.exception.owned_cleanup["authority_retained"])
        self.assertFalse(any(call[0] == "close" for call in self.kernel.calls))

    def test_post_create_metadata_failure_cannot_reclassify_created_child_as_unlaunched(self):
        class FragileArgv(list):
            iterations = 0

            def __iter__(self):
                self.iterations += 1
                if self.iterations == 3:
                    raise RuntimeError("synthetic metadata copy failure")
                return super().__iter__()

        self.argv = FragileArgv(self.argv)
        self.kernel.terminate_ok = False
        with self.assertRaises(RuntimeError):
            self.launch()
        self.assertTrue(self.job.created)
        self.assertEqual((self.job.job, self.job.process, self.job.thread), (201, 101, 102))
        self.kernel.TerminateProcess.assert_called_once_with(101, 1)
        self.assertFalse(self.job.closed)

    def test_cleanup_base_exception_after_creation_carries_exact_live_owner(self):
        class CleanupAbort(BaseException):
            pass

        self.kernel.assign_ok = False
        abort = CleanupAbort("synthetic cleanup interruption")
        with patch.object(self.job, "finish", side_effect=abort):
            with self.assertRaises(CleanupAbort) as caught:
                self.launch()
        self.assertIs(caught.exception, abort)
        self.assertIs(caught.exception.owned_job, self.job)
        self.assertEqual(caught.exception.owned_primary_error_type, "OSError")
        self.assertEqual(caught.exception.owned_cleanup["owned_handles"], {"job": 201, "process": 101, "thread": 102})
        self.assertTrue(caught.exception.owned_cleanup["authority_retained"])
        self.assertEqual(self.job.launch_failure["cleanup"]["status"], "cleanup_exception")
        self.assertFalse(self.job.closed)
        self.assertFalse(any(call[0] == "close" for call in self.kernel.calls))

    def test_resume_failure_terminates_only_owned_job_and_retains_all_authority_on_failure(self):
        self.kernel.resume_result, self.kernel.terminate_ok = 0xFFFFFFFF, False
        with self.assertRaises(OSError):
            self.launch()
        self.kernel.TerminateJobObject.assert_called_once_with(201, 1)
        self.kernel.TerminateProcess.assert_not_called()
        self.assertEqual((self.job.job, self.job.process, self.job.thread), (201, 101, 102))

    def test_stdio_restoration_failure_after_resume_still_retains_created_authority(self):
        self.restoration_failure, self.kernel.terminate_ok = 13, False
        with self.assertRaises(OSError):
            self.launch()
        self.assertTrue(self.job.resumed)
        self.assertFalse(self.inherited[12])
        self.assertFalse(self.inherited[14])
        self.assertEqual(self.job.launch_failure["stage"], "restore_stdio")
        self.assertEqual((self.job.job, self.job.process, self.job.thread), (201, 101, 102))

    def test_failed_thread_handle_close_after_resume_does_not_discard_process_authority(self):
        self.kernel.close_fail.add(102)
        self.kernel.terminate_ok = False
        with self.assertRaises(OSError):
            self.launch()
        self.assertEqual(self.job.launch_failure["stage"], "close_thread")
        self.assertEqual((self.job.job, self.job.process, self.job.thread), (201, 101, 102))
        self.assertFalse(self.job.closed)

    def test_nonstandard_resume_counts_are_failed_owned_launches(self):
        for result in (0, 2, True):
            with self.subTest(result=result):
                kernel = Kernel()
                kernel.resume_result, kernel.terminate_ok = result, False
                with patch.object(owned.ctypes, "WinDLL", return_value=kernel):
                    self.job = owned.WindowsJob()
                self.kernel = kernel
                with self.assertRaises(OSError):
                    self.launch()
                self.assertTrue(self.job.assigned)
                self.assertFalse(self.job.resumed)
                self.assertIsNotNone(self.job.process)

    def test_created_handle_survives_until_assignment_failure_cleanup_is_observed(self):
        self.kernel.assign_ok = False
        with self.assertRaises(OSError) as caught:
            self.launch()
        self.assertTrue(caught.exception.owned_cleanup["job_empty_observed"])
        self.assertTrue(caught.exception.owned_cleanup["main_handle_signaled"])
        self.assertEqual(caught.exception.owned_cleanup["active_processes"], 0)
        self.assertTrue(self.job.closed)

    def test_empty_qualification_queries_independent_accounting_pid_list_and_main_handle(self):
        self.ready_process()
        self.observed_empty()
        report = self.job.finish(0, 0)
        self.assertEqual(report["active_processes"], 0)
        self.assertIs(type(report["active_processes"]), int)
        self.assertEqual(report["members"], [])
        self.assertTrue(report["main_handle_signaled"])
        self.assertTrue(report["job_empty_observed"])
        self.assertTrue(report["handles_closed"])
        self.assertFalse(report["authority_retained"])
        self.assertIn(("query", 201, 1), self.kernel.calls)
        self.assertIn(("query", 201, 3), self.kernel.calls)
        self.assertIn(("wait", 101), self.kernel.calls)

    def test_each_disagreement_preserves_authority_and_cannot_qualify_empty(self):
        for running, active, pids in ((True, 0, []), (False, 1, []), (False, 0, [501])):
            with self.subTest(running=running, active=active, pids=pids):
                self.kernel = Kernel()
                with patch.object(owned.ctypes, "WinDLL", return_value=self.kernel):
                    self.job = owned.WindowsJob()
                self.launch()
                self.kernel.running, self.kernel.active, self.kernel.pids = running, active, pids
                self.kernel.terminate_ok = False
                self.kernel.calls.clear()
                report = self.job.finish(0, 0)
                self.assertFalse(report["job_empty_observed"])
                self.assertTrue(report["authority_retained"])
                self.assertFalse(any(call[0] == "close" for call in self.kernel.calls))

    def test_failed_job_termination_retains_handles_and_forced_is_sticky_after_retry(self):
        self.ready_process()
        self.kernel.terminate_ok = False
        first = self.job.finish(0, 0)
        self.assertTrue(first["forced"])
        self.assertTrue(first["authority_retained"])
        self.assertEqual((self.job.job, self.job.process), (201, 101))
        self.observed_empty()
        second = self.job.finish(0, 0)
        self.assertTrue(second["forced"])
        self.assertTrue(second["handles_closed"])
        self.assertTrue(self.job.finish(0, 0)["forced"])

    def test_successful_termination_without_observed_exit_preserves_authority(self):
        self.ready_process()
        self.kernel.terminate_effect = False
        report = self.job.finish(0, 0)
        self.assertTrue(report["forced"])
        self.assertFalse(report["job_empty_observed"])
        self.assertFalse(report["handles_closed"])
        self.assertTrue(report["authority_retained"])
        self.assertEqual(self.job.process, 101)

    def test_forced_termination_is_observed_even_when_wait_budget_is_zero(self):
        self.ready_process()
        report = self.job.finish(0, 0)
        self.assertTrue(report["forced"])
        self.assertTrue(report["job_empty_observed"])
        self.assertTrue(report["handles_closed"])
        self.assertEqual(report["returncode"], 1)

    def test_close_does_not_implicitly_kill_or_discard_unqualified_authority(self):
        self.ready_process()
        report = self.job.close()
        self.assertFalse(report["handles_closed"])
        self.assertTrue(report["authority_retained"])
        self.assertEqual((self.job.job, self.job.process), (201, 101))
        self.assertEqual(self.kernel.calls, [])

    def test_close_failure_preserves_failed_handle_and_remaining_authority(self):
        self.ready_process()
        self.observed_empty()
        self.kernel.close_fail.add(101)
        first = self.job.finish(0, 0)
        self.assertTrue(first["job_empty_observed"])
        self.assertFalse(first["handles_closed"])
        self.assertEqual((self.job.job, self.job.process), (201, 101))
        self.kernel.close_fail.clear()
        second = self.job.finish(0, 0)
        self.assertTrue(second["handles_closed"])
        self.assertTrue(second["observation_reused"])

    def test_accounting_or_pid_query_failure_never_becomes_empty(self):
        for kind in (1, 3):
            with self.subTest(query=kind):
                self.kernel = Kernel()
                with patch.object(owned.ctypes, "WinDLL", return_value=self.kernel):
                    self.job = owned.WindowsJob()
                self.launch()
                self.kernel.query_fail.add(kind)
                self.kernel.terminate_ok = False
                report = self.job.finish(0, 0)
                self.assertFalse(report["job_empty_observed"])
                self.assertTrue(report["authority_retained"])

    def test_pid_list_is_bounded_and_duplicate_pid_evidence_is_rejected(self):
        self.kernel.pids = list(range(1000, 1100))
        self.assertEqual(self.job.members(), self.kernel.pids)
        self.kernel.pids = [501, 501]
        with self.assertRaises(ValueError):
            self.job.members()
        self.kernel.pids = list(range(1, 5000))
        with self.assertRaises(ValueError):
            self.job.members()

    def test_wait_failure_or_boolean_result_cannot_claim_signaled_main(self):
        self.ready_process()
        for result in (0xFFFFFFFF, False):
            with self.subTest(result=result):
                self.kernel.wait_override, self.kernel.terminate_ok = result, False
                report = self.job.finish(0, 0)
                self.assertFalse(report["main_handle_signaled"])
                self.assertFalse(report["job_empty_observed"])
                self.assertTrue(report["authority_retained"])

    def test_cleanup_never_terminates_a_member_by_pid(self):
        self.ready_process()
        self.kernel.active, self.kernel.pids = 2, [501, 987654]
        self.job.finish(0, 0)
        self.kernel.TerminateJobObject.assert_called_once_with(201, 1)
        self.kernel.TerminateProcess.assert_not_called()
        self.assertFalse(any(987654 in call[1:] for call in self.kernel.calls if call[0] != "query"))

    def test_constructor_limit_failure_keeps_failed_close_authority_on_exception(self):
        kernel = Kernel()
        kernel.set_limits_ok = False
        kernel.close_fail.add(201)
        with patch.object(owned.ctypes, "WinDLL", return_value=kernel):
            with self.assertRaises(OSError) as caught:
                owned.WindowsJob()
        owner = caught.exception.owned_job
        self.assertFalse(owner.closed)
        self.assertEqual(owner.job, 201)
        kernel.close_fail.clear()
        self.assertTrue(owner.close()["handles_closed"])

    def test_constructor_cleanup_base_exception_preserves_unreturned_job_owner(self):
        class CleanupAbort(BaseException):
            pass

        kernel = Kernel()
        kernel.set_limits_ok = False
        abort = CleanupAbort("synthetic constructor cleanup interruption")
        kernel.CloseHandle.side_effect = abort
        with patch.object(owned.ctypes, "WinDLL", return_value=kernel):
            with self.assertRaises(CleanupAbort) as caught:
                owned.WindowsJob()
        self.assertIs(caught.exception, abort)
        owner = caught.exception.owned_job
        self.assertEqual((owner.job, owner.process, owner.thread), (201, None, None))
        self.assertFalse(owner.closed)
        self.assertTrue(caught.exception.owned_cleanup["authority_retained"])
        self.assertEqual(caught.exception.owned_primary_error_type, "OSError")
        kernel.CloseHandle.side_effect = kernel._CloseHandle
        self.assertTrue(owner.close()["handles_closed"])

    def test_cleanup_waits_reject_bool_nonfinite_and_negative_values(self):
        for value in (True, -1, float("nan"), float("inf"), "1"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.job.finish(value, 0)


if __name__ == "__main__":
    unittest.main()
