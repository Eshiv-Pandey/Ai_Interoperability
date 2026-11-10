"""Create the versioned primary-checked bibliography without editing prior drafts."""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = 'docs/research/source-evidence/final-literature-review-v1-20261110'
SOURCE = ROOT / BASE


def record(path):
    data = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


def evidence(name, location, format='Formatted web-tool excerpt, not original HTTP response bytes'):
    return {'path': BASE + '/' + name, 'location': location, 'format': format}


def write(path, data):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(data)


frozen_names = ['paper/working-draft-v4.md', 'paper/claim-ledger-v4.json',
                'paper/draft-status-v4.json', 'paper/audit_draft_v4.py',
                'docs/research/paper-artifact-guide-v4.md']
frozen = [record(ROOT / name) for name in frozen_names]
prior = json.loads((ROOT / 'paper/references-v2.json').read_bytes())
entries = copy.deepcopy(prior['entries'])
locations = {
    1: ('01-modern-primary.json', 'AgentThread primary title/authors/version/history; turn205292view0'),
    2: ('01-modern-primary.json', 'CONTINUITY primary title/authors/version/history; turn205292view1'),
    3: ('01-modern-primary.json', 'PC2 title/authors/version/history and current page-displayed arXiv DOI; turn205292view2'),
    4: ('01-modern-primary.json', 'BRIDGE primary title/ordered authors/version/history; turn205292view3'),
    5: ('05-precise-method-primary.json', 'ACL authors93 and109-119; volume65, date67-69, pages83, DOI89; turn969776view0'),
    6: ('01-modern-primary.json', 'Facts Without Rules primary title/authors/version/history; turn205292view5'),
    7: ('02-classical-primary.json', 'EWD472 title, publication identity15 and author21; turn623426view0'),
    8: ('02-classical-primary.json', 'Quotient author-hosted PDF title/printed authors0-1 and IEEE2018 footer; turn623426view1'),
    9: ('02-classical-primary.json', 'IR-MIA explicit title/authors and v7 history; turn623426view2'),
    10: ('02-classical-primary.json', 'Pacti explicit title/authors and v1 history; turn623426view3'),
    11: ('05-precise-method-primary.json', 'NeurIPS official title0, authors2 and proceedings volume/year4; turn969776view1'),
    12: ('02-classical-primary.json', 'PMLR official title/authors/volume/pages/year and exported BibTeX; turn623426view5'),
    13: ('03-symbolic-primary.json', 'Dagstuhl official authors/title95-119, DOI and exported proceedings citation157 onward; turn340010view0'),
    14: ('software-pin-review/receipt.json', 'AmirK-S repository, exact pin, UTC author/committer date, account and decoded LICENSE blob checks', 'Retained gh API response-body bytes and independently decoded pinned LICENSE'),
    15: ('software-pin-review/receipt.json', 'mgcrea repository, exact pin, UTC author/committer date, account and decoded LICENSE blob checks', 'Retained gh API response-body bytes and independently decoded pinned LICENSE'),
    16: ('03-symbolic-primary.json', 'YAPA explicit three-author list, title and v1 history; turn340010view3'),
    17: ('06-closest-bodies-and-publication.json', 'DEEPSEC primary author bibliography title0, authors/venue/year2 and DOI3,37-47; turn795301view0'),
    18: ('03-symbolic-primary.json', 'POR explicit title/authors and v2 history; turn340010view5'),
}
for entry in entries:
    entry['evidence'].append(evidence(*locations[entry['number']]))
    entry['primary_metadata_review'] = {
        'date_utc': '2026-11-10', 'status': 'verified_against_primary_source',
        'reviewer': 'Codex AI', 'human_review': False,
        'prior_system_results_reproduced': False,
    }

entries[2]['fields']['doi'] = '10.48550/arXiv.2610.28484'
entries[2]['limits'] = ['The refreshed primary page displays an arXiv DOI. This is not a journal publication or independently checked DOI-resolution claim.']
entries[4]['manuscript_urls'] = ['https://aclanthology.org/2026.acl-long.1294.pdf']
entries[4]['evidence'].append(evidence('07-precise-version-and-memo.json',
    'ACL official PDF first page0-4 confirms author order and printed proceedings/page identity; turn464144view3'))
entries[4]['limits'] = ['Current refresh inspects official landing metadata and PDF first-page identity; empirical claims are not reproduced.']
entries[10]['limits'] = ['Official proceedings page verifies title/authors/volume/year. Unverified pages/editors/DOI remain omitted; earlier BibTeX-export error retained.']
for number, date in [(14, '6 September 2026'), (15, '9 October 2026')]:
    entry = entries[number - 1]
    license_name = 'Apache-2.0' if number == 14 else 'MIT'
    entry['fields']['note'] = license_name + '; exact commit dated ' + date + ', verified against primary GitHub metadata and retained source lock'
    entry['limits'] = ['Attribution identifies the GitHub repository account, not an independently verified legal personal identity or conceptual inventor.']

