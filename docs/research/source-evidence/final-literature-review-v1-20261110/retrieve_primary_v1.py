"""Bounded raw primary retrieval; retain failures and never overwrite evidence."""
import concurrent.futures
import datetime as dt
import hashlib
import json
from pathlib import Path

import requests
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'raw-primary-v1'
OUT.mkdir(exist_ok=False)
SOURCES = [
    ('cegar', 'https://web.stanford.edu/class/cs357/cegar.pdf', 'pdf'),
    ('csp', 'https://www.cs.ubc.ca/~mack/Publications/AI77.pdf', 'pdf'),
    ('memo', 'https://www.cs.utexas.edu/~hunt/research/hash-cons/hash-cons-papers/michie-memo-nature-1968.pdf', 'pdf'),
    ('bmc', 'https://fmv.jku.at/papers/BiereCimattiClarkeZhu-TACAS99.pdf', 'pdf'),
    ('memo-publisher', 'https://www.nature.com/articles/218019a0', 'html'),
]

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def fetch(source):
    name, url, kind = source
    record = {'id': name, 'requested_url': url, 'started_at_utc': now()}
    try:
        with requests.get(url, timeout=(10, 20), stream=True) as response:
            record.update(status=response.status_code, final_url=response.url,
                          content_type=response.headers.get('Content-Type'))
            chunks = []
            size = 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > 5_000_000:
                    raise RuntimeError('response exceeds fixed 5 MB bound')
                chunks.append(chunk)
            body = b''.join(chunks)
            path = OUT / (name + '.' + kind)
            path.write_bytes(body)
            record.update(body_path=path.relative_to(ROOT).as_posix(),
                          body_bytes=len(body), body_sha256=hashlib.sha256(body).hexdigest())
            response.raise_for_status()
            if kind == 'pdf':
                if not body.startswith(b'%PDF-'):
                    raise ValueError('response is not a PDF')
                reader = PdfReader(path)
                texts = ['=== Physical page ' + str(i + 1) + ' ===\n' + (p.extract_text() or '')
                         for i, p in enumerate(reader.pages)]
                text_path = OUT / (name + '-extracted.txt')
                text_path.write_text('\n\n'.join(texts), encoding='utf-8')
                record.update(physical_pages=len(reader.pages),
                              extracted_text_path=text_path.relative_to(ROOT).as_posix(),
                              extraction='pypdf text extraction; physical pages do not establish proceedings pagination')
            record['outcome'] = 'success'
    except Exception as error:
        record.update(outcome='failure', error=type(error).__name__ + ': ' + str(error))
    record['finished_at_utc'] = now()
    return record

started = now()
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    results = list(pool.map(fetch, SOURCES))
manifest = {'schema_version': 'bounded-primary-retrieval/1', 'started_at_utc': started,
            'finished_at_utc': now(), 'max_workers': 3, 'max_body_bytes': 5_000_000,
            'raw_http_response_bodies': True, 'prior_system_results_reproduced': False,
            'sources': results}
(OUT / 'retrieval.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(manifest, ensure_ascii=True, indent=2))
