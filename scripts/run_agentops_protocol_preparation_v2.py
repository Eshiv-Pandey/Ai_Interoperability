"""Record current protocol software tests and their exact input hashes."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

import agentops_protocol_preparation_v2 as preparation

ROOT = Path(__file__).resolve().parents[1]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserve the earlier software preparation')
    args.output.mkdir(parents=True, exist_ok=False)
    inputs = [preparation.file_record(ROOT, name) for name in preparation.SOFTWARE_INPUT_PATHS]
    command = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests',
               '-p', 'test_agentops_protocol*.py', '-v']
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(command, cwd=ROOT, capture_output=True)
    (args.output / 'tests.stdout.bin').write_bytes(result.stdout)
    (args.output / 'tests.stderr.bin').write_bytes(result.stderr)
    after = [preparation.file_record(ROOT, name) for name in preparation.SOFTWARE_INPUT_PATHS]
    receipt = {
        'schema_version': 'agentops-protocol-software-preparation/2',
        'argv': command,
        'started_at_utc': started,
        'finished_at_utc': datetime.now(timezone.utc).isoformat(),
        'returncode': result.returncode,
        'inputs': inputs,
        'inputs_unchanged': inputs == after,
        'application_execution_performed': False,
        'scope': 'Constructed checker/coordinator tests; no WSL or AgentOps request',
    }
    with (args.output / 'result.json').open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(result.stderr.decode(errors='replace'))
    raise SystemExit(0 if result.returncode == 0 and receipt['inputs_unchanged'] else 1)
