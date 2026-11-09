"""Restore this task's temporary WSL memory cap only if no one changed it."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
plan = json.loads((root / 'plan.json').read_bytes())
config = Path(plan['config'])
original = (root / 'original.wslconfig').read_bytes()
if hashlib.sha256(original).hexdigest() != plan['original_sha256']:
    raise ValueError('Original configuration capture changed')
current = config.read_bytes()
digest = hashlib.sha256(current).hexdigest()
if digest == plan['temporary_sha256']:
    config.write_bytes(original)
elif digest != plan['original_sha256']:
    raise ValueError('Configuration changed independently; refusing to overwrite it')
restored = config.read_bytes() == original
result = {'status': 'restored' if restored else 'failed',
          'restored_at_utc': datetime.now(timezone.utc).isoformat(),
          'original_bytes_restored': restored, 'config': str(config)}
with (root / 'restoration.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result))
raise SystemExit(0 if restored else 1)
