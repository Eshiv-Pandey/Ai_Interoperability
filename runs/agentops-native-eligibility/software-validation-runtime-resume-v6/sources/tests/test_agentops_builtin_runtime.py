"""Native loader and export regression checks; no AgentOps or Linux execution."""
import importlib.machinery
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from inspect_agentops_runtime_v5 import classify_native_module
from export_agentops_workspace_v6 import export_evidence
from run_agentops_linux_workspace_v5 import record


class BuiltinRuntimeTests(unittest.TestCase):
    def test_real_builtin_without_file_is_accepted(self):
        self.assertFalse(hasattr(sys, "__file__"))
        self.assertEqual(classify_native_module(sys), "builtin")

    def test_real_stdlib_extension_is_accepted(self):
        import _sqlite3
        self.assertEqual(classify_native_module(_sqlite3), "extension")

    def test_python_source_module_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "never a Python shim"):
            classify_native_module(json)

    def test_missing_file_does_not_prove_builtin(self):
        fake = SimpleNamespace(__name__="not_a_builtin", __loader__=importlib.machinery.BuiltinImporter,
            __spec__=importlib.machinery.ModuleSpec("not_a_builtin", importlib.machinery.BuiltinImporter, origin="built-in"))
        with self.assertRaises(ValueError):
            classify_native_module(fake)

    def test_inconsistent_builtin_loader_or_spec_is_rejected(self):
        for loader, spec in ((None, sys.__spec__), (sys.__loader__, None),
                             (sys.__loader__, importlib.machinery.ModuleSpec("wrong", sys.__loader__, origin="built-in"))):
            fake = SimpleNamespace(__name__="sys", __loader__=loader, __spec__=spec)
            with self.subTest(loader=loader, spec=spec), self.assertRaises(ValueError):
                classify_native_module(fake)

    def test_builtin_provider_records_export_from_revalidation_stream(self):
        base = ROOT / "tmp" / ("builtin-export-" + uuid.uuid4().hex)
        source = base / "linux"
        run = source / "runs/agentops-native-eligibility/runtime-revalidation-v5"
        run.mkdir(parents=True)
        binary = source / "external/runtime/python/bin/python3.13"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"authored interpreter")
        library = source / "external/runtime/python/lib/libpython3.13.so"
        library.parent.mkdir(parents=True)
        library.write_bytes(b"authored shared interpreter library")
        providers = [record(binary, source), record(library, source)]
        inventory = {"schema_version": "agentops-installed-runtime-inspection/5", "packages": [],
                     "fcntl_native": {"kind": "builtin", "provider_file": providers[0], "provider_files": providers}}
        stream = run / "runtime-inspection.stdout.bin"
        stream.write_text(json.dumps(inventory), encoding="utf-8")
        (run / "result.json").write_text(json.dumps({"runtime_inventory": record(stream, source)}), encoding="utf-8")
        destination = base / "export"
        result = export_evidence(source, destination, [])
        self.assertEqual(result["reference_failures"], [])
        for item in providers:
            self.assertEqual(record(destination / item["path"], destination), item)


if __name__ == "__main__":
    unittest.main()
