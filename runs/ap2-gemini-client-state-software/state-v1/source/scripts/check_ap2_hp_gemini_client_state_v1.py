"""Once-only source-copy constructed client-state validation; no SDK import."""
import argparse
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "runs/ap2-gemini-client-state-software/state-v1"
SOURCES = {
    "src/interoperability/ap2_hp_gemini_client_state_v1.py": "058ce68e4d0cf605ee0641c7b6e6dc51163242120e845e1472652f5b2822337e",
    "tests/test_ap2_hp_gemini_client_state_v1.py": "060313ed5138f8f0e8f63380c29003f19341b7319c9cc2c9bee4af21e960d857",
}
DRIVER = "scripts/check_ap2_hp_gemini_client_state_v1.py"
RUN_NAME = "constructed_client_state_checks"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-driver-sha256", required=True)
    args = parser.parse_args(argv)
    if OUTPUT.exists():
        raise ValueError("Consumed client-state allocation cannot be rerun")
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise ValueError("Isolated site-disabled bytecode-disabled interpreter required")
    paths = {name: ROOT / name for name in (*SOURCES, DRIVER)}
    before = {name: path.read_bytes() for name, path in paths.items()}
    expected = {**SOURCES, DRIVER: args.expected_driver_sha256}
    if any(digest(raw) != expected[name] for name, raw in before.items()):
        raise ValueError("Reviewed source/driver bytes differ before allocation")
    tree = ast.parse(before[next(name for name in SOURCES if name.startswith("tests/"))])
    test_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ClientStateChecks")
    names = sorted(node.name for node in test_class.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
    if len(names) != len(set(names)) or len(names) != 19:
        raise ValueError("Exactly nineteen declared tests required")
    OUTPUT.mkdir(parents=True)
    copied = OUTPUT / "source"
    for name, raw in before.items():
        target = copied / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    plan = {"schema_version": "ap2-hp-client-state-software/1", "source_hashes": expected,
            "tests_declared": names, "isolated_python": True, "site_disabled": True,
            "bytecode_disabled": True, "synthetic_classes_only": True,
            "sdk_imports": 0, "provider_requests": 0, "original_application_imports": 0,
            "actual_quota_reserved": False, "native_guard_installed": False}
    (OUTPUT / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    def deny(event, arguments):
        if event.startswith("socket.") or event in {"subprocess.Popen", "os.system", "os.spawn", "os.posix_spawn", "os.exec"}:
            raise RuntimeError("Client-state capture denies network/process launch")
        if event == "import" and str(arguments[0]).split(".")[0] in {"google", "httpx", "httpcore", "ap2", "a2a", "uvicorn", "roles", "common"}:
            raise RuntimeError("Original/SDK imports are outside this capture")
    sys.addaudithook(deny)
    sys.path.insert(0, str(copied / "src"))
    test_path = copied / "tests/test_ap2_hp_gemini_client_state_v1.py"
    spec = importlib.util.spec_from_file_location(RUN_NAME, test_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[RUN_NAME] = module
    spec.loader.exec_module(module)
    records = []
    class Outcomes(unittest.TextTestResult):
        def addSuccess(self, test):
            records.append({"id": test.id(), "status": "passed"})
            super().addSuccess(test)
        def addError(self, test, error):
            records.append({"id": test.id(), "status": "error"})
            super().addError(test, error)
        def addFailure(self, test, error):
            records.append({"id": test.id(), "status": "failed"})
            super().addFailure(test, error)
        def addSkip(self, test, reason):
            records.append({"id": test.id(), "status": "skipped"})
            super().addSkip(test, reason)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Outcomes).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(module.ClientStateChecks))
    (OUTPUT / "stdout.txt").write_text(stream.getvalue(), encoding="utf-8")
    ids = [RUN_NAME + ".ClientStateChecks." + name for name in names]
    membership = sorted(row["id"] for row in records) == ids and all(row["status"] == "passed" for row in records)
    unchanged = all(path.read_bytes() == before[name] and (copied / name).read_bytes() == before[name]
                    for name, path in paths.items())
    receipt = {**plan, "status": "passed_constructed_software_tests_only" if result.wasSuccessful() and membership and unchanged else "failed",
               "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
               "skips": len(result.skipped), "declared_test_membership_verified": membership,
               "source_and_driver_inputs_unchanged": unchanged, "source_copies": len(paths),
               "transitive_sdk_fidelity_verified": False, "native_qualification_established": False}
    (OUTPUT / "test-outcomes.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "result.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["status"] == "passed_constructed_software_tests_only" else 1


if __name__ == "__main__":
    raise SystemExit(main())
