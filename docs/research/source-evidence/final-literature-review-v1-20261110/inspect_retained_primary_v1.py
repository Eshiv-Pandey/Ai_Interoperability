"""Extract citation tags and original scanned page images without changing PDFs."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'primary-inspection-v1'
OUT.mkdir(exist_ok=False)

class Metadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.entries = []
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'meta' and values.get('name', '').startswith('citation_'):
            if values['name'] not in ('citation_reference', 'citation_springer_api_url'):
                self.entries.append({'name': values['name'], 'content': values.get('content')})

parser = Metadata()
parser.feed((ROOT / 'raw-primary-v1/memo-publisher.html').read_text(encoding='utf-8'))
(OUT / 'memo-publisher-metadata.json').write_text(json.dumps(parser.entries, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
reader = PdfReader(ROOT / 'raw-primary-v1/memo.pdf')
images = []
for index, page in enumerate(reader.pages):
    for j, item in enumerate(page.images):
        path = OUT / ('memo-page-' + str(index + 1) + '-image-' + str(j + 1) + '.png')
        item.image.save(path)
        images.append({'physical_page': index + 1, 'path': path.relative_to(ROOT).as_posix(),
                       'original_pdf_image_name': item.name,
                       'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
(OUT / 'image-extraction.json').write_text(json.dumps({'source':'raw-primary-v1/memo.pdf',
    'method':'pypdf original page image extraction; PNG encoding by Pillow', 'images':images}, indent=2) + '\n', encoding='utf-8')
print(json.dumps(images))