new = [
    {
        'number': 19, 'key': 'clarke2000cegar', 'type': 'inproceedings',
        'fields': {
            'title': 'Counterexample-Guided Abstraction Refinement',
            'author': 'Clarke, Edmund and Grumberg, Orna and Jha, Somesh and Lu, Yuan and Veith, Helmut',
            'booktitle': 'Computer Aided Verification (CAV 2000)',
            'series': 'Lecture Notes in Computer Science', 'volume': '1855',
            'year': '2000', 'pages': '154--169', 'publisher': 'Springer, Berlin, Heidelberg',
            'doi': '10.1007/10722167_15',
            'url': 'https://link.springer.com/chapter/10.1007/10722167_15',
        },
        'manuscript_urls': ['https://web.stanford.edu/class/cs357/cegar.pdf'],
        'evidence': [evidence('06-closest-bodies-and-publication.json',
            'Springer title11, authors24-29, CAV2000/volume22,32, pages15 and PDF mechanism0-67; turn795301view1/view2'),
            evidence('08-csp-publication-final.json', 'Springer cite-this-paper154, DOI159 and year149; turn214303view1'),
            evidence('raw-primary-v1/cegar.pdf', 'Inspected original paper sections1, abstract and exact-prefix refinement discussion', 'Retained primary author/institution-hosted PDF bytes')],
        'limits': ['CMU repository deposit is dated2011 and links more than one version. Bibliographic identity uses the primary CAV2000 publisher record and inspected original paper; repository deposit date is not publication year.'],
    },
    {
        'number': 20, 'key': 'mackworth1977consistency', 'type': 'article',
        'fields': {
            'title': 'Consistency in Networks of Relations', 'author': 'Mackworth, Alan',
            'journal': 'Artificial Intelligence', 'volume': '8', 'number': '1',
            'year': '1977', 'pages': '99--118',
            'url': 'https://www.cs.ubc.ca/~mack/Publications/b2hd-AI77.html',
        },
        'manuscript_urls': ['https://www.cs.ubc.ca/~mack/Publications/AI77.pdf'],
        'evidence': [evidence('05-precise-method-primary.json', 'Author primary title3, publication4 and exported BibTeX12-19; turn969776view3')],
        'limits': ['Author publication metadata and BibTeX verified. Full-body fetches from the author PDF and institutional copy failed and are retained; this refresh does not claim a fresh full-body AC-3 review. DOI omitted because publisher verification failed.'],
    },
    {
        'number': 21, 'key': 'michie1968memo', 'type': 'article',
        'fields': {
            'title': "``Memo'' Functions and Machine Learning", 'author': 'Michie, Donald',
            'journal': 'Nature', 'volume': '218', 'number': '5136', 'year': '1968',
            'pages': '19--22', 'doi': '10.1038/218019a0',
            'url': 'https://www.nature.com/articles/218019a0',
        },
        'manuscript_urls': ['https://www.cs.utexas.edu/~hunt/research/hash-cons/hash-cons-papers/michie-memo-nature-1968.pdf'],
        'evidence': [evidence('raw-primary-v1/memo-publisher.html', 'citation_title/author/journal/volume/issue/date/firstpage/lastpage/doi meta tags', 'Retained primary publisher HTTP body bytes'),
            evidence('primary-inspection-v1/memo-publisher-metadata.json', 'HTMLParser-extracted citation meta tags bound to retained publisher body', 'Derived primary metadata extraction'),
            evidence('primary-inspection-v1/memo-page-1-image-1.png', 'Printed page19 title/author and definition of evaluation procedure plus stored results', 'Original PDF page image extracted by pypdf and encoded as PNG'),
            evidence('primary-inspection-v1/memo-page-2-image-1.png', 'Printed page20 lookup/reuse example', 'Original PDF page image extracted by pypdf and encoded as PNG')],
        'limits': ['Scanned paper body was inspected through original page images; extracted text only exposes the copyright line. Distinct same-title page306 correction10.1038/218306c0 is not substituted.'],
    },
    {
        'number': 22, 'key': 'biere1999bmc', 'type': 'inproceedings',
        'fields': {
            'title': 'Symbolic Model Checking without {BDDs}',
            'author': 'Biere, Armin and Cimatti, Alessandro and Clarke, Edmund and Zhu, Yunshan',
            'booktitle': 'Tools and Algorithms for the Construction and Analysis of Systems (TACAS 1999)',
            'series': 'Lecture Notes in Computer Science', 'volume': '1579', 'year': '1999',
            'pages': '193--207', 'publisher': 'Springer, Berlin, Heidelberg',
            'doi': '10.1007/3-540-49059-0_14',
            'url': 'https://link.springer.com/chapter/10.1007/3-540-49059-0_14',
        },
        'manuscript_urls': ['https://fmv.jku.at/papers/BiereCimattiClarkeZhu-TACAS99.pdf'],
        'evidence': [evidence('07-precise-version-and-memo.json', 'Publisher title11/authors25-29/pages16/volume31; primary PDF0-16 and bounded semantics180 onward; turn464144view1/view2/view6'),
            evidence('08-csp-publication-final.json', 'Publisher citation189, DOI194, year184 and publication196; turn214303view2'),
            evidence('raw-primary-v1/bmc.pdf', 'Original paper sections3-5 and bounded semantics/completeness conditions', 'Retained primary author-hosted PDF bytes')],
        'limits': ['This is the four-author TACAS1999 version. The different five-author DAC1999 paper and later bounded-model-checking titles are not substituted.'],
    },
]
for entry in new:
    entry['primary_metadata_review'] = {'date_utc': '2026-11-10',
        'status': 'verified_against_primary_source', 'reviewer': 'Codex AI',
        'human_review': False, 'prior_system_results_reproduced': False}
