#!/usr/bin/env python3
"""
Fill Office document XML metadata template with MFT + XML metadata.
Combines MFT timestamps with embedded Office document XML metadata for timestomping detection.
"""

import json
import sys
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import uuid


def parse_timestamp(ts_str):
    """Convert MFT timestamp to ISO 8601 format. Returns None if invalid."""
    if not ts_str or ts_str.strip() == '':
        return None

    try:
        # MFT format: 2025-03-04 10:15:43.5470000
        if '.' in ts_str:
            date_part, frac_part = ts_str.rsplit('.', 1)
            frac_part = frac_part[:6]  # Trim to microseconds
            ts_str = f"{date_part}.{frac_part}"

        dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + 'Z'  # Keep 2 decimal places
    except:
        try:
            dt = datetime.strptime(ts_str.strip(), "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except:
            return None


def parse_xml_core(xml_path):
    """Parse docProps/core.xml to extract metadata."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Namespaces
        ns = {
            'cp': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'dcterms': 'http://purl.org/dc/terms/'
        }

        # Extract fields
        creator = root.find('.//dc:creator', ns)
        last_modified_by = root.find('.//cp:lastModifiedBy', ns)
        dcterms_created = root.find('.//dcterms:created', ns)
        dcterms_modified = root.find('.//dcterms:modified', ns)

        return {
            'dc_creator': creator.text if creator is not None else '',
            'last_modified_by': last_modified_by.text if last_modified_by is not None else '',
            'dcterms_created': dcterms_created.text if dcterms_created is not None else '',
            'dcterms_modified': dcterms_modified.text if dcterms_modified is not None else ''
        }
    except Exception as e:
        print(f"Error parsing XML {xml_path}: {e}")
        return None


def fill_template(template_path, entry_template_path, mft_csv_path, xml_folder_path, output_path):
    """Fill template with Office document data."""

    # Load templates
    with open(template_path, 'r') as f:
        template = json.load(f)

    with open(entry_template_path, 'r') as f:
        entry_template = json.load(f)[0]

    # Find Office documents in XML folder
    xml_folder = Path(xml_folder_path)
    office_docs = []

    # For each extracted Office document XML folder
    for doc_folder in xml_folder.iterdir():
        if doc_folder.is_dir():
            core_xml = doc_folder / 'docProps' / 'core.xml'
            if core_xml.exists():
                doc_name = doc_folder.name.replace('(xml)', '').strip()
                xml_data = parse_xml_core(core_xml)
                if xml_data:
                    office_docs.append({
                        'name': doc_name,
                        'xml_data': xml_data
                    })

    print(f"Found {len(office_docs)} Office documents with XML metadata")

    # Load MFT CSV
    mft_records = {}
    with open(mft_csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row.get('FileName', '').strip()
            if filename:
                mft_records[filename] = row

    print(f"Loaded {len(mft_records)} MFT records")

    # Generate entries
    filled_entries = []
    matched = 0

    for doc in office_docs:
        doc_name = doc['name']
        xml_data = doc['xml_data']

        # Find matching MFT record
        if doc_name not in mft_records:
            print(f"No MFT record found for: {doc_name}")
            continue

        mft = mft_records[doc_name]
        matched += 1

        # Generate UUID
        entry_uuid = str(uuid.uuid4())

        # Fill entry template
        entry_json = json.dumps(entry_template, indent=2)

        # Replace placeholders
        # Escape backslashes for JSON
        parent_path = mft.get('ParentPath', '').replace('\\', '\\\\')
        file_path = parent_path + '\\\\' + doc_name if parent_path else doc_name

        replacements = {
            '{ENTRY_UUID}': entry_uuid,
            '{FILE_NAME}': doc_name,
            '{FILE_PATH}': file_path,
            '{EXTENSION}': mft.get('Extension', ''),
            '{FILE_SIZE}': mft.get('FileSize', '0'),
            '{MFT_ENTRY_NUMBER}': mft.get('EntryNumber', '0'),
            '{MFT_PARENT_ENTRY_NUMBER}': mft.get('ParentEntryNumber', '0'),
            # MFT $SI timestamps (0x10)
            '{MFT_SI_CREATED}': parse_timestamp(mft.get('Created0x10', '')),
            '{MFT_SI_MODIFIED}': parse_timestamp(mft.get('LastModified0x10', '')),
            '{MFT_SI_ACCESSED}': parse_timestamp(mft.get('LastAccess0x10', '')),
            '{MFT_SI_RECORD_CHANGE}': parse_timestamp(mft.get('LastRecordChange0x10', '')),
            # MFT $FN timestamps (0x30)
            '{MFT_FN_CREATED}': parse_timestamp(mft.get('Created0x30', '')),
            '{MFT_FN_MODIFIED}': parse_timestamp(mft.get('LastModified0x30', '')),
            '{MFT_FN_ACCESSED}': parse_timestamp(mft.get('LastAccess0x30', '')),
            '{MFT_FN_RECORD_CHANGE}': parse_timestamp(mft.get('LastRecordChange0x30', '')),
            # XML metadata
            '{DC_CREATOR}': xml_data['dc_creator'],
            '{LAST_MODIFIED_BY}': xml_data['last_modified_by'],
            '{DCTERMS_CREATED}': xml_data['dcterms_created'],
            '{DCTERMS_MODIFIED}': xml_data['dcterms_modified']
        }

        for placeholder, value in replacements.items():
            entry_json = entry_json.replace(placeholder, str(value))

        filled_entry = json.loads(entry_json)
        filled_entries.append(filled_entry)

    # Add to @graph
    template['@graph'] = filled_entries

    # Write output
    with open(output_path, 'w') as f:
        json.dump(template, f, indent=2)

    print(f"\nGenerated: {output_path}")
    print(f"   - Matched: {matched}/{len(office_docs)} documents")
    print(f"   - Total nodes: {len(filled_entries)}")


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: python office_xml_filler.py <mft_csv> <xml_folder> [output.jsonld]")
        print("\nExample:")
        print("  python office_xml_filler.py ../AF-TIMESTOMPING/8857c9daca525a1d3fdeef70119a2277_$MFT.csv ../AF-TIMESTOMPING office_xml_filled.jsonld")
        sys.exit(1)

    mft_csv = sys.argv[1]
    xml_folder = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else 'office_xml_filled.jsonld'

    template_path = Path(__file__).parent / 'office_xml_template.json'
    entry_template_path = Path(__file__).parent / 'office_xml_template-entry.json'

    fill_template(template_path, entry_template_path, mft_csv, xml_folder, output_file)


if __name__ == "__main__":
    main()
