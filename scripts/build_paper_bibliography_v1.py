"""Render the retained bibliography metadata; refuse to replace outputs."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'paper/references-v1.json'
OUTPUTS = [ROOT / 'paper/references-v1.bib', ROOT / 'paper/references-v1.md']


def plain(value):
    for encoded, decoded in [("{\\'{I}}", 'Í'), ("\\'{I}", 'Í'),
                             ('\\~{n}', 'ñ'), ('{\\\"u}', 'ü')]:
        value = value.replace(encoded, decoded)
    return value.replace('{', '').replace('}', '')


def authors(value):
    result = []
    for author in value.split(' and '):
        name = plain(author)
        if ', ' in name:
            family, given = name.split(', ', 1)
            name = given + ' ' + family
        result.append(name)
    return ', '.join(result)


if __name__ == '__main__':
    if any(path.exists() for path in OUTPUTS):
        raise SystemExit('Refusing to replace a retained bibliography output.')
    data = json.loads(SOURCE.read_text(encoding='utf-8'))
    bib = ['% Bibliography for the incomplete internal working draft, 25 October 2026.',
           '% Metadata and evidence limits are in references-v1.json.',
           '% Versioned preprints are not relabeled as reviewed journal publications.', '']
    md = ['# Bibliography v1', '',
          'Thirteen literature references and two pinned software sources for the current',
          'incomplete working draft. Primary metadata provenance and unresolved fields are',
          'recorded in [references-v1.json](references-v1.json). This is a targeted metadata',
          'audit, not a final literature search, human review or reproduction of prior results.', '',
          '<!-- reference-entries -->', '']
    for item in data['entries']:
        fields = item['fields']
        bib.append('@' + item['type'] + '{' + item['key'] + ',')
        bib.extend('  ' + key + ' = {' + value + '},' for key, value in fields.items())
        bib.extend(['}', ''])
        details = []
        venue = fields.get('booktitle', fields.get('journal', fields.get('howpublished', '')))
        if venue:
            details.append(plain(venue))
        if fields.get('series'):
            details.append(plain(fields['series']))
        if fields.get('volume'):
            details.append('vol. ' + fields['volume'])
        if fields.get('number'):
            details.append('no. ' + fields['number'])
        if fields.get('pages'):
            details.append('pp. ' + fields['pages'].replace('--', '–'))
        details.append(fields['year'])
        if fields.get('eprint'):
            details.append('arXiv:' + fields['eprint'])
        if fields.get('doi'):
            details.append('DOI ' + fields['doi'])
        if fields.get('note'):
            details.append(plain(fields['note']))
        md.extend([str(item['number']) + '. ' + authors(fields['author']) + '. [' +
                   plain(fields['title']) + '](' + fields['url'] + '). ' +
                   '; '.join(details) + '.', ''])
    for path, text in zip(OUTPUTS, ['\n'.join(bib), '\n'.join(md)]):
        with path.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
    print(json.dumps({'references':len(data['entries']),
                      'outputs':[p.relative_to(ROOT).as_posix() for p in OUTPUTS]}))
