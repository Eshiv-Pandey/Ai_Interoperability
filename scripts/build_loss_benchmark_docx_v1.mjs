// Deterministic OOXML report packaging. No external libraries or network access.
import fs from 'node:fs/promises';
import path from 'node:path';

function xml(value) {
  return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&apos;');
}

const textRun = (value, properties = '') => `<w:r>${properties ? `<w:rPr>${properties}</w:rPr>` : ''}<w:t xml:space="preserve">${xml(value)}</w:t></w:r>`;
const paragraph = (value, style = 'Normal', extra = '') => `<w:p><w:pPr><w:pStyle w:val="${style}"/>${extra}</w:pPr>${textRun(value)}</w:p>`;

function table(block) {
  const count = block.headers.length;
  const widths = block.widths ?? (count === 2 ? [2700, 7380] : count === 3 ? [3650, 5430, 1000]
    : count === 6 ? [2800, 1456, 1456, 1456, 1456, 1456]
      : Array.from({length: count}, (_, i) => Math.floor(10080 / count) + (i === count - 1 ? 10080 % count : 0)));
  if (widths.length !== count || widths.some(value => !Number.isSafeInteger(value) || value <= 0)
      || widths.reduce((total, value) => total + value, 0) !== 10080) throw new Error('Invalid table widths');
  const rows = [block.headers, ...block.rows].map((row, index) => {
    if (row.length !== count) throw new Error('Inconsistent table width');
    const cells = row.map((value, column) => `<w:tc><w:tcPr><w:tcW w:w="${widths[column]}" w:type="dxa"/><w:vAlign w:val="center"/>${index === 0 ? '<w:shd w:fill="E9EDF2"/>' : ''}</w:tcPr><w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>${textRun(value, `<w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="19"/>${index === 0 ? '<w:b/>' : ''}`)}</w:p></w:tc>`).join('');
    return `<w:tr><w:trPr><w:cantSplit/>${index === 0 ? '<w:tblHeader/>' : ''}</w:trPr>${cells}</w:tr>`;
  }).join('');
  return `<w:tbl><w:tblPr><w:tblW w:w="10080" w:type="dxa"/><w:tblLayout w:type="fixed"/><w:tblBorders>${['top','left','bottom','right','insideH','insideV'].map(side => `<w:${side} w:val="single" w:sz="4" w:color="CCD3DC"/>`).join('')}</w:tblBorders><w:tblCellMar><w:top w:w="70" w:type="dxa"/><w:bottom w:w="70" w:type="dxa"/><w:left w:w="90" w:type="dxa"/><w:right w:w="90" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>${widths.map(width => `<w:gridCol w:w="${width}"/>`).join('')}</w:tblGrid>${rows}</w:tbl>${paragraph('', 'Normal', '<w:spacing w:after="40"/>')}`;
}

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function zip(parts) {
  const locals = [], central = [];
  let offset = 0;
  for (const [name, value] of Object.entries(parts)) {
    const filename = Buffer.from(name, 'utf8'), data = Buffer.from(value, 'utf8'), crc = crc32(data);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0); local.writeUInt16LE(20, 4); local.writeUInt16LE(0x800, 6);
    local.writeUInt16LE(33, 12); local.writeUInt32LE(crc, 14); local.writeUInt32LE(data.length, 18);
    local.writeUInt32LE(data.length, 22); local.writeUInt16LE(filename.length, 26);
    const entry = Buffer.concat([local, filename, data]); locals.push(entry);
    const directory = Buffer.alloc(46);
    directory.writeUInt32LE(0x02014b50, 0); directory.writeUInt16LE(20, 4); directory.writeUInt16LE(20, 6);
    directory.writeUInt16LE(0x800, 8); directory.writeUInt16LE(33, 14); directory.writeUInt32LE(crc, 16);
    directory.writeUInt32LE(data.length, 20); directory.writeUInt32LE(data.length, 24);
    directory.writeUInt16LE(filename.length, 28); directory.writeUInt32LE(offset, 42);
    central.push(Buffer.concat([directory, filename])); offset += entry.length;
  }
  const directory = Buffer.concat(central), end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0); end.writeUInt16LE(central.length, 8); end.writeUInt16LE(central.length, 10);
  end.writeUInt32LE(directory.length, 12); end.writeUInt32LE(offset, 16);
  return Buffer.concat([...locals, directory, end]);
}

export async function buildReport(inputPath, outputPath) {
  const input = JSON.parse(await fs.readFile(inputPath, 'utf8'));
  if (!/^[\p{L}\p{N} ]+$/u.test(input.title)) throw new Error('Title must contain only letters numbers and spaces');
  let body = paragraph(input.title, 'Title') + paragraph(input.subtitle, 'Subtitle');
  for (const block of input.blocks) {
    if (block.kind === 'paragraph') body += paragraph(block.text);
    else if (block.kind === 'heading') {
      if (!/^[\p{L}\p{N} ]+$/u.test(block.text)) throw new Error('Heading punctuation');
      body += paragraph(block.text, 'Heading1');
    } else if (block.kind === 'table') body += table(block);
    else if (block.kind === 'page_break') body += '<w:p><w:r><w:br w:type="page"/></w:r></w:p>';
    else throw new Error('Unknown report block');
  }
  const declaration = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>';
  const parts = {
    '[Content_Types].xml': declaration + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>',
    '_rels/.rels': declaration + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>',
    'word/document.xml': declaration + `<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>${body}<w:sectPr><w:footerReference w:type="default" r:id="rId2"/><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="900" w:right="1080" w:bottom="900" w:left="1080" w:header="400" w:footer="400"/><w:pgNumType w:start="1"/></w:sectPr></w:body></w:document>`,
    'word/_rels/document.xml.rels': declaration + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/></Relationships>',
    'word/styles.xml': declaration + '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="22"/><w:color w:val="000000"/><w:lang w:val="en-IN"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="100" w:line="252" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:after="140"/></w:pPr><w:rPr><w:b/><w:sz w:val="40"/><w:color w:val="000000"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:after="160"/></w:pPr><w:rPr><w:sz w:val="21"/><w:color w:val="555555"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="160" w:after="80"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="28"/><w:color w:val="000000"/></w:rPr></w:style></w:styles>',
    'word/footer1.xml': declaration + '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:color w:val="666666"/></w:rPr><w:t>Development benchmark   Page </w:t></w:r><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText> PAGE </w:instrText></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>',
    'docProps/core.xml': declaration + `<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>${xml(input.title)}</dc:title><dc:creator>Ai Interoperability project</dc:creator><dc:description>Development benchmark supervisor report with measured results and limitations</dc:description></cp:coreProperties>`,
  };
  await fs.mkdir(path.dirname(outputPath), {recursive: true});
  await fs.writeFile(outputPath, zip(parts), {flag: 'wx'});
  return {output: outputPath, blocks: input.blocks.length, parts: Object.keys(parts).length};
}
