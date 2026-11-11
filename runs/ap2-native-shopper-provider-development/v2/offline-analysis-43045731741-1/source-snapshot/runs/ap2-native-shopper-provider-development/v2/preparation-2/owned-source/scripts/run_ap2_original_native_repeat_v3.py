"""Once-only original native AP2 entries with an accounted Gemini HTTP boundary.

Original native modules and GenAI payloads are unchanged. An owned scripted
caller and public Task reader are separate interventions. This is one fresh repeat
development control after the preserved V2 byte-budget partial, not held-out data.
"""
from __future__ import annotations

import argparse
import errno
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'runs/ap2-environment-preparation/source-stage-v1/manifest.json'
ENVIRONMENT = ROOT / 'runs/ap2-environment-preparation/installed-assessment-v1/environment-manifest.json'
STAGE_SHA = '78828cea09bdd387230a2fc0772b542beabfe07b72c3a2f24b24c02c1a2f4463'
ENVIRONMENT_SHA = '4d6efdd2e4003b82517f45aead140a7afd6f1e180b3ce518904d87c96e5adeb5'
SOURCE = STAGE.parent / 'ap2'
MODEL = 'gemini-3.1-flash-lite-preview'
API_PATH = '/v1beta/models/' + MODEL + ':generateContent'
API_ORIGIN = 'https://generativelanguage.googleapis.com'
SYNTHETIC_KEY = 'AP2_OWNED_ACCOUNTED_DOWNSTREAM_KEY_NOT_A_PROVIDER_CREDENTIAL'
MAX_CALLS, MIN_INTERVAL, MAX_REQUEST_BYTES, MAX_RESPONSE_BYTES = 80, 6.0, 131072, 1048576
MAX_TOTAL_REQUEST_BYTES, MAX_TOTAL_USAGE_TOKENS = 200000, 100000
PORT_PREFLIGHT_WAIT_SECONDS = 8.0
SERVICE_ENTRIES = (
    ('merchant', 'roles.merchant_agent', 8001, '/a2a/merchant_agent'),
    ('credentials', 'roles.credentials_provider_agent', 8002, '/a2a/credentials_provider'),
    ('processor', 'roles.merchant_payment_processor_agent', 8003, '/a2a/merchant_payment_processor_agent'),
)
OWNED = ('scripts/run_ap2_original_native_repeat_v3.py',
         'scripts/ap2_public_scripted_continuation_v2.py',
         'src/interoperability/ap2_public_scripted_continuation_v2.py',
         'src/interoperability/ap2_public_task_read_v1.py', 'src/interoperability/ap2_public_original_binding_v2.py')


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def file_record(path):
    return {'path': str(path), **digest(path.read_bytes())}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def append(path, value):
    with path.open('ab') as stream:
        stream.write((json.dumps(value, sort_keys=True, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())


def normal_name(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def expected_versions():
    raw = ENVIRONMENT.read_bytes()
    if digest(raw)['sha256'] != ENVIRONMENT_SHA:
        raise ValueError('pinned_original_version_manifest_changed')
    excluded = {'ap2', 'ap2-samples', 'x402-a2a', 'pywin32', 'pywin32-ctypes', 'wmi'}
    original = json.loads(raw)['all_distributions']
    return {normal_name(name): row['version'] for name, row in original.items()
            if name.lower() not in excluded}


def source_records():
    raw = STAGE.read_bytes()
    if digest(raw)['sha256'] != STAGE_SHA:
        raise ValueError('pinned_original_source_manifest_changed')
    manifest = json.loads(raw)
    rows = {row['path']: {key: row[key] for key in ('bytes', 'sha256')}
            for row in manifest['files'] if row['project'] == 'ap2'}
    if manifest['ap2_commit'] != 'e1ea56db72a6385bce3e5c1112b3a56ce60acb43' or len(rows) != 136:
        raise ValueError('original_complete_source_membership_changed')
    for relative, expected in rows.items():
        if digest((SOURCE / relative).read_bytes()) != expected:
            raise ValueError('original_source_bytes_changed:' + relative)
    actual_members = {p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob('*')
                      if p.is_file() and p.suffix != '.pyc' and '__pycache__' not in p.parts}
    if actual_members != set(rows):
        raise ValueError('original_source_tree_membership_changed')
    return rows


def x402_source_records():
    raw = STAGE.read_bytes()
    if digest(raw)['sha256'] != STAGE_SHA:
        raise ValueError('pinned_original_source_manifest_changed')
    manifest = json.loads(raw)
    rows = {row['path']: {key: row[key] for key in ('bytes', 'sha256')}
            for row in manifest['files'] if row['project'] == 'a2a-x402'}
    if len(rows) != 24 or manifest['x402_files'] != 24:
        raise ValueError('x402_source_membership_changed')
    for relative, expected in rows.items():
        if digest((STAGE.parent / 'a2a-x402' / relative).read_bytes()) != expected:
            raise ValueError('x402_source_bytes_changed:' + relative)
    source = STAGE.parent / 'a2a-x402'
    actual_members = {p.relative_to(source).as_posix() for p in source.rglob('*')
                      if p.is_file() and p.suffix != '.pyc' and '__pycache__' not in p.parts}
    if actual_members != set(rows):
        raise ValueError('x402_source_tree_membership_changed')
    return rows


def task_facts():
    # A separate adaptive development control, not a replacement V2 attempt.
    return [dict(case_id='ap2-native-provider-v3-repeat-completed',
                 catalog_search='unbranded walking shoes', user_email='bugsbunny@gmail.com',
                 cart_index=0, payment_method_index=0, wallet_consent=True,
                 confirm_cart=True, otp_response='123', fault='none', repeat_after_completed=True)]


def fixed_plan_fields():
    return {
        'schema_version': 'ap2-original-native-provider-screen/3',
        'source_stage_sha256': STAGE_SHA, 'original_windows_environment_sha256': ENVIRONMENT_SHA,
        'model': MODEL, 'provider_origin': API_ORIGIN, 'provider_path': API_PATH,
        'limits': {'upstream_calls_including_smoke': MAX_CALLS, 'minimum_interval_seconds': MIN_INTERVAL,
                   'maximum_total_request_bytes': MAX_TOTAL_REQUEST_BYTES,
                   'maximum_observed_usage_tokens_before_stopping': MAX_TOTAL_USAGE_TOKENS,
                   'request_timeout_seconds': 45, 'caller_timeout_seconds': 300,
                   'screen_timeout_seconds': 1500, 'port_preflight_wait_seconds': PORT_PREFLIGHT_WAIT_SECONDS},
        'linux_native_pid_listener_ownership_required': True,
        'source_and_sdk_unchanged': True, 'owned_base_url_accounting_proxy': True,
        'original_run_sh_provisioning_qualified': False, 'unchanged_adk_shopper_qualified': False,
        'human_gold_qualified': False, 'held_out_study': False, 'provider_requests': 0,
        'adaptive_development_followup': True, 'preserved_source_run': 42995902326,
        'preserved_source_archive_sha256': '5aa54a06193b25416e6d952fdee9be2af1760fd60fed596107906c5864bb2bf3',
    }


def prepare(output):
    if output.exists():
        raise ValueError('fresh_plan_directory_required')
    sources, versions, x402_sources = source_records(), expected_versions(), x402_source_records()
    output.mkdir(parents=True)
    owned = {name: digest((ROOT / name).read_bytes()) for name in OWNED}
    write(output / 'plan.json', {
        **fixed_plan_fields(), 'prepared_at': now(),
        'sources': sources, 'x402_sources': x402_sources, 'versions': versions, 'owned_sources': owned, 'facts': task_facts(),
    })
    (output / 'requirements.txt').write_text(''.join(f'{n}=={v}\n' for n, v in sorted(versions.items())), encoding='utf-8')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ProviderBoundary:
    """Serial, shared, durable upstream allocations. Only this object holds the key."""
    def __init__(self, output, secret, *, mode='live', send=None, interval=MIN_INTERVAL, clock=time.monotonic, sleeper=time.sleep):
        if mode not in {'live', 'fixture'} or (mode == 'live' and not secret):
            raise ValueError('explicit_provider_mode_and_live_credential_required')
        if mode == 'fixture' and secret:
            raise ValueError('fixture_mode_must_not_receive_a_real_credential')
        if mode == 'fixture' and send is None:
            raise ValueError('fixture_mode_requires_an_explicit_owned_response_function')
        self.output, self.secret, self.mode = output, secret, mode
        self.send = send or self._send_live
        self.interval, self.clock, self.sleeper = interval, clock, sleeper
        self.lock, self.last_started = threading.Lock(), None
        self.calls, self.request_bytes, self.usage_tokens, self.successful_responses = 0, 0, 0, 0
        self.unknown_usage_responses = 0
        self.stopped, self.failed = False, False
        self.output.mkdir(parents=True, exist_ok=False)

    def redact(self, raw):
        return raw.replace(self.secret.encode(), b'[REDACTED_PROVIDER_SECRET]') if self.secret else raw

    def _send_live(self, raw):
        req = urllib.request.Request(API_ORIGIN + API_PATH, data=raw,
              headers={'Content-Type': 'application/json', 'x-goog-api-key': self.secret}, method='POST')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        try:
            response = opener.open(req, timeout=45)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise ValueError('provider_response_size_bound')
            return response.status, body

    def request(self, path, raw, downstream_key):
        if path != API_PATH or downstream_key != SYNTHETIC_KEY or not raw or len(raw) > MAX_REQUEST_BYTES:
            return 400, b'{"error":{"message":"owned_provider_request_refused"}}'
        try:
            payload = json.loads(raw)
            if type(payload) is not dict or 'contents' not in payload:
                raise ValueError('invalid_generate_payload')
        except (ValueError, UnicodeDecodeError):
            return 400, b'{"error":{"message":"owned_provider_invalid_json"}}'
        with self.lock:
            if self.stopped or self.calls >= MAX_CALLS or self.request_bytes + len(raw) > MAX_TOTAL_REQUEST_BYTES or self.usage_tokens >= MAX_TOTAL_USAGE_TOKENS:
                self.stopped = True
                append(self.output / 'local-refusals.jsonl', {'time': now(), 'status': 'no_upstream_call_budget_or_prior_failure'})
                return 429, b'{"error":{"message":"owned_provider_budget_or_prior_failure"}}'
            if self.last_started is not None:
                self.sleeper(max(0.0, self.interval - (self.clock() - self.last_started)))
            self.last_started = self.clock()
            number = self.calls
            self.calls += 1
            self.request_bytes += len(raw)
            request_path = self.output / f'{number:03d}.request.json'
            request_path.write_bytes(self.redact(raw))
            append(self.output / 'ledger.jsonl', {'allocation': number, 'phase': 'started', 'time': now(),
                   'provider_mode': self.mode, 'path': API_PATH, 'request': digest(self.redact(raw)),
                   'upstream_call_consumed': True, 'retry': False})
            status, body, problem = 502, b'{"error":{"message":"owned_provider_transport_failure"}}', None
            try:
                status, body = self.send(raw)
                if type(status) is not int or type(body) is not bytes or len(body) > MAX_RESPONSE_BYTES:
                    raise ValueError('malformed_provider_response')
                body = self.redact(body)
                parsed = json.loads(body)
                usage = parsed.get('usageMetadata', {}) if type(parsed) is dict else {}
                total = usage.get('totalTokenCount')
                if status == 200 and (type(total) is not int or total <= 0):
                    self.unknown_usage_responses += 1
                    self.stopped = True
                    total = 0
                elif status != 200 and total is None:
                    total = 0
                if type(total) is not int or total < 0:
                    raise ValueError('malformed_provider_usage')
                self.usage_tokens += total
                if status == 200:
                    self.successful_responses += 1
            except BaseException as error:
                problem = type(error).__name__
                self.stopped = self.failed = True
                # Preserve a received adverse HTTP/body observation, including
                # HTML, malformed JSON and usage errors. No replacement result.
                if type(status) is not int or type(body) is not bytes or len(body) > MAX_RESPONSE_BYTES:
                    status, body = 502, b'{"error":{"message":"owned_provider_transport_or_size_failure"}}'
            if status != 200:
                self.stopped = self.failed = True
            response_path = self.output / f'{number:03d}.response.json'
            response_path.write_bytes(body)
            append(self.output / 'ledger.jsonl', {'allocation': number, 'phase': 'finished', 'time': now(),
                   'http_status': status, 'response': digest(body), 'transport_error_type': problem,
                   'observed_cumulative_usage_tokens': self.usage_tokens, 'upstream_call_consumed': True})
            return status, body

    def summary(self):
        return {'provider_mode': self.mode, 'upstream_allocations': self.calls,
                'cumulative_request_bytes': self.request_bytes, 'observed_usage_tokens': self.usage_tokens,
                'responses_with_unknown_usage': self.unknown_usage_responses,
                'usage_threshold_is_a_post_response_stop_not_a_hard_token_cap': True,
                'stopped': self.stopped, 'failed': self.failed,
                'successful_provider_responses': self.successful_responses,
                'actual_live_generation_responses_observed': self.mode == 'live' and self.successful_responses > 0}


def make_proxy(boundary):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            length = self.headers.get('Content-Length', '')
            if not length.isdecimal() or int(length) > MAX_REQUEST_BYTES or self.headers.get('Transfer-Encoding'):
                status, raw = 400, b'{"error":{"message":"owned_provider_invalid_length"}}'
            else:
                status, raw = boundary.request(self.path, self.rfile.read(int(length)), self.headers.get('x-goog-api-key'))
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        def do_GET(self):
            self.send_error(405)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def smoke(boundary):
    payload = {'contents': [{'role': 'user', 'parts': [{'text': 'Call the access_check function once.'}]}],
               'tools': [{'functionDeclarations': [{'name': 'access_check', 'description': 'Return the access check.',
                          'parameters': {'type': 'OBJECT', 'properties': {}}}]}],
               'toolConfig': {'functionCallingConfig': {'mode': 'ANY'}},
               'generationConfig': {'maxOutputTokens': 64}}
    status, raw = boundary.request(API_PATH, json.dumps(payload).encode(), SYNTHETIC_KEY)
    passed = False
    if status == 200:
        try:
            parts = json.loads(raw)['candidates'][0]['content']['parts']
            passed = any(p.get('functionCall', {}).get('name') == 'access_check' for p in parts)
        except (ValueError, KeyError, TypeError, IndexError):
            pass
    if not passed:
        boundary.stopped = True
    return {'http_status': status, 'exact_original_model': MODEL, 'forced_tool_observed': passed,
            'status': 'provider_access_smoke_passed' if passed else 'provider_access_smoke_failed',
            'calls': boundary.calls, 'independent_provider_capacity_verified': False,
            'limits_are_conservative_run_bounds_not_verified_account_quota': True}


def child_environment(work, site_packages, proxy_url, *, caller=False):
    names = ('PATH', 'SystemRoot', 'WINDIR', 'LANG', 'LC_ALL', 'LD_LIBRARY_PATH')
    env = {name: os.environ[name] for name in names if name in os.environ}
    sample = SOURCE / 'code/samples/python/src'
    x402 = STAGE.parent / 'a2a-x402/python/x402_a2a/src'
    env.update(PYTHONPATH=os.pathsep.join(map(str, (ROOT / 'src', sample, SOURCE / 'code/sdk/python', x402, site_packages))),
               PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1', PAYMENT_METHOD='CARD',
               TEMP_DB_DIR=str(work / 'state'), AGENT_PROVIDER_PUBLIC_KEY_PATH=str(work / 'state/agent_provider_signing_key.pub'),
               HOME=str(work), TMPDIR=str(work / 'tmp'), TEMP=str(work / 'tmp'), TMP=str(work / 'tmp'),
               NO_PROXY='localhost,127.0.0.1,::1')
    if not caller:
        env.update(GOOGLE_API_KEY=SYNTHETIC_KEY, GOOGLE_GENAI_USE_VERTEXAI='false', GOOGLE_GEMINI_BASE_URL=proxy_url)
    return env


def portable_runtime(python, site_packages, pip_report, output, versions):
    if not python.is_file() or not site_packages.is_dir() or not pip_report.is_file():
        raise ValueError('prepared_python_site_and_pip_report_required')
    result = subprocess.run([str(python), '-I', '-B', '-c',
        "import importlib.metadata,json,sys; print(json.dumps({'python_executable':sys.executable,'python_version':sys.version.split()[0],'python_version_string':sys.version,'root':sys.prefix,'distributions':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()}}))"],
        capture_output=True, timeout=30, check=True)
    info = json.loads(result.stdout)
    actual = {normal_name(name): version for name, version in info['distributions'].items()}
    if any(actual.get(name) != version for name, version in versions.items()):
        raise ValueError('installed_distribution_version_mismatch')
    runtime_root = Path(info['root']).resolve(strict=True)
    if not site_packages.is_relative_to(runtime_root):
        raise ValueError('site_packages_outside_exact_python_runtime')
    files = {}
    for path in sorted(site_packages.rglob('*')):
        if path.is_symlink():
            raise ValueError('linked_runtime_file')
        if path.is_file() and path.suffix != '.pyc' and '__pycache__' not in path.parts:
            files[path.relative_to(runtime_root).as_posix()] = digest(path.read_bytes())
    value = dict(info, root=str(runtime_root), site_packages=str(site_packages), files=files,
                 distributions=actual, required_original_versions=versions,
                 pip_report=file_record(pip_report), source_stage_sha256=STAGE_SHA,
                 original_windows_environment_sha256=ENVIRONMENT_SHA,
                 compiled_windows_wheel_hashes_apply_to_linux=False)
    path = output / 'portable-runtime.json'
    write(path, value)
    return path, digest(path.read_bytes())['sha256']


def safe_exception(error, secret=''):
    message = str(error).replace(secret, '[REDACTED_PROVIDER_SECRET]') if secret else str(error)
    if 'PRIVATE KEY-----' in message:
        message = 'private_key_material_message_redacted'
    return {'type': type(error).__name__, 'errno': error.errno if isinstance(error, OSError) else None,
            'message': ' '.join(message.split())[:500]}


def require_free_ports(*, record=None, timeout=PORT_PREFLIGHT_WAIT_SECONDS):
    """Bind-only original listener semantics; never contacts a foreign listener."""
    deadline = time.monotonic() + timeout
    while True:
        sockets, pending, problem = [], None, None
        try:
            for _, _, port, _ in SERVICE_ENTRIES:
                pending = port
                sock = socket.socket()
                sockets.append(sock)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('127.0.0.1', port))
            if record:
                record({'time': now(), 'status': 'bind_only_reuseaddr_preflight_passed',
                        'ports': [entry[2] for entry in SERVICE_ENTRIES], 'foreign_service_contacted': False})
            return
        except OSError as error:
            problem = error
            if record:
                record({'time': now(), 'status': 'bind_only_reuseaddr_preflight_refused',
                        'port': pending, 'error': safe_exception(error), 'foreign_service_contacted': False})
        finally:
            for sock in sockets:
                sock.close()
        if problem.errno != errno.EADDRINUSE or time.monotonic() >= deadline:
            raise problem
        time.sleep(min(0.25, max(0.0, deadline - time.monotonic())))


def owned_listener(process, port, *, proc_root=Path('/proc')):
    """Require the exact native process to own its Linux listening socket inode."""
    if process.poll() is not None:
        return False
    owned = set()
    fd_root = proc_root / str(process.pid) / 'fd'
    try:
        for path in fd_root.iterdir():
            try:
                target = os.readlink(path)
            except OSError:
                continue
            if target.startswith('socket:[') and target.endswith(']'):
                owned.add(target[8:-1])
        with (proc_root / 'net/tcp').open() as stream:
            lines = stream.read().splitlines()[1:]
    except OSError:
        return False
    expected = '0100007F:' + f'{port:04X}'
    for line in lines:
        fields = line.split()
        if len(fields) >= 10 and fields[1].upper() == expected and fields[3] == '0A' and fields[9] in owned:
            return True
    return False


def wait_cards(processes, output, timeout=45):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    deadline, found = time.monotonic() + timeout, {}
    while time.monotonic() < deadline:
        if any(process.poll() is not None for process in processes):
            raise ValueError('original_native_service_exited_before_card_readiness')
        for index, (name, _, port, route) in enumerate(SERVICE_ENTRIES):
            if name in found:
                continue
            # A bind-release race cannot turn another process's card into ours.
            # No request is sent until this exact native PID owns the listener.
            if not owned_listener(processes[index], port):
                continue
            try:
                with opener.open(f'http://127.0.0.1:{port}{route}/.well-known/agent-card.json', timeout=1) as response:
                    raw = response.read(MAX_RESPONSE_BYTES + 1)
                    value = json.loads(raw)
                    if response.status != 200 or len(raw) > MAX_RESPONSE_BYTES or value.get('protocolVersion') != '0.3.0':
                        raise ValueError('original_native_card_identity_mismatch')
                    (output / f'{name}.agent-card.json').write_bytes(raw)
                    found[name] = digest(raw)
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
        if len(found) == 3:
            return found
        time.sleep(0.25)
    raise TimeoutError('original_native_service_card_readiness_deadline')


def stop_processes(processes):
    statuses = []
    for process in reversed(processes):
        problem = None
        try:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
        except BaseException as error:
            problem = type(error).__name__
            try:
                process.kill()
                process.wait(timeout=10)
            except BaseException as cleanup_error:
                problem += ':' + type(cleanup_error).__name__
        statuses.append({'pid': process.pid, 'returncode': process.returncode,
                         'reaped': process.poll() is not None, 'cleanup_error_type': problem})
    return statuses


def archive_safety(output, secret):
    checked = 0
    for path in output.rglob('*'):
        if not path.is_file():
            continue
        raw = path.read_bytes()
        if path.suffix.lower() in {'.pem', '.key'} or path.name == '.env' or b'PRIVATE KEY-----' in raw or (secret and secret.encode() in raw):
            raise ValueError('unsafe_retained_secret_or_private_key')
        checked += 1
    return checked


def execute(plan_dir, output, python, site_packages, pip_report, mode):
    if output.exists():
        raise ValueError('fresh_execution_directory_required')
    plan = json.loads((plan_dir / 'plan.json').read_bytes())
    if any(json.dumps(plan.get(key), sort_keys=True) != json.dumps(value, sort_keys=True)
           for key, value in fixed_plan_fields().items()):
        raise ValueError('prospective_plan_fixed_bounds_bindings_or_qualification_changed')
    if (plan['sources'] != source_records() or plan.get('x402_sources') != x402_source_records()
            or plan['versions'] != expected_versions() or plan['facts'] != task_facts()
            or plan.get('model') != MODEL or plan.get('provider_origin') != API_ORIGIN or plan.get('provider_path') != API_PATH
            or plan.get('schema_version') != 'ap2-original-native-provider-screen/3'):
        raise ValueError('prospective_plan_or_original_source_changed')
    if set(plan.get('owned_sources', {})) != set(OWNED):
        raise ValueError('owned_plan_source_membership_changed')
    if any(digest((ROOT / name).read_bytes()) != expected for name, expected in plan['owned_sources'].items()):
        raise ValueError('owned_runner_or_caller_changed_after_plan')
    if sys.platform != 'linux':
        raise ValueError('linux_original_listener_pid_ownership_required_for_v2_execution')
    if mode != 'live':
        raise ValueError('application_execution_requires_explicit_live_mode_fixture_is_controls_only')
    secret = os.environ.get('GOOGLE_API_KEY', '')
    if not secret or secret == SYNTHETIC_KEY:
        raise ValueError('real_provider_secret_missing')
    output.mkdir(parents=True)
    start = time.monotonic()
    deadline = start + 1500
    rows = [{'case_id': facts['case_id'], 'status': 'unexecuted', 'reason': 'provider_smoke_not_passed'} for facts in plan['facts']]
    write(output / 'opening.json', {'time': now(), 'plan': file_record(plan_dir / 'plan.json'),
          'prospective_tasks': rows, 'source_stage_sha256': STAGE_SHA, 'provider_mode': mode,
          'actual_secret_persisted': False, 'scripted_public_caller_intervention': True})
    try:
        runtime_path, runtime_sha = portable_runtime(python, site_packages, pip_report, output, plan['versions'])
    except Exception as error:
        write(output / 'result.json', {'schema_version': 'ap2-original-native-provider-screen-result/3',
              'completed_at': now(), 'cases': rows, 'allocated_task_count': 1, 'unexecuted_count': 1,
              'failure_type': type(error).__name__, 'status': 'runtime_preflight_failed_before_provider_or_task_calls',
              'provider': {'upstream_allocations': 0}, 'whole_task_grades': None, 'error': safe_exception(error, secret),
              'all_attempts_and_missing_tasks_retained': True})
        write(output / 'archive-safety.json', {'checked_files': archive_safety(output, secret),
              'provider_secret_or_private_key_found': False})
        return
    boundary = ProviderBoundary(output / 'provider', secret, mode=mode)
    server = thread = None
    problem = None
    try:
        observed_smoke = smoke(boundary)
        write(output / 'provider-access-smoke.json', observed_smoke)
        if not observed_smoke['forced_tool_observed']:
            return
        server, thread = make_proxy(boundary)
        proxy_url = f'http://127.0.0.1:{server.server_port}'
        for index, facts in enumerate(plan['facts']):
            if boundary.stopped or time.monotonic() >= deadline:
                rows[index].update(reason='provider_budget_failure_or_screen_deadline')
                continue
            case_dir = output / 'cases' / facts['case_id']
            case_dir.mkdir(parents=True, exist_ok=False)
            public_path = case_dir / (facts['case_id'] + '.public-human-facts.json')
            write(public_path, facts)
            rows[index].update(status='started', reason=None, started_at=now())
            append(output / 'task-ledger.jsonl', rows[index])
            processes, handles = [], []
            with tempfile.TemporaryDirectory(prefix='ap2-native-provider-private-') as private:
                work = Path(private)
                for subdir in ('state', '.logs', 'tmp'):
                    (work / subdir).mkdir()
                try:
                    require_free_ports(timeout=max(0.0, min(PORT_PREFLIGHT_WAIT_SECONDS, deadline - time.monotonic())),
                        record=lambda record: append(case_dir / 'native-port-preflight.jsonl', record))
                    env = child_environment(work, site_packages, proxy_url)
                    for name, module, port, route in SERVICE_ENTRIES:
                        handle = (case_dir / f'{name}.stdout.log').open('xb')
                        handles.append(handle)
                        command = [str(python), '-B', '-m', module]
                        processes.append(subprocess.Popen(command, cwd=work, env=env, stdout=handle, stderr=subprocess.STDOUT))
                    cards = wait_cards(processes, case_dir, timeout=max(0.0, min(45.0, deadline - time.monotonic())))
                    write(case_dir / 'native-launch.json', {'entries': [{'module': m, 'port': p, 'rpc_path': r} for _, m, p, r in SERVICE_ENTRIES],
                          'public_cards': cards, 'original_entrypoints': True, 'original_genai_client_replaced': False,
                          'owned_accounting_base_url': proxy_url, 'secret_in_children': False,
                          'exact_native_pid_listener_ownership_verified_before_card_requests': True})
                    caller_env = child_environment(work, site_packages, proxy_url, caller=True)
                    command = [str(python), '-B', str(ROOT / 'scripts/ap2_public_scripted_continuation_v2.py'),
                               '--source-stage', str(STAGE), '--environment-manifest', str(runtime_path),
                               '--environment-manifest-sha256', runtime_sha, '--site-packages', str(site_packages),
                               '--task-root', str(work), '--samples-root', str(SOURCE / 'code/samples/python/src'),
                               '--public-human-facts', str(public_path), '--output', str(case_dir / 'caller')]
                    caller_log = (case_dir / 'caller.stdout.log').open('xb')
                    handles.append(caller_log)
                    caller = subprocess.Popen(command, cwd=work, env=caller_env, stdout=caller_log, stderr=subprocess.STDOUT)
                    processes.append(caller)
                    try:
                        caller.wait(timeout=max(0.0, min(300.0, deadline - time.monotonic())))
                    except subprocess.TimeoutExpired:
                        rows[index].update(status='executed_timeout_retained', reason='caller_parent_300_second_deadline')
                    else:
                        rows[index].update(status='executed_returned' if caller.returncode == 0 else 'executed_nonzero_retained',
                                           caller_returncode=caller.returncode)
                except BaseException as error:
                    rows[index].update(status='executed_launch_or_readiness_failure_retained', reason=type(error).__name__,
                                       error=safe_exception(error, secret))
                finally:
                    rows[index]['process_cleanup'] = stop_processes(processes)
                    for handle in handles:
                        handle.close()
                    watch = work / '.logs/watch.log'
                    if watch.is_file():
                        (case_dir / 'original-watch.log').write_bytes(boundary.redact(watch.read_bytes()))
                    rows[index].update(finished_at=now(), original_private_state_retained=False)
                    append(output / 'task-ledger.jsonl', rows[index])
    except BaseException as error:
        problem = type(error).__name__
    finally:
        boundary.stopped = True
        if server is not None:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        # Active HTTP handlers can outlive their caller's termination. Drain
        # the one serial upstream call before taking final census/safety hashes.
        with boundary.lock:
            boundary.stopped = True
        write(output / 'result.json', {'schema_version': 'ap2-original-native-provider-screen-result/3',
              'completed_at': now(), 'cases': rows, 'allocated_task_count': 1,
              'unexecuted_count': sum(r['status'] == 'unexecuted' for r in rows), 'failure_type': problem,
              'provider': boundary.summary(), 'source_stage_sha256': STAGE_SHA,
              'portable_runtime_sha256': runtime_sha, 'original_run_sh_provisioning_qualified': False,
              'unchanged_adk_shopper_qualified': False, 'human_gold_qualified': False,
              'whole_task_grades': None, 'exact_A2A_wire_capture_claimed': False,
              'all_attempts_and_missing_tasks_retained': True})
        count = archive_safety(output, secret)
        write(output / 'archive-safety.json', {'checked_files': count, 'provider_secret_or_private_key_found': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'execute'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--python', type=Path)
    parser.add_argument('--site-packages', type=Path)
    parser.add_argument('--pip-report', type=Path)
    parser.add_argument('--provider-mode', choices=('live', 'fixture'))
    args = parser.parse_args()
    if args.mode == 'prepare':
        prepare(args.output.resolve())
    else:
        if any(value is None for value in (args.plan, args.python, args.site_packages, args.pip_report, args.provider_mode)):
            parser.error('execute requires plan/python/site-packages/pip-report/provider-mode')
        # Preserve the venv executable path. Resolving its symlink changes
        # Python's sys.prefix to the global interpreter and loses the venv.
        execute(args.plan.resolve(), args.output.resolve(), args.python.absolute(), args.site_packages.resolve(), args.pip_report.resolve(), args.provider_mode)
    print(json.dumps({'mode': args.mode, 'output': str(args.output), 'provider_secret_printed': False}))


if __name__ == '__main__':
    main()
