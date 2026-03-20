#!/usr/bin/env python3
"""
Windows LNK Template Filler
Fills LNK templates from CSV data (LECmd output)
"""

import csv
import json
import uuid
import os
import copy
from pathlib import Path
from datetime import datetime


def generate_uuid():
    """Generate a UUID for unique identifiers."""
    return str(uuid.uuid4())


def parse_timestamp(ts_str):
    """Parse timestamp string to ISO 8601 format. Returns None if invalid."""
    if not ts_str or ts_str.strip() == '':
        return None

    try:
        # Parse format: 2025-03-04 01:10:37
        dt = datetime.strptime(ts_str.strip(), "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except:
        return None


def extract_filename(path):
    """Extract filename from full path."""
    if not path:
        return ""
    return os.path.basename(path)


def load_template_snippets():
    """Load template snippets."""
    base_path = Path(__file__).parent

    # Load base template
    with open(base_path / "lnk_template_base.json", 'r') as f:
        base_template = json.load(f)

    # Load source file snippet
    with open(base_path / "lnk_template-source_file.json", 'r') as f:
        source_snippet = json.load(f)

    # Load entry snippet
    with open(base_path / "lnk_template-entry.json", 'r') as f:
        entry_snippet = json.load(f)

    return base_template, source_snippet, entry_snippet


def fill_template_from_csv(csv_file_path, output_file_path=None):
    """Fill template from CSV data."""

    # Load template snippets
    base_template, source_snippet, entry_snippet = load_template_snippets()

    # Read CSV data
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        csv_data = list(reader)

    print(f"Processing {len(csv_data)} LNK entries from {csv_file_path}")

    # Generate UUIDs
    source_uuid = generate_uuid()

    # Fill source file template
    source_file = source_snippet[0].copy()
    source_file['@id'] = source_file['@id'].replace('{UUID}', source_uuid)

    # Fill source file facet
    source_facet = source_file['core:hasFacet'][0]
    source_facet['@id'] = source_facet['@id'].replace('{UUID}', source_uuid)

    # Process each LNK entry
    entries = []

    for i, row in enumerate(csv_data):
        entry_uuid = generate_uuid()

        # Fill entry template (deep copy to avoid shared references)
        entry = copy.deepcopy(entry_snippet[0])
        entry['@id'] = entry['@id'].replace('{ENTRY_UUID}', entry_uuid)

        # Fill file facet
        file_facet = entry['core:hasFacet'][0]
        file_facet['@id'] = file_facet['@id'].replace('{ENTRY_UUID}', entry_uuid)

        # Fill LNK facet
        lnk_facet = entry['core:hasFacet'][1]
        lnk_facet['@id'] = lnk_facet['@id'].replace('{ENTRY_UUID}', entry_uuid)

        # Extract source file (LNK file itself)
        source_file_path = row.get('SourceFile', '')
        source_file_name = extract_filename(source_file_path)

        # Fill file facet properties
        file_facet['observable:fileName'] = source_file_name
        file_facet['observable:filePath'] = source_file_path
        file_facet['observable:extension'] = '.lnk'
        file_facet['observable:sizeInBytes']['@value'] = int(row.get('FileSize', 0)) if row.get('FileSize') else 0
        file_facet['observable:accessedTime']['@value'] = parse_timestamp(row.get('SourceAccessed'))
        file_facet['observable:observableCreatedTime']['@value'] = parse_timestamp(row.get('SourceCreated'))
        file_facet['observable:modifiedTime']['@value'] = parse_timestamp(row.get('SourceModified'))

        # Extract target file info
        local_path = row.get('LocalPath', '')
        target_file_name = extract_filename(local_path)

        # Fill LNK facet properties
        lnk_facet['dfc-ext:targetFilePath'] = local_path
        lnk_facet['dfc-ext:targetFileName'] = target_file_name

        # Only add timestamps if they have valid data
        target_created = parse_timestamp(row.get('TargetCreated'))
        if target_created:
            lnk_facet['dfc-ext:targetCreatedTime']['@value'] = target_created
        else:
            del lnk_facet['dfc-ext:targetCreatedTime']

        target_modified = parse_timestamp(row.get('TargetModified'))
        if target_modified:
            lnk_facet['dfc-ext:targetModifiedTime']['@value'] = target_modified
        else:
            del lnk_facet['dfc-ext:targetModifiedTime']

        target_accessed = parse_timestamp(row.get('TargetAccessed'))
        if target_accessed:
            lnk_facet['dfc-ext:targetAccessedTime']['@value'] = target_accessed
        else:
            del lnk_facet['dfc-ext:targetAccessedTime']

        lnk_facet['dfc-ext:relativePath'] = row.get('RelativePath', '')
        lnk_facet['dfc-ext:workingDirectory'] = row.get('WorkingDirectory', '')
        lnk_facet['dfc-ext:arguments'] = row.get('Arguments', '')
        
        # MFT entry numbers - only include if valid
        try:
            mft_entry = row.get('TargetMFTEntryNumber', '').strip()
            if mft_entry:
                lnk_facet['dfc-ext:targetMftEntryNumber']['@value'] = int(mft_entry, 16)
            else:
                del lnk_facet['dfc-ext:targetMftEntryNumber']
        except:
            del lnk_facet['dfc-ext:targetMftEntryNumber']

        try:
            mft_seq = row.get('TargetMFTSequenceNumber', '').strip()
            if mft_seq:
                lnk_facet['dfc-ext:targetMftSequenceNumber']['@value'] = int(mft_seq, 16)
            else:
                del lnk_facet['dfc-ext:targetMftSequenceNumber']
        except:
            del lnk_facet['dfc-ext:targetMftSequenceNumber']

        lnk_facet['dfc-ext:machineId'] = row.get('MachineID', '')
        lnk_facet['dfc-ext:machineMacAddress'] = row.get('MachineMACAddress', '')

        entries.append(entry)

    # Assemble final template
    base_template['@graph'] = [source_file] + entries

    # Auto-generate output filename if not provided
    if output_file_path is None:
        output_file_path = "lnk_filled.jsonld"

    # Write output
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(base_template, f, indent=2, ensure_ascii=False)

    print(f"Generated LNK template: {output_file_path}")
    print(f"   - Source file: 1")
    print(f"   - LNK entries: {len(entries)}")
    print(f"   - Total nodes: {len(entries) + 1}")


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python lnk_template_filler.py <input.csv> [output.jsonld]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    fill_template_from_csv(input_file, output_file)


if __name__ == "__main__":
    main()