entries.extend(new)

data = {
    'schema_version': 'working-paper-bibliography/3', 'date_utc': '2026-11-10',
    'scope': 'Twenty literature references and two exact pinned software sources; 18 retained identities plus 4 primary closest-method additions.',
    'prior_version': 'paper/references-v2.json', 'compatible_existing_numbering': 'Entries 1-18 retain paper v4 numbering; 19-22 are available for a subsequent manuscript version.',
    'frozen_draft': 'paper/working-draft-v4.md', 'frozen_draft_edited': False,
    'primary_metadata_checked_entries': 22, 'human_metadata_review_completed': False,
    'prior_system_results_reproduced': False,
    'complete_final_publication_bibliography': False,
    'literature_assessment': 'docs/research/final-literature-review-v1.md',
    'entries': entries,
}
write(ROOT / 'paper/references-v3.json', json.dumps(data, ensure_ascii=False, indent=2) + '\n')
bib = '% Primary-checked bibliography v3. Evidence and limits: references-v3.json.\n\n'
for entry in entries:
    bib += '@' + entry['type'] + '{' + entry['key'] + ',\n'
    bib += ',\n'.join('  ' + key + ' = {' + value + '}' for key, value in entry['fields'].items())
    bib += '\n}\n\n'
write(ROOT / 'paper/references-v3.bib', bib)

def plain(value):
    value = value.replace('``', '"').replace("''", '"')
    value = value.replace("\\'{I}", 'Í').replace("\\'{I}\\~{n}igo", 'Íñigo')
    value = value.replace('Í\\~{n}igo', 'Íñigo')
    return value.replace('{', '').replace('}', '')

def authors(value):
    result = []
    for name in value.split(' and '):
        if ', ' in name:
            surname, given = name.split(', ', 1)
            result.append(plain(given + ' ' + surname))
        else:
            result.append(plain(name))
    return ', '.join(result)

md = '# Bibliography v3\n\n'
md += ('Twenty literature references and two pinned software sources, checked against primary metadata on 10 November 2026. '
       'The existing 18 citation numbers remain stable. Four closest-method references are added for a later draft; paper v4 is unchanged.\n\n'
       'This is an AI metadata/source review. Human publication-metadata review and prior-system result reproduction remain incomplete. '
       'See [source records and limits](references-v3.json), [the literature assessment](../docs/research/final-literature-review-v1.md) '
       'and [the retrieval manifest](../' + BASE + '/manifest.json).\n\n<!-- reference-entries -->\n\n')
for entry in entries:
    fields = entry['fields']
    parts = [fields[key] for key in ('booktitle', 'journal', 'series') if key in fields]
    parts += [('vol. ' + fields['volume'])] if 'volume' in fields else []
    parts += [('no. ' + fields['number'])] if 'number' in fields else []
    parts += [('pp. ' + fields['pages'].replace('--', '-'))] if 'pages' in fields else []
    parts.append(fields['year'])
    if 'eprint' in fields:
        parts.append('arXiv:' + fields['eprint'])
    if 'doi' in fields:
        parts.append('DOI ' + fields['doi'])
    if 'howpublished' in fields:
        parts.append(fields['howpublished'])
    if 'note' in fields:
        parts.append(fields['note'])
    md += (str(entry['number']) + '. ' + authors(fields['author']) + '. [' + plain(fields['title']) + ']('
           + fields['url'] + '). ' + '; '.join(plain(p) for p in parts) + '.\n\n')
write(ROOT / 'paper/references-v3.md', md)

assert frozen == [record(ROOT / name) for name in frozen_names], 'Frozen paper v4 changed during bibliography generation'
manifest = {
    'schema_version': 'final-literature-source-manifest/1',
    'generated_at_utc': datetime.now(timezone.utc).isoformat(),
    'sources': [record(path) for path in sorted(SOURCE.rglob('*')) if path.is_file()],
    'frozen_paper_v4': frozen,
    'bibliography_artifacts': [record(ROOT / name) for name in
        ('paper/references-v3.json', 'paper/references-v3.bib', 'paper/references-v3.md', 'paper/build_references_v3.py')],
    'primary_metadata_checked_entries': 22, 'existing_entries': 18, 'new_closest_method_entries': 4,
    'human_review': False, 'prior_system_results_reproduced': False,
    'retention_note': 'Search/open receipts are formatted tool output. raw-primary-v1 contains HTTP body bytes. software-pin-review contains gh API output bodies plus decoded LICENSE bytes. Each is labelled separately; failures are retained.',
}
write(SOURCE / 'manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': 'created', 'entries': len(entries), 'source_files': len(manifest['sources']),
                  'paper_v4_preserved': True}))
