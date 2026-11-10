"""Read-only citation/source integrity audit, not an automated scientific review."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/research/source-evidence/final-literature-review-v1-20261110'


def require(value, message):
    if not value:
        raise ValueError(message)


def load(path):
    return json.loads(path.read_bytes())


def normalized(value):
    value = unicodedata.normalize('NFKD', value)
    return ''.join(c.lower() for c in value if c.isalnum() and not unicodedata.combining(c))


def record(path):
    data = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


def audit():
    data = load(ROOT / 'paper/references-v3.json')
    prior = load(ROOT / 'paper/references-v2.json')
    entries = data['entries']
    require(len(entries) == 22, 'Expected22 references')
    require([entry['number'] for entry in entries] == list(range(1, 23)), 'Numbering changed')
    require(len(set(entry['key'] for entry in entries)) == 22, 'Duplicate citation key')
    require(data['primary_metadata_checked_entries'] == 22
            and data['human_metadata_review_completed'] is False
            and data['prior_system_results_reproduced'] is False
            and data['complete_final_publication_bibliography'] is False,
            'Review scope incorrectly claimed')
    for old, entry in zip(prior['entries'], entries):
        require((old['number'], old['key'], old['type']) == (entry['number'], entry['key'], entry['type']),
                'Existing citation identity changed')
        changed = {key for key in set(old['fields']) | set(entry['fields'])
                   if old['fields'].get(key) != entry['fields'].get(key)}
        allowed = {3: {'doi'}, 14: {'note'}, 15: {'note'}}.get(entry['number'], set())
        require(changed <= allowed, 'Unexpected retained metadata change for' + str(entry['number']))
        require(all(item in entry['evidence'] for item in old['evidence']), 'Prior evidence removed')

    bib = (ROOT / 'paper/references-v3.bib').read_text(encoding='utf-8')
    md = (ROOT / 'paper/references-v3.md').read_text(encoding='utf-8')
    require(re.findall(r'(?m)^@\w+\{([^,]+),', bib) == [entry['key'] for entry in entries], 'BibTeX key order mismatch')
    require([int(n) for n in re.findall(r'(?m)^(\d+)\. ', md)] == list(range(1, 23)), 'Markdown numbering mismatch')
    require(bib.count('{') == bib.count('}'), 'Unbalanced BibTeX braces')
    for text in (bib, md, (ROOT / 'paper/references-v3.json').read_text(encoding='utf-8')):
        require('\ufffd' not in text, 'Replacement character in citation artifact')

    matched = []
    evidence_paths = set()
    for entry in entries:
        require(all(isinstance(entry['fields'].get(key), str) and entry['fields'][key]
                    for key in ('title', 'author', 'year', 'url')), 'Missing citation field')
        require(entry['fields']['url'].startswith('https://'), 'Unexpected primary citation URL')
        review = entry['primary_metadata_review']
        require(review['human_review'] is False and review['prior_system_results_reproduced'] is False,
                'Per-entry review exceeds scope')
        texts = []
        for item in entry['evidence']:
            path = ROOT / item['path']
            require(path.is_file() and item['location'] and item['format'], 'Missing citation evidence')
            evidence_paths.add(path.relative_to(ROOT).as_posix())
            if path.is_relative_to(BASE) and path.suffix in ('.json', '.html', '.txt'):
                texts.append(path.read_text(encoding='utf-8'))
        combined = normalized('\n'.join(texts))
        if entry['number'] == 8:
            footer = ROOT / 'docs/research/source-evidence/final-literature-public-v1/quotient-publication-footer.json'
            evidence_paths.add(footer.relative_to(ROOT).as_posix())
            combined += normalized(footer.read_text(encoding='utf-8'))
        require(normalized(entry['fields']['title']) in combined,
                'Fresh primary evidence does not contain title for' + str(entry['number']))
        if 'doi' in entry['fields']:
            require(normalized(entry['fields']['doi']) in combined,
                    'Fresh primary evidence lacks retained DOI for' + str(entry['number']))
        require(entry['fields']['year'] in combined, 'Fresh primary evidence lacks cited year for ' + str(entry['number']))
        matched.append(entry['number'])

    manifest = load(BASE / 'manifest.json')
    for item in manifest['sources'] + manifest['bibliography_artifacts'] + manifest['frozen_paper_v4']:
        require(record(ROOT / item['path']) == item, 'Manifest/source mismatch: ' + item['path'])
    software = load(BASE / 'software-pin-review/receipt.json')
    require(software['status'] == 'verified' and software['source_lock_matches'] is True,
            'Software pins not verified')
    require(hashlib.sha256((ROOT / 'external/source-lock.json').read_bytes()).hexdigest()
            == software['local_source_lock_sha256'], 'Software source lock changed')
    for item in software['files']:
        path = BASE / 'software-pin-review' / item['path']
        require(len(path.read_bytes()) == item['bytes']
                and hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], 'Software response changed')
    for i, (prefix, repo) in enumerate(zip(('amirk', 'mgcrea'), software['repositories'])):
        commit = load(BASE / 'software-pin-review' / (prefix + '-commit-response.json'))
        license_value = load(BASE / 'software-pin-review' / (prefix + '-license-response.json'))
        license_bytes = (BASE / 'software-pin-review' / (prefix + '-LICENSE')).read_bytes()
        require(commit['sha'] == repo['pin'] and repo['pin'] in entries[13 + i]['fields']['howpublished'],
                'Software commit citation mismatch')
        require(commit['commit']['author']['date'] == repo['author_date'], 'Software date mismatch')
        require(license_value['license']['spdx_id'] == repo['license_spdx'], 'Software license metadata mismatch')
        blob = b'blob ' + str(len(license_bytes)).encode('ascii') + b'\0' + license_bytes
        require(hashlib.sha1(blob).hexdigest() == license_value['sha'], 'Pinned license bytes differ from Git blob')

    note = (ROOT / 'docs/research/final-literature-review-v1.md').read_text(encoding='utf-8')
    require('**Signed:** Codex AI' in note and '**Human review:** no.' in note
            and 'subjective AI assessment' in note, 'Assessment signature/scope missing')
    require('not an exhaustive systematic review' in note, 'Literature search scope overstated')
    require('39/66' in note and '54/66' in note and '1,024 to 16' in note
            and '5,566 to 14,773' in note and '8,895 bytes' in note,
            'Established adverse result missing')
    return {'schema_version': 'bibliography-v3-read-only-audit/1', 'status': 'passed',
            'checked_at_utc': datetime.now(timezone.utc).isoformat(),
            'references': 22, 'existing_numbering_preserved': 18,
            'primary_title_year_doi_matches': matched,
            'fresh_source_files_verified': len(manifest['sources']),
            'all_citation_evidence_files_exist': len(evidence_paths),
            'software_pin_and_license_blob_checks': 2,
            'frozen_paper_v4_unchanged': True,
            'artifacts': [record(ROOT / name) for name in ('paper/references-v3.json',
                'paper/references-v3.bib', 'paper/references-v3.md', 'paper/build_references_v3.py',
                'paper/audit_references_v3.py', 'docs/research/final-literature-review-v1.md')],
            'source_manifest': record(BASE / 'manifest.json'),
            'human_review': False, 'novelty_proven': False, 'prior_system_results_reproduced': False,
            'limits': 'Automated audit checks citation identities, primary evidence occurrence and immutable bytes. Signed method judgments remain subjective AI assessment.'}


if __name__ == '__main__':
    import argparse
    import traceback
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    path = ROOT / args.output
    require(not path.exists(), 'Audit allocation already consumed')
    try:
        result = audit()
    except Exception as error:
        result = {'status': 'failed', 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
                  'error': str(error), 'traceback': traceback.format_exc()}
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True))
    raise SystemExit(0 if result['status'] == 'passed' else 1)
