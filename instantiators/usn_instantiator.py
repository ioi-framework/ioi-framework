#!/usr/bin/env python3
"""
USN Journal Template Filler
Fills USN journal templates from JSON or CSV data using standard FileFacet + custom UsnFacet.
Follows the MFT baseline pattern for CASE/UCO compliance.
"""

import json
import uuid
import os
import copy
import csv
from datetime import datetime, timezone
from pathlib import Path


def sanitize_int(value, default='0'):
    """Return a stringified integer, coercing booleans/empty strings to safe defaults."""
    if value is None:
        return default
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, (int, float)):
        return str(int(value))

    value_str = str(value).strip()
    if not value_str:
        return default

    lowered = value_str.lower()
    if lowered == 'true':
        return '1'
    if lowered == 'false':
        return '0'

    try:
        if 'e' in lowered or '.' in value_str:
            return str(int(float(value_str)))
        return str(int(value_str))
    except ValueError:
        digits = ''.join(ch for ch in value_str if ch.isdigit())
        return digits if digits else default


DEFAULT_TIMESTAMP = '1970-01-01T00:00:00Z'


def _format_iso(dt: datetime) -> str:
    iso = dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    return iso.replace('.000000Z', 'Z')


def sanitize_timestamp(value, default=DEFAULT_TIMESTAMP):
    """Normalize timestamps to ISO 8601 strings. Fallback to default if parsing fails."""
    if value is None:
        return default

    value_str = str(value).strip()
    if not value_str or value_str.startswith('0000-00-00'):
        return default

    iso_candidate = value_str.replace('Z', '+00:00') if value_str.endswith('Z') else value_str
    try:
        dt = datetime.fromisoformat(iso_candidate)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return _format_iso(dt)
    except ValueError:
        pass

    datetime_formats = [
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
        '%m/%d/%Y %H:%M:%S',
        '%m/%d/%Y %H:%M',
        '%Y-%m-%d'
    ]

    time_only_formats = [
        '%H:%M:%S.%f',
        '%H:%M:%S',
        '%H:%M.%f',
        '%H:%M'
    ]

    for fmt in datetime_formats:
        try:
            dt = datetime.strptime(value_str, fmt)
            return _format_iso(dt.replace(tzinfo=timezone.utc))
        except ValueError:
            continue

    for fmt in time_only_formats:
        try:
            dt = datetime.strptime(value_str, fmt)
            dt = dt.replace(year=1970, month=1, day=1, tzinfo=timezone.utc)
            return _format_iso(dt)
        except ValueError:
            continue

    try:
        seconds = float(value_str)
        dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
        return _format_iso(dt)
    except Exception:
        return default


def generate_uuid():
    """Generate a UUID for unique identifiers."""
    return str(uuid.uuid4())


def load_template_snippets():
    """Load template snippets."""
    base_path = Path(__file__).parent / 'templates' / 'usn'

    # Load base template
    with open(base_path / "usn_template_base.json", 'r') as f:
        base_template = json.load(f)

    # Load source file snippet
    with open(base_path / "usn_template-source_file.json", 'r') as f:
        source_snippet = json.load(f)

    # Load entry snippet
    with open(base_path / "usn_template-entry_clean.json", 'r') as f:
        entry_snippet = json.load(f)

    # Load action snippet
    with open(base_path / "usn_template-action.json", 'r') as f:
        action_snippet = json.load(f)

    return base_template, source_snippet, entry_snippet, action_snippet


