#!/usr/bin/env python3
"""
Office XML Instantiator — CASE/UCO JSON-LD generator for Office timestomping detection.

Accepts three input modes:

  1. Merged JSON (Autopsy path — produced by ArtifactExporter._export_zip_xml):
       python3 office_xml_instantiator.py office_xml_merged.json output.jsonld

  2. Raw .docx file (manual investigator path):
       python3 office_xml_instantiator.py report.docx output.jsonld

  3. Unzipped Office package directory (manual investigator path):
       python3 office_xml_instantiator.py report_docx_xml/ output.jsonld

In both modes the output JSON-LD contains only:
  - ioi-ext:OfficeXMLFacet  (xml_creator, xml_created, xml_modified, xml_last_modified_by)
  - observable:FileFacet     (fileName/filePath join keys for IOI-012 SPARQL rule)

Filesystem timestamps ($SI) are NOT included here — they come from the MFT graph
produced by mft_instantiator.py. IOI-012 joins both graphs on fileName.

CLI (standard 2-argument contract — callable by MapperRunner):
  python3 office_xml_instantiator.py <input> <output.jsonld>
"""

import argparse
import copy
import json
import uuid
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_TIMESTAMP = '1970-01-01T00:00:00Z'
OFFICE_EXTENSIONS = ('.docx', '.xlsx', '.pptx', '.docm', '.xlsm', '.pptm')


# ── Helpers ─────────────────────────────────────────────────────────────────

def generate_uuid():
    return str(uuid.uuid4())


def sanitize_timestamp(value, default=DEFAULT_TIMESTAMP):
    """Normalise ISO 8601 timestamp or return default."""
    if not value or str(value).strip() == '':
        return default
    v = str(value).strip()
    if 'T' in v:
        return v if v.endswith('Z') else v + 'Z'
    return default


def sanitize_int(value, default='0'):
    """Safe integer string conversion."""
    if value is None or str(value).strip() == '':
        return default
    try:
        return str(int(float(str(value))))
    except (ValueError, TypeError):
        return default


def _directory_size(path):
    """Return cumulative size in bytes for all files under a directory."""
    total = 0
    for child in path.rglob('*'):
        if child.is_file():
            total += child.stat().st_size
    return total


def _infer_filename_from_unzipped_dir(path):
    """Infer the original Office filename from an extracted package directory name."""
    name = path.name
    if name.endswith('(xml)'):
        return name[:-5]

    suffix_map = {
        '_docx_xml': '.docx',
        '_xlsx_xml': '.xlsx',
        '_pptx_xml': '.pptx',
        '_docm_xml': '.docm',
        '_xlsm_xml': '.xlsm',
        '_pptm_xml': '.pptm',
    }
    lowered = name.lower()
    for suffix, ext in suffix_map.items():
        if lowered.endswith(suffix):
            return name[:-len(suffix)] + ext
    return None


def _default_output_filepath(path, inferred_filename=None):
    """Default to the evidence-like file path without requiring manual input."""
    if inferred_filename:
        return str((path.parent / inferred_filename).resolve())
    return str(path.resolve())


def _resolve_sibling_office_file(path, inferred_filename):
    """Reuse sibling Office file metadata when the extracted folder sits next to the source file."""
    if not inferred_filename:
        return None
    candidate = path.parent / inferred_filename
    if candidate.exists() and candidate.is_file():
        return candidate
    return None


# ── Input loaders ────────────────────────────────────────────────────────────

