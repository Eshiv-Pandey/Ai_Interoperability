"""Original ASGI/business capture with separate read-only memory observations.

Memory evidence is best effort: an unsupported schema, live rollback journal,
or recorder I/O failure cannot change the original application's result. The
original v1 transport/business observer retains its existing behavior. These
boundary observations do not prove continuous absence or cross-store atomicity.
"""
from __future__ import annotations

from pathlib import Path

from agentops_asgi_capture_v1 import Capture as BusinessCapture
from agentops_asgi_capture_v1 import evidence
from interoperability.agentops_memory_evidence_v1 import SCHEMA, snapshot_memory


class Capture(BusinessCapture):
    def __init__(self, app, output: Path, *, max_requests=256, max_bytes=32 * 1024 * 1024):
        super().__init__(app, output, max_requests=max_requests, max_bytes=max_bytes)
        self.memory_errors = []

    def snapshot(self, directory, name):
        # Preserve the business snapshot file and original failure behavior.
        super().snapshot(directory, name)
        try:
            value = snapshot_memory(self.output / "state/memory.db", observation_mode="live")
            if (type(value) is not dict or value.get("schema_version") != SCHEMA
                    or value.get("status") not in {"recorded", "absent", "unsupported"}):
                raise ValueError("memory observer returned an unsupported report")
            evidence.write_json(directory / (name + ".memory.snapshot.json"), value)
            if value["status"] == "unsupported":
                self.memory_errors.append({"boundary": name, "exchange": directory.name,
                                           "status": "unsupported"})
        except Exception as error:
            # No caller payload/provider error text enters this summary. Missing
            # evidence stays missing and is never replaced by an empty success.
            self.memory_errors.append({"boundary": name, "exchange": directory.name,
                                       "status": "capture_failed", "error_type": type(error).__name__})