def fill_template_from_data(input_file_path, output_file_path):
    """Fill template from JSON or CSV data."""

    # Load template snippets
    base_template, source_snippet, entry_snippet, action_snippet = load_template_snippets()

    # Detect file format and load data
    json_data = []
    file_ext = Path(input_file_path).suffix.lower()

    if file_ext == '.csv':
        # CSV format (MFTECmd output)
        print(f"Detected CSV format: {input_file_path}")
        with open(input_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            json_data = list(reader)
        print(f"Loaded {len(json_data)} records from CSV")
    else:
        # Try JSON array first, fallback to JSONL
        try:
            with open(input_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    json_data = data
                elif isinstance(data, dict):
                    # Check for usn_operations key (case 2 format)
                    if 'usn_operations' in data:
                        json_data = data['usn_operations']
                    else:
                        json_data = [data]
                else:
                    json_data = [data]
        except json.JSONDecodeError:
            # JSONL format (one JSON per line)
            with open(input_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        json_data.append(json.loads(line))

    print(f"Processing {len(json_data)} USN journal entries from {input_file_path}")

    # Generate UUID for source file
    source_uuid = generate_uuid()

    # Fill source file template
    source_file = copy.deepcopy(source_snippet[0])
    source_file['@id'] = source_file['@id'].replace('{SOURCE_UUID}', source_uuid)

    # Use real NTFS $UsnJrnl:$J system artifact path (alternate data stream)
    source_filename = '$J'
    source_filepath = "C:\\$Extend\\$UsnJrnl:$J"

    # Fill source file properties
    source_facet = source_file['core:hasFacet'][0]
    source_facet['@id'] = source_facet['@id'].replace('{SOURCE_UUID}', source_uuid)
    source_facet['observable:fileName'] = source_filename
    source_facet['observable:extension'] = ''
    source_facet['observable:filePath'] = source_filepath
    # Real USN Journal size (50MB default)
    source_facet['observable:sizeInBytes']['@value'] = sanitize_int(52428800)

    # Process each USN entry
    entries = []
    actions = []

    for i, row in enumerate(json_data):
        entry_uuid = generate_uuid()
        action_uuid = generate_uuid()

        # Fill entry template (deep copy to avoid shared references)
        entry = copy.deepcopy(entry_snippet[0])
        entry['@id'] = entry['@id'].replace('{ENTRY_UUID}', entry_uuid)

        # Fill file facet
        file_facet = entry['core:hasFacet'][0]
        file_facet['@id'] = file_facet['@id'].replace('{ENTRY_UUID}', entry_uuid)

        # Fill custom USN facet
        usn_facet = entry['core:hasFacet'][1]
        usn_facet['@id'] = usn_facet['@id'].replace('{ENTRY_UUID}', entry_uuid)

        # Extract values from JSON row
        file_name = row.get('Name', '')
        file_extension = row.get('Extension', '')
        parent_path = row.get('ParentPath', '')
        update_timestamp = sanitize_timestamp(row.get('UpdateTimestamp', DEFAULT_TIMESTAMP))

        # Construct full file path
        if parent_path:
            file_path = f"{parent_path}\\{file_name}" if not parent_path.endswith('\\') else f"{parent_path}{file_name}"
        else:
            file_path = file_name

        # Fill FileFacet properties (standard CASE/UCO)
        file_facet['observable:fileName'] = file_name
        file_facet['observable:extension'] = file_extension
        file_facet['observable:filePath'] = file_path
        file_facet['observable:modifiedTime']['@value'] = update_timestamp

        # Fill UsnFacet properties (custom ioi-ext)
        usn_facet['ioi-ext:entryNumber']['@value'] = sanitize_int(row.get('EntryNumber', 0))
        usn_facet['ioi-ext:sequenceNumber']['@value'] = sanitize_int(row.get('SequenceNumber', 0))
        usn_facet['ioi-ext:parentEntryNumber']['@value'] = sanitize_int(row.get('ParentEntryNumber', 0))
        usn_facet['ioi-ext:parentSequenceNumber']['@value'] = sanitize_int(row.get('ParentSequenceNumber', 0))
        usn_facet['ioi-ext:parentPath'] = parent_path
        usn_facet['ioi-ext:updateSequenceNumber']['@value'] = sanitize_int(row.get('UpdateSequenceNumber', 0))
        usn_facet['ioi-ext:updateTimestamp']['@value'] = update_timestamp
        usn_facet['ioi-ext:updateReasons'] = row.get('UpdateReasons', '')
        usn_facet['ioi-ext:fileAttributes'] = row.get('FileAttributes', '')
        usn_facet['ioi-ext:offsetToData']['@value'] = sanitize_int(row.get('OffsetToData', 0))
        usn_facet['ioi-ext:sourceFile'] = source_filename

        entries.append(entry)

        # Create action linking source to entry
        action = copy.deepcopy(action_snippet[0])
        action['@id'] = action['@id'].replace('{ACTION_UUID}', action_uuid)
        action['core:source']['@id'] = action['core:source']['@id'].replace('{SOURCE_UUID}', source_uuid)
        action['core:target']['@id'] = action['core:target']['@id'].replace('{ENTRY_UUID}', entry_uuid)
        actions.append(action)

    # Combine all components
    final_template = copy.deepcopy(base_template)
    final_template['@graph'] = [source_file] + entries + actions

    # Write output
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(final_template, f, indent=2, ensure_ascii=False)

    print(f"Generated USN template: {output_file_path}")
    print(f"   - Source file: 1")
    print(f"   - USN entries: {len(entries)}")
    print(f"   - Actions: {len(actions)}")
    print(f"   - Total nodes: {len(final_template['@graph'])}")
    print(f"   - Uses FileFacet + custom UsnFacet (CASE/UCO compliant)")


def fill_template_chunked(input_file_path, output_base_path, chunk_size):
    """Fill template in chunks, writing multiple output files."""
    base_template, source_snippet, entry_snippet, action_snippet = load_template_snippets()

    json_data = []
    file_ext = Path(input_file_path).suffix.lower()

    if file_ext == '.csv':
        print(f"Detected CSV format: {input_file_path}")
        with open(input_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            json_data = list(reader)
        print(f"Loaded {len(json_data)} records from CSV")
    else:
        try:
            with open(input_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    json_data = data
                elif isinstance(data, dict):
                    if 'usn_operations' in data:
                        json_data = data['usn_operations']
                    else:
                        json_data = [data]
                else:
                    json_data = [data]
        except json.JSONDecodeError:
            with open(input_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        json_data.append(json.loads(line))

    print(f"Processing {len(json_data)} USN entries in chunks of {chunk_size}")

    base_no_ext = output_base_path.replace('.jsonld', '')
    total_chunks = (len(json_data) + chunk_size - 1) // chunk_size

    source_uuid = generate_uuid()
    source_file = copy.deepcopy(source_snippet[0])
    source_file['@id'] = source_file['@id'].replace('{SOURCE_UUID}', source_uuid)
    source_facet = source_file['core:hasFacet'][0]
    source_facet['@id'] = source_facet['@id'].replace('{SOURCE_UUID}', source_uuid)
    source_facet['observable:fileName'] = '$J'
    source_facet['observable:extension'] = ''
    source_facet['observable:filePath'] = "C:\\$Extend\\$UsnJrnl:$J"
    source_facet['observable:sizeInBytes']['@value'] = sanitize_int(52428800)

    for chunk_idx in range(total_chunks):
        chunk_rows = json_data[chunk_idx * chunk_size:(chunk_idx + 1) * chunk_size]
        entries = []
        actions = []

        for row in chunk_rows:
            entry_uuid = generate_uuid()
            action_uuid = generate_uuid()

            entry = copy.deepcopy(entry_snippet[0])
            entry['@id'] = entry['@id'].replace('{ENTRY_UUID}', entry_uuid)

            file_facet = entry['core:hasFacet'][0]
            file_facet['@id'] = file_facet['@id'].replace('{ENTRY_UUID}', entry_uuid)

            usn_facet = entry['core:hasFacet'][1]
            usn_facet['@id'] = usn_facet['@id'].replace('{ENTRY_UUID}', entry_uuid)

            file_name = row.get('Name', '')
            file_extension = row.get('Extension', '')
            parent_path = row.get('ParentPath', '')
            update_timestamp = sanitize_timestamp(row.get('UpdateTimestamp', DEFAULT_TIMESTAMP))

            if parent_path:
                file_path = f"{parent_path}\\{file_name}" if not parent_path.endswith('\\') else f"{parent_path}{file_name}"
            else:
                file_path = file_name

            file_facet['observable:fileName'] = file_name
            file_facet['observable:extension'] = file_extension
            file_facet['observable:filePath'] = file_path
            file_facet['observable:modifiedTime']['@value'] = update_timestamp

            usn_facet['ioi-ext:entryNumber']['@value'] = sanitize_int(row.get('EntryNumber', 0))
            usn_facet['ioi-ext:sequenceNumber']['@value'] = sanitize_int(row.get('SequenceNumber', 0))
            usn_facet['ioi-ext:parentEntryNumber']['@value'] = sanitize_int(row.get('ParentEntryNumber', 0))
            usn_facet['ioi-ext:parentSequenceNumber']['@value'] = sanitize_int(row.get('ParentSequenceNumber', 0))
            usn_facet['ioi-ext:parentPath'] = parent_path
            usn_facet['ioi-ext:updateSequenceNumber']['@value'] = sanitize_int(row.get('UpdateSequenceNumber', 0))
            usn_facet['ioi-ext:updateTimestamp']['@value'] = update_timestamp
            usn_facet['ioi-ext:updateReasons'] = row.get('UpdateReasons', '')
            usn_facet['ioi-ext:fileAttributes'] = row.get('FileAttributes', '')
            usn_facet['ioi-ext:offsetToData']['@value'] = sanitize_int(row.get('OffsetToData', 0))
            usn_facet['ioi-ext:sourceFile'] = '$J'

            entries.append(entry)

            action = copy.deepcopy(action_snippet[0])
            action['@id'] = action['@id'].replace('{ACTION_UUID}', action_uuid)
            action['core:source']['@id'] = action['core:source']['@id'].replace('{SOURCE_UUID}', source_uuid)
            action['core:target']['@id'] = action['core:target']['@id'].replace('{ENTRY_UUID}', entry_uuid)
            actions.append(action)

        chunk_template = copy.deepcopy(base_template)
        chunk_template['@graph'] = [source_file] + entries + actions

        chunk_path = f"{base_no_ext}_chunk{chunk_idx}.jsonld"
        with open(chunk_path, 'w', encoding='utf-8') as f:
            json.dump(chunk_template, f, indent=2, ensure_ascii=False)

        print(f"CHUNK_OUTPUT:{chunk_path}")
        print(f"   Chunk {chunk_idx + 1}/{total_chunks}: {len(entries)} entries -> {chunk_path}")


def main():
    """Main function."""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='USN Journal Template Filler')
    parser.add_argument('input_file', help='Input file (JSON, JSONL, or CSV)')
    parser.add_argument('output_file', help='Output JSON-LD file')
    parser.add_argument('--chunk-size', type=int, default=0,
                        help='Split output into chunks of N entries (0 = no chunking)')
    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found")
        sys.exit(1)

    if args.chunk_size > 0:
        fill_template_chunked(args.input_file, args.output_file, args.chunk_size)
    else:
        fill_template_from_data(args.input_file, args.output_file)


if __name__ == "__main__":
    main()