def load_from_merged_json(input_path):
    """
    Autopsy path — read pre-merged records from ArtifactExporter.
    Each record already has xml_* fields populated.
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        records = json.load(f)
    print('Loaded %d record(s) from merged JSON: %s' % (len(records), input_path))
    return records


def _parse_core_xml(xml_bytes):
    """Parse docProps/core.xml bytes and return xml_* metadata dict."""
    try:
        root = ET.fromstring(xml_bytes)
        ns = {
            'cp':      'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
            'dc':      'http://purl.org/dc/elements/1.1/',
            'dcterms': 'http://purl.org/dc/terms/',
        }
        def _text(tag):
            el = root.find(tag, ns)
            return el.text.strip() if el is not None and el.text else ''
        return {
            'xml_creator':          _text('dc:creator'),
            'xml_last_modified_by': _text('cp:lastModifiedBy'),
            'xml_created':          _text('dcterms:created'),
            'xml_modified':         _text('dcterms:modified'),
        }
    except Exception as e:
        print('  Warning: core.xml parse failed: %s' % e)
        return {'xml_creator': '', 'xml_last_modified_by': '', 'xml_created': '', 'xml_modified': ''}


def extract_from_docx(input_path, override_filepath=None):
    """
    Manual investigator path — extract XML metadata directly from a .docx file.
    fs_* timestamps are intentionally omitted (come from mft_instantiator separately).

    override_filepath: if provided, used as observable:filePath (must match MFT graph path
                       for IOI-012 join to work). If None, user is prompted interactively.
    """
    p = Path(input_path)

    if override_filepath:
        filepath = override_filepath
    else:
        print('  [Manual mode] Enter the original file path as it appears in the MFT')
        print('  (e.g. /Users/ktams/Desktop/Confidential/password.docx)')
        print('  This must match the MFT graph filePath for IOI-012 to detect a hit.')
        filepath = input('  filePath > ').strip() or str(p.resolve())

    record = {
        'filename':  p.name,
        'filepath':  filepath,
        'extension': p.suffix.lstrip('.'),
        'size':      p.stat().st_size,
    }
    try:
        with zipfile.ZipFile(input_path, 'r') as zf:
            if 'docProps/core.xml' in zf.namelist():
                xml_bytes = zf.read('docProps/core.xml')
                record.update(_parse_core_xml(xml_bytes))
                print('  core.xml extracted and parsed from %s' % p.name)
            else:
                print('  Warning: docProps/core.xml not found in %s' % p.name)
                record.update({'xml_creator': '', 'xml_last_modified_by': '', 'xml_created': '', 'xml_modified': ''})
    except zipfile.BadZipFile:
        print('  Error: %s is not a valid ZIP/Office file' % p.name)
        record.update({'xml_creator': '', 'xml_last_modified_by': '', 'xml_created': '', 'xml_modified': ''})
    return [record]


def extract_from_unzipped_dir(input_path, override_filepath=None):
    """
    Manual investigator path — extract XML metadata from an unzipped Office package folder.

    Supports directories such as:
      - password.docx(xml)/
      - af012_password_docx_xml/

    If a sibling Office file is present next to the extracted directory, reuse its
    filename, resolved path, and file size so the emitted JSON-LD matches the raw
    .docx branch as closely as possible without changing current behavior.
    """
    p = Path(input_path)
    core_xml_path = p / 'docProps' / 'core.xml'
    inferred_filename = _infer_filename_from_unzipped_dir(p)
    sibling_office_file = _resolve_sibling_office_file(p, inferred_filename)

    if sibling_office_file is not None:
        filename = sibling_office_file.name
        extension = sibling_office_file.suffix.lstrip('.')
        size = sibling_office_file.stat().st_size
        default_filepath = str(sibling_office_file.resolve())
    else:
        filename = inferred_filename or p.name
        extension = Path(filename).suffix.lstrip('.')
        size = _directory_size(p)
        default_filepath = _default_output_filepath(p, inferred_filename=filename if extension else None)

    record = {
        'filename': filename,
        'filepath': override_filepath or default_filepath,
        'extension': extension,
        'size': size,
    }

    if core_xml_path.exists():
        xml_bytes = core_xml_path.read_bytes()
        record.update(_parse_core_xml(xml_bytes))
        print('  core.xml extracted and parsed from %s' % core_xml_path)
    else:
        print('  Warning: docProps/core.xml not found in %s' % p)
        record.update({'xml_creator': '', 'xml_last_modified_by': '', 'xml_created': '', 'xml_modified': ''})

    return [record]


# ── Template loader ──────────────────────────────────────────────────────────

def load_template_snippets():
    base = Path(__file__).parent / 'templates' / 'office_xml'
    with open(base / 'office_xml_template-entry.json') as f:
        entry_snippet = json.load(f)
    return entry_snippet


def _replace_placeholders(obj, replacements):
    """Recursively replace {PLACEHOLDER} strings in a dict/list structure."""
    if isinstance(obj, dict):
        return {k: _replace_placeholders(v, replacements) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_replace_placeholders(i, replacements) for i in obj]
    elif isinstance(obj, str):
        for placeholder, value in replacements.items():
            obj = obj.replace(placeholder, value)
        return obj
    return obj


# ── Core JSON-LD builder ─────────────────────────────────────────────────────

def build_graph(records):
    """
    Build the JSON-LD @graph from records using the entry template.

    Each record produces:
      - 1 observable:File entry node (from template)
          └── observable:FileFacet    (fileName/filePath — join keys for IOI-012)
          └── ioi-ext:OfficeXMLFacet  (embedded XML metadata — detection evidence)
      - 1 uco-action:InvestigativeAction linking source → entry

    Plus 1 shared source file node.
    """
    entry_snippet = load_template_snippets()
    graph = []

    source_uuid = generate_uuid()
    source_id   = 'kb:office_xml-source--%s' % source_uuid
    graph.append({
        '@id':   source_id,
        '@type': 'observable:File',
        'core:hasFacet': [{
            '@id':                   'kb:office_xml-source-facet--%s' % source_uuid,
            '@type':                 'observable:FileFacet',
            'observable:fileName':   'office_xml_instantiator_output',
        }]
    })

    actions = []

    for rec in records:
        entry_uuid = generate_uuid()
        entry_id   = 'kb:office_xml--%s' % entry_uuid

        fname = rec.get('filename', '')
        fpath = rec.get('filepath', '')
        fsize = sanitize_int(rec.get('size', 0))
        fext  = rec.get('extension', '')

        xml_creator     = rec.get('xml_creator', '') or ''
        xml_last_mod_by = rec.get('xml_last_modified_by', '') or ''
        xml_created     = sanitize_timestamp(rec.get('xml_created'))
        xml_modified    = sanitize_timestamp(rec.get('xml_modified'))

        replacements = {
            '{ENTRY_UUID}':       entry_uuid,
            '{FILE_NAME}':        fname,
            '{FILE_PATH}':        fpath,
            '{EXTENSION}':        fext,
            '{FILE_SIZE}':        fsize,
            '{DC_CREATOR}':       xml_creator,
            '{LAST_MODIFIED_BY}': xml_last_mod_by,
            '{DCTERMS_CREATED}':  xml_created,
            '{DCTERMS_MODIFIED}': xml_modified,
            # MFT timestamps not available in office graph — default
            '{MFT_SI_CREATED}':        DEFAULT_TIMESTAMP,
            '{MFT_SI_MODIFIED}':       DEFAULT_TIMESTAMP,
            '{MFT_SI_ACCESSED}':       DEFAULT_TIMESTAMP,
            '{MFT_SI_RECORD_CHANGE}':  DEFAULT_TIMESTAMP,
            '{MFT_ENTRY_NUMBER}':      '0',
            '{MFT_PARENT_ENTRY_NUMBER}': '0',
            '{MFT_FN_CREATED}':        DEFAULT_TIMESTAMP,
            '{MFT_FN_MODIFIED}':       DEFAULT_TIMESTAMP,
            '{MFT_FN_ACCESSED}':       DEFAULT_TIMESTAMP,
            '{MFT_FN_RECORD_CHANGE}':  DEFAULT_TIMESTAMP,
        }

        entry_node = copy.deepcopy(entry_snippet)[0]
        entry_node = _replace_placeholders(entry_node, replacements)
        entry_node['@id'] = entry_id
        graph.append(entry_node)

        action_uuid = generate_uuid()
        actions.append({
            '@id':   'kb:office_xml-action--%s' % action_uuid,
            '@type': 'uco-action:InvestigativeAction',
            'core:source': {'@id': source_id},
            'core:target': {'@id': entry_id},
        })

    graph.extend(actions)
    return graph


# ── Entry point ──────────────────────────────────────────────────────────────

def fill_template_from_data(input_path, output_path, override_filepath=None):
    """
    Dispatch to correct loader based on input file type, then build JSON-LD.
    """
    p = Path(input_path)
    ext = p.suffix.lower()

    if p.is_dir():
        records = extract_from_unzipped_dir(input_path, override_filepath=override_filepath)
    elif ext == '.json':
        records = load_from_merged_json(input_path)
    elif ext in OFFICE_EXTENSIONS:
        records = extract_from_docx(input_path, override_filepath=override_filepath)
    else:
        # Fallback: try JSON first, then Office ZIP/manual path
        try:
            records = load_from_merged_json(input_path)
        except (json.JSONDecodeError, ValueError):
            records = extract_from_docx(input_path, override_filepath=override_filepath)

    print('Processing %d Office document(s)' % len(records))

    output = {
        '@context': {
            'kb':         'https://ioi-framework.github.io/kb/',
            'ioi-ext':    'https://ioi-framework.github.io/ns/ioi-ext/',
            'core':       'https://ontology.unifiedcyberontology.org/uco/core/',
            'observable': 'https://ontology.unifiedcyberontology.org/uco/observable/',
            'uco-action': 'https://ontology.unifiedcyberontology.org/uco/action/',
            'xsd':        'http://www.w3.org/2001/XMLSchema#'
        },
        '@graph': build_graph(records)
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    entry_count  = sum(1 for n in output['@graph'] if 'OfficeXMLFacet' in json.dumps(n))
    action_count = sum(1 for n in output['@graph'] if n.get('@type') == 'uco-action:InvestigativeAction')

    print('Generated: %s' % output_path)
    print('  Entry nodes  : %d' % entry_count)
    print('  Action nodes : %d' % action_count)
    print('  Total nodes  : %d' % len(output['@graph']))


def main():
    parser = argparse.ArgumentParser(
        description='Generate CASE/UCO JSON-LD for Office XML timestomping detection.\n'
                    'Input can be a merged JSON (Autopsy path), an Office document, or an extracted Office package directory.')
    parser.add_argument('input',  help='Merged JSON from ArtifactExporter, path to an Office file, or path to an extracted Office package directory')
    parser.add_argument('output', help='Output JSON-LD file')
    parser.add_argument('--filepath', default=None,
                        help='(Manual file/folder mode only) Original file path as it appears in the MFT '
                             '(e.g. /Users/ktams/Desktop/Confidential/password.docx). '
                             'Must match MFT graph filePath for IOI-012 join to work. '
                             'If omitted, .docx input prompts interactively and extracted folders infer a default path automatically.')
    args = parser.parse_args()
    fill_template_from_data(args.input, args.output, override_filepath=args.filepath)


if __name__ == '__main__':
    main()
