#!/usr/bin/env python3
"""
Office XML Instantiator — CASE/UCO JSON-LD generator for Office timestomping detection.

Reads the merged JSON produced by ArtifactExporter (zip_xml strategy) which contains:
  - Filesystem timestamps ($SI from Autopsy AbstractFile) — what the attacker modified
  - Embedded docProps/core.xml metadata           — what the attacker forgot to change

IOI-012 SPARQL rule fires when these two sets of timestamps contradict each other,
proving that the filesystem timestamps were tampered (timestomped).

CLI (standard 2-argument contract — callable by MapperRunner):
  python3 office_xml_instantiator.py <merged.json> <output.jsonld>
"""

import argparse
import copy
import json
import uuid
from pathlib import Path

DEFAULT_TIMESTAMP = '1970-01-01T00:00:00Z'


# ── Helpers ────────────────────────────────────────────────────────────────

def generate_uuid():
    return str(uuid.uuid4())


def sanitize_timestamp(value, default=DEFAULT_TIMESTAMP):
    """Normalise ISO 8601 timestamp or return default."""
    if not value or str(value).strip() == '':
        return default
    v = str(value).strip()
    # Already ISO 8601 (from AbstractFile epoch conversion or core.xml)
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


# ── Core logic ─────────────────────────────────────────────────────────────

def build_graph(records):
    """
    Build the JSON-LD @graph from merged records.

    Each record produces:
      - 1 observable:File entry node
          └── observable:FileFacet     (filesystem $SI timestamps)
          └── ioi-ext:OfficeXMLFacet  (embedded XML metadata)
      - 1 uco-action:InvestigativeAction linking source → entry

    Plus 1 shared source file node for the dataset.
    """
    graph = []

    # Source node — represents the dataset / analysis run
    source_uuid = generate_uuid()
    source_id   = 'kb:office_xml-source--%s' % source_uuid
    source_node = {
        '@id':   source_id,
        '@type': 'observable:File',
        'core:hasFacet': [
            {
                '@id':   'kb:office_xml-source-facet--%s' % source_uuid,
                '@type': 'observable:FileFacet',
                'observable:fileName': 'office_xml_merged.json',
            }
        ]
    }
    graph.append(source_node)

    actions = []

    for rec in records:
        entry_uuid = generate_uuid()
        entry_id   = 'kb:office_xml--%s' % entry_uuid

        fname    = rec.get('filename', '')
        fpath    = rec.get('filepath', '')
        fsize    = sanitize_int(rec.get('size', 0))
        fext     = rec.get('extension', '')

        # Filesystem timestamps ($SI — the tampered ones)
        fs_created  = sanitize_timestamp(rec.get('fs_created'))
        fs_modified = sanitize_timestamp(rec.get('fs_modified'))
        fs_accessed = sanitize_timestamp(rec.get('fs_accessed'))
        fs_changed  = sanitize_timestamp(rec.get('fs_changed'))

        # Embedded XML metadata (the authentic ones the attacker forgot)
        xml_creator     = rec.get('xml_creator', '')
        xml_last_mod_by = rec.get('xml_last_modified_by', '')
        xml_created     = sanitize_timestamp(rec.get('xml_created'))
        xml_modified    = sanitize_timestamp(rec.get('xml_modified'))

        entry_node = {
            '@id':   entry_id,
            '@type': 'observable:File',
            'core:hasFacet': [
                {
                    '@id':   'kb:office_xml-file-facet--%s' % entry_uuid,
                    '@type': 'observable:FileFacet',
                    'observable:fileName':  fname,
                    'observable:filePath':  fpath,
                    'observable:extension': fext,
                    'observable:sizeInBytes': {
                        '@type':  'xsd:long',
                        '@value': fsize
                    },
                    'observable:observableCreatedTime': {
                        '@type':  'xsd:dateTime',
                        '@value': fs_created
                    },
                    'observable:modifiedTime': {
                        '@type':  'xsd:dateTime',
                        '@value': fs_modified
                    },
                    'observable:accessedTime': {
                        '@type':  'xsd:dateTime',
                        '@value': fs_accessed
                    },
                    'observable:metadataChangeTime': {
                        '@type':  'xsd:dateTime',
                        '@value': fs_changed
                    },
                },
                {
                    '@id':   'kb:office_xml-ext-facet--%s' % entry_uuid,
                    '@type': 'ioi-ext:OfficeXMLFacet',
                    # Predicate names match IOI-012 rule exactly:
                    #   ioi-ext:created      ← rule queries this
                    #   ioi-ext:modified     ← informational
                    #   ioi-ext:creator      ← informational
                    #   ioi-ext:lastModifiedBy ← informational
                    'ioi-ext:creator':        xml_creator,
                    'ioi-ext:lastModifiedBy': xml_last_mod_by,
                    'ioi-ext:created': {
                        '@type':  'xsd:dateTime',
                        '@value': xml_created
                    },
                    'ioi-ext:modified': {
                        '@type':  'xsd:dateTime',
                        '@value': xml_modified
                    },
                }
            ]
        }
        graph.append(entry_node)

        # InvestigativeAction: source dataset → this entry
        action_uuid = generate_uuid()
        actions.append({
            '@id':   'kb:office_xml-action--%s' % action_uuid,
            '@type': 'uco-action:InvestigativeAction',
            'core:source': {'@id': source_id},
            'core:target': {'@id': entry_id},
        })

    graph.extend(actions)
    return graph


# ── Entry point ────────────────────────────────────────────────────────────

def fill_template_from_data(input_path, output_path):
    """
    Read merged JSON from ArtifactExporter, produce CASE/UCO JSON-LD.

    Args:
        input_path:  Path to merged JSON (list of dicts with fs_ + xml_ fields)
        output_path: Output .jsonld file path
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        records = json.load(f)

    print('Processing %d Office document(s) from %s' % (len(records), input_path))

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
    print('  Source nodes : 1')
    print('  Entry nodes  : %d' % entry_count)
    print('  Action nodes : %d' % action_count)
    print('  Total nodes  : %d' % len(output['@graph']))


def main():
    parser = argparse.ArgumentParser(
        description='Generate CASE/UCO JSON-LD for Office XML timestomping detection')
    parser.add_argument('input',  help='Merged JSON from ArtifactExporter')
    parser.add_argument('output', help='Output JSON-LD file')
    args = parser.parse_args()
    fill_template_from_data(args.input, args.output)


if __name__ == '__main__':
    main()
