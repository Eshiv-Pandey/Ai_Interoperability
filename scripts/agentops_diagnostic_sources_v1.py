"""Copy source bytes named by recorded shutdown frames, after capture only.

This inspects current files; it does not attest which module bytes were loaded
before or during execution. It imports no captured source and sends no signal.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import stat

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_INPUT_BYTES = 8 * 1024 * 1024
TRACE_FRAME = re.compile(r'^\s*File "(.*)", line [0-9]+ in .*$')


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(path, workspace, raw):
    return {'path': path.relative_to(workspace).as_posix(), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def capture_sources(case_dir: Path, workspace: Path):
    """Return/write an exclusive post-capture receipt with explicit closure gaps.

    Caller must already have established service termination. This helper does
    not infer process state from files. Copies live below diagnostic-sources.
    """
    workspace = Path(workspace).resolve(strict=True)
    case_dir = Path(case_dir).resolve(strict=True)
    if not workspace.is_dir() or not case_dir.is_dir() or not case_dir.is_relative_to(workspace):
        raise ValueError('Require an existing case directory inside the workspace')
    output = case_dir / 'diagnostic-sources'
    output.mkdir(exist_ok=False)
    report = {'schema_version': 'agentops-diagnostic-source-capture/1',
              'started_at_utc': stamp(), 'status': 'captured_with_gaps',
              'inspection_phase': 'post_capture', 'preexecution_module_fidelity': False,
              'limits': {'per_source_bytes': MAX_FILE_BYTES, 'total_source_bytes': MAX_TOTAL_BYTES,
                         'per_diagnostic_input_bytes': MAX_INPUT_BYTES},
              'inputs': [], 'sources': [], 'closure_gaps': [],
              'application_requests': 0, 'live_model_calls': 0}
    gaps, named = report['closure_gaps'], {}

    def gap(reason, **details):
        gaps.append({'reason': reason, **details})

    def add(filename, origin):
        if type(filename) is not str or not filename:
            gap('invalid_frame_filename', origin=origin)
        else:
            named.setdefault(filename, []).append(origin)

    def read_input(filename):
        path = case_dir / 'service/shutdown-diagnostics' / filename
        try:
            resolved = path.resolve(strict=True)
            if not resolved.is_relative_to(workspace) or path.is_symlink():
                gap('diagnostic_input_outside_or_symlink', input=filename)
                return None
            if resolved.stat().st_size > MAX_INPUT_BYTES:
                gap('diagnostic_input_byte_limit', input=filename)
                return None
            with resolved.open('rb') as stream:
                raw = stream.read(MAX_INPUT_BYTES + 1)
            if len(raw) > MAX_INPUT_BYTES:
                gap('diagnostic_input_byte_limit', input=filename)
                return None
            report['inputs'].append(digest(path, workspace, raw))
            return raw.decode('utf-8')
        except (OSError, ValueError) as error:
            gap('diagnostic_input_unavailable', input=filename, error_type=type(error).__name__)
            return None

    lifecycle = read_input('lifecycle.jsonl')
    if lifecycle is not None:
        for number, line in enumerate(lifecycle.splitlines(), 1):
            try:
                event = json.loads(line, object_pairs_hook=unique_pairs)
                if not isinstance(event, dict) or event.get('schema_version') != 'agentops-shutdown-event/2':
                    raise ValueError('Unexpected event schema')
                for kind in ('tasks', 'threads'):
                    if kind not in event:
                        continue
                    if not isinstance(event[kind], list):
                        raise ValueError('Invalid snapshot list')
                    for item, row in enumerate(event[kind]):
                        if not isinstance(row, dict) or not isinstance(row.get('stack'), list):
                            raise ValueError('Invalid stack list')
                        for index, frame in enumerate(row['stack']):
                            origin = {'input': 'lifecycle.jsonl', 'line': number,
                                      'kind': kind, 'item': item, 'frame': index}
                            add(frame.get('file') if isinstance(frame, dict) else None, origin)
            except (ValueError, TypeError) as error:
                gap('unparsed_lifecycle_record', line=number, error_type=type(error).__name__)
    trace = read_input('teardown-stacks.txt')
    if trace is not None:
        for number, line in enumerate(trace.splitlines(), 1):
            match = TRACE_FRAME.match(line)
            if match:
                add(match.group(1), {'input': 'teardown-stacks.txt', 'line': number})
            elif line.lstrip().startswith('File '):
                gap('unparsed_trace_frame', line=number)

    total = 0
    for filename, origins in sorted(named.items()):
        detail = {'original_linux_path': filename, 'origins': origins}
        try:
            source = Path(filename)
            if '\0' in filename or not source.is_absolute() or '..' in source.parts:
                gap('nonabsolute_or_traversal_frame_path', **detail)
                continue
            if source.suffix != '.py':
                gap('not_python_source_path', **detail)
                continue
            if not source.is_relative_to(workspace):
                gap('source_outside_workspace', **detail)
                continue
            resolved = source.resolve(strict=True)
            if not resolved.is_relative_to(workspace):
                gap('source_symlink_outside_workspace', **detail)
                continue
            before = resolved.stat()
            if not stat.S_ISREG(before.st_mode):
                gap('source_not_regular_file', **detail)
                continue
            if before.st_size > MAX_FILE_BYTES:
                gap('source_byte_limit', **detail)
                continue
            if total + before.st_size > MAX_TOTAL_BYTES:
                gap('total_source_byte_limit', **detail)
                continue
            with resolved.open('rb') as stream:
                raw = stream.read(MAX_FILE_BYTES + 1)
            after = resolved.stat()
            if len(raw) > MAX_FILE_BYTES or total + len(raw) > MAX_TOTAL_BYTES:
                gap('source_grew_beyond_byte_limit', **detail)
                continue
            identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
            if identity(before) != identity(after) or len(raw) != after.st_size:
                gap('source_changed_during_inspection', **detail)
                continue
            snapshot = output / f'source-{len(report["sources"]) + 1:04d}.py'
            with snapshot.open('xb') as stream:
                stream.write(raw)
            report['sources'].append({**detail,
                'original_workspace_relative_path': source.relative_to(workspace).as_posix(),
                'resolved_workspace_relative_path': resolved.relative_to(workspace).as_posix(),
                'snapshot': digest(snapshot, workspace, raw)})
            total += len(raw)
        except (OSError, ValueError) as error:
            gap('source_unavailable', **detail, error_type=type(error).__name__)
    report.update(status='captured' if not gaps else 'captured_with_gaps',
                  recorded_frame_paths=len(named), copied_sources=len(report['sources']),
                  copied_bytes=total, recorded_frame_source_closure=not gaps,
                  finished_at_utc=stamp())
    with (output / 'result.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    return report
