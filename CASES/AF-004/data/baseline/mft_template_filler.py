#!/usr/bin/env python3
"""
MFT Template Filler - Clean Version (Custom Facets Only)
Fills MFT templates from CSV data using only custom ioi-ext properties.
This eliminates validation warnings by avoiding non-existent observable:mft* properties.
"""

import csv
import json
import uuid
import os
import copy
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
        # Support scientific / decimal notation
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
    base_path = Path(__file__).parent

    # Load base template
    with open(base_path / "mft_template_base.json", 'r') as f:
        base_template = json.load(f)

    # Load source file snippet
    with open(base_path / "mft_template-source_file.json", 'r') as f:
        source_snippet = json.load(f)

    # Load clean entry snippet (custom facets only)
    with open(base_path / "mft_template-entry_clean.json", 'r') as f:
        entry_snippet = json.load(f)

    # Load action snippet
    with open(base_path / "mft_template-action.json", 'r') as f:
        action_snippet = json.load(f)

    return base_template, source_snippet, entry_snippet, action_snippet


def fill_template_from_csv(csv_file_path, output_file_path):
    """Fill template from CSV data."""

    # Load template snippets
    base_template, source_snippet, entry_snippet, action_snippet = load_template_snippets()

    # Read CSV data
    with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        csv_data = list(reader)

    print(f"Processing {len(csv_data)} MFT entries from {csv_file_path}")

    # Generate UUIDs
    source_uuid = generate_uuid()

    # Fill source file template
    # Deep copy to avoid mutating the snippet template when replacing placeholders
    source_file = copy.deepcopy(source_snippet[0])
    source_file['@id'] = source_file['@id'].replace('{UUID}', source_uuid)

    # Get MFT filename from CSV (assuming first row has source file info)
    mft_filename = csv_data[0].get('SourceFile', 'MFT_export.csv')
    mft_filepath = f"C:\\Windows\\System32\\MFT_export.csv"  # Default path

    # Fill source file properties
    source_facet = source_file['core:hasFacet'][0]
    source_facet['@id'] = source_facet['@id'].replace('{UUID}', source_uuid)
    source_facet['observable:fileName'] = mft_filename
    source_facet['observable:filePath'] = mft_filepath
    source_facet['observable:extension'] = '.csv'
    # Estimate
    source_facet['observable:sizeInBytes']['@value'] = sanitize_int(len(csv_data) * 100)

    # Process each MFT entry
    entries = []
    actions = []

    for i, row in enumerate(csv_data):
        entry_uuid = generate_uuid()
        action_uuid = generate_uuid()

        # Fill entry template (deep copy to avoid shared references)
        entry = copy.deepcopy(entry_snippet[0])
        entry['@id'] = entry['@id'].replace('{ENTRY_UUID}', entry_uuid)

        # Fill file facet
        file_facet = entry['core:hasFacet'][0]
        file_facet['@id'] = file_facet['@id'].replace(
            '{ENTRY_UUID}', entry_uuid)

        # Fill custom facet
        custom_facet = entry['core:hasFacet'][1]
        custom_facet['@id'] = custom_facet['@id'].replace(
            '{ENTRY_UUID}', entry_uuid)

        # Map CSV fields to template placeholders
        field_mapping = {
            'EntryNumber': 'ENTRY_NUMBER',
            'SequenceNumber': 'SEQUENCE_NUMBER',
            'InUse': 'IN_USE',
            'ParentEntryNumber': 'PARENT_ENTRY_NUMBER',
            'ParentSequenceNumber': 'PARENT_SEQUENCE_NUMBER',
            'ParentPath': 'PARENT_PATH',
            'FileName': 'FILE_NAME',
            'Extension': 'FILE_EXTENSION',
            'FileSize': 'FILE_SIZE',
            'ReferenceCount': 'REFERENCE_COUNT',
            'ReparseTarget': 'REPARSE_TARGET',
            'IsDirectory': 'IS_DIRECTORY',
            'HasAds': 'HAS_ADS',
            'IsAds': 'IS_ADS',
            'SI<FN': 'SI_LESS_THAN_FN',
            'uSecZeros': 'USEC_ZEROS',
            'Copied': 'COPIED',
            'SiFlags': 'SI_FLAGS',
            'NameType': 'NAME_TYPE',
            'Created0x10': 'CREATED_0X10',
            'Created0x30': 'CREATED_0X30',
            'LastModified0x10': 'LAST_MODIFIED_0X10',
            'LastModified0x30': 'LAST_MODIFIED_0X30',
            'LastRecordChange0x10': 'LAST_RECORD_CHANGE_0X10',
            'LastRecordChange0x30': 'LAST_RECORD_CHANGE_0X30',
            'LastAccess0x10': 'LAST_ACCESS_0X10',
            'LastAccess0x30': 'LAST_ACCESS_0X30',
            'UpdateSequenceNumber': 'UPDATE_SEQUENCE_NUMBER',
            'LogfileSequenceNumber': 'LOGFILE_SEQUENCE_NUMBER',
            'SecurityId': 'SECURITY_ID',
            'ObjectIdFileDroid': 'OBJECT_ID_FILE_DROID',
            'LoggedUtilStream': 'LOGGED_UTIL_STREAM',
            'ZoneIdContents': 'ZONE_ID_CONTENTS',
            'SourceFile': 'SOURCE_FILE'
        }

        # Fill file facet properties
        file_facet['observable:fileName'] = row.get('FileName', '')
        file_facet['observable:extension'] = row.get('Extension', '')
        file_facet['observable:filePath'] = f"{row.get('ParentPath', '')}{row.get('FileName', '')}"
        file_facet['observable:isDirectory']['@value'] = row.get(
            'IsDirectory', 'FALSE').lower()
        file_facet['observable:sizeInBytes']['@value'] = sanitize_int(row.get(
            'FileSize', '0'))
        file_facet['observable:ntfsHardLinkCount']['@value'] = sanitize_int(row.get(
            'ReferenceCount', '0'))
        file_facet['observable:ntfsOwnerSID'] = row.get('SecurityId', '')

        # Fill MFT_FLAGS with default boolean value (not in CSV)
        custom_facet['ioi-ext:mftFlags']['@value'] = 'false'

        # Fill custom facet properties
        for csv_field, placeholder in field_mapping.items():
            value = row.get(csv_field, '')

            # Handle special cases
            if placeholder == 'NAME_TYPE':
                # Keep as string value (DosWindows, Posix, etc.)
                custom_facet['ioi-ext:nameType'] = value or 'Unknown'
            elif placeholder == 'ENTRY_NUMBER':
                custom_facet['ioi-ext:entryNumber']['@value'] = sanitize_int(value)
            elif placeholder == 'SEQUENCE_NUMBER':
                custom_facet['ioi-ext:sequenceNumber']['@value'] = sanitize_int(value)
            elif placeholder == 'PARENT_ENTRY_NUMBER':
                custom_facet['ioi-ext:parentEntryNumber']['@value'] = sanitize_int(value)
            elif placeholder == 'PARENT_SEQUENCE_NUMBER':
                custom_facet['ioi-ext:parentSequenceNumber']['@value'] = sanitize_int(value)
            elif placeholder == 'FILE_SIZE':
                custom_facet['ioi-ext:fileSize']['@value'] = sanitize_int(value)
            elif placeholder == 'REFERENCE_COUNT':
                custom_facet['ioi-ext:referenceCount']['@value'] = sanitize_int(value)
            elif placeholder == 'SI_FLAGS':
                # Keep as string value (Archive, Hidden|System, etc.)
                custom_facet['ioi-ext:siFlags'] = value or 'None'
            elif placeholder == 'UPDATE_SEQUENCE_NUMBER':
                custom_facet['ioi-ext:updateSequenceNumber']['@value'] = sanitize_int(value)
            elif placeholder == 'LOGFILE_SEQUENCE_NUMBER':
                custom_facet['ioi-ext:logfileSequenceNumber']['@value'] = sanitize_int(value)
            elif placeholder == 'IN_USE':
                custom_facet['ioi-ext:inUse']['@value'] = value.lower() if value else 'false'
            elif placeholder == 'IS_DIRECTORY':
                custom_facet['ioi-ext:isDirectory']['@value'] = value.lower() if value else 'false'
            elif placeholder == 'HAS_ADS':
                custom_facet['ioi-ext:hasAds']['@value'] = value.lower() if value else 'false'
            elif placeholder == 'IS_ADS':
                custom_facet['ioi-ext:isAds']['@value'] = value.lower() if value else 'false'
            elif placeholder == 'SI_LESS_THAN_FN':
                custom_facet['ioi-ext:siLessThanFn']['@value'] = value.lower() if value else 'false'
            elif placeholder == 'USEC_ZEROS':
                custom_facet['ioi-ext:uSecZeros']['@value'] = sanitize_int(value)
            elif placeholder == 'COPIED':
                custom_facet['ioi-ext:copied']['@value'] = value.lower() if value else 'false'
            elif placeholder == 'CREATED_0X10':
                custom_facet['ioi-ext:created0x10']['@value'] = sanitize_timestamp(value)
            elif placeholder == 'CREATED_0X30':
                custom_facet['ioi-ext:created0x30']['@value'] = sanitize_timestamp(value)
            elif placeholder == 'LAST_MODIFIED_0X10':
                custom_facet['ioi-ext:lastModified0x10']['@value'] = sanitize_timestamp(value)
            elif placeholder == 'LAST_MODIFIED_0X30':
                custom_facet['ioi-ext:lastModified0x30']['@value'] = sanitize_timestamp(value)
            elif placeholder == 'LAST_RECORD_CHANGE_0X10':
                custom_facet['ioi-ext:lastRecordChange0x10']['@value'] = sanitize_timestamp(value)
            elif placeholder == 'LAST_RECORD_CHANGE_0X30':
                custom_facet['ioi-ext:lastRecordChange0x30']['@value'] = sanitize_timestamp(value)
            elif placeholder == 'LAST_ACCESS_0X10':
                custom_facet['ioi-ext:lastAccess0x10']['@value'] = sanitize_timestamp(value)
            elif placeholder == 'LAST_ACCESS_0X30':
                custom_facet['ioi-ext:lastAccess0x30']['@value'] = sanitize_timestamp(value)
            elif placeholder == 'PARENT_PATH':
                custom_facet['ioi-ext:parentPath'] = value or ''
            elif placeholder == 'FILE_NAME':
                custom_facet['ioi-ext:fileName'] = value or ''
            elif placeholder == 'FILE_EXTENSION':
                custom_facet['ioi-ext:extension'] = value or ''
            elif placeholder == 'REPARSE_TARGET':
                custom_facet['ioi-ext:reparseTarget'] = value or ''
            elif placeholder == 'SECURITY_ID':
                custom_facet['ioi-ext:securityId'] = value or ''
            elif placeholder == 'OBJECT_ID_FILE_DROID':
                custom_facet['ioi-ext:objectIdFileDroid'] = value or ''
            elif placeholder == 'LOGGED_UTIL_STREAM':
                custom_facet['ioi-ext:loggedUtilStream'] = value or ''
            elif placeholder == 'ZONE_ID_CONTENTS':
                custom_facet['ioi-ext:zoneIdContents'] = value or ''
            elif placeholder == 'SOURCE_FILE':
                custom_facet['ioi-ext:sourceFile'] = value or ''

        entries.append(entry)

        # Create action linking source to entry
        # Deep copy the action snippet to preserve placeholder values for subsequent rows
        action = copy.deepcopy(action_snippet[0])
        action['@id'] = action['@id'].replace('{ACTION_UUID}', action_uuid)
        action['core:source']['@id'] = action['core:source']['@id'].replace(
            '{SOURCE_UUID}', source_uuid)
        action['core:target']['@id'] = action['core:target']['@id'].replace(
            '{ENTRY_UUID}', entry_uuid)
        actions.append(action)

    # Combine all components
    final_template = copy.deepcopy(base_template)
    final_template['@graph'] = [source_file] + entries + actions

    # Write output
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(final_template, f, indent=2, ensure_ascii=False)

    print(f"Generated clean template: {output_file_path}")
    print(f"   - Source file: 1")
    print(f"   - MFT entries: {len(entries)}")
    print(f"   - Actions: {len(actions)}")
    print(f"   - Total nodes: {len(final_template['@graph'])}")
    print(f"   - Uses only custom ioi-ext properties (no warnings!)")


def fill_template_chunked(csv_file_path, output_base_path, chunk_size):
    """
    Split CSV into chunks and write one JSON-LD file per chunk.
    Prints each output path to stdout on its own line.
    """
    base_template, source_snippet, entry_snippet, action_snippet = load_template_snippets()

    with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        csv_data = list(reader)

    print(f"Processing {len(csv_data)} MFT entries in chunks of {chunk_size}")

    # Strip .jsonld suffix so we can append _chunk0.jsonld etc.
    if output_base_path.endswith('.jsonld'):
        base = output_base_path[:-len('.jsonld')]
    else:
        base = output_base_path

    chunk_paths = []
    for chunk_idx, start in enumerate(range(0, len(csv_data), chunk_size)):
        chunk_data = csv_data[start:start + chunk_size]
        chunk_path = f"{base}_chunk{chunk_idx}.jsonld"

        # Reuse fill_template_from_csv on this slice by temporarily
        # writing a minimal wrapper that operates on chunk_data directly
        source_uuid = generate_uuid()
        source_file = copy.deepcopy(source_snippet[0])
        source_file['@id'] = source_file['@id'].replace('{UUID}', source_uuid)
        mft_filename = chunk_data[0].get('SourceFile', 'MFT_export.csv')
        source_facet = source_file['core:hasFacet'][0]
        source_facet['@id'] = source_facet['@id'].replace('{UUID}', source_uuid)
        source_facet['observable:fileName'] = mft_filename
        source_facet['observable:filePath'] = f"C:\\Windows\\System32\\MFT_export.csv"
        source_facet['observable:extension'] = '.csv'
        source_facet['observable:sizeInBytes']['@value'] = sanitize_int(len(chunk_data) * 100)

        entries = []
        actions = []
        for row in chunk_data:
            entry_uuid = generate_uuid()
            action_uuid = generate_uuid()
            entry = copy.deepcopy(entry_snippet[0])
            entry['@id'] = entry['@id'].replace('{ENTRY_UUID}', entry_uuid)
            file_facet = entry['core:hasFacet'][0]
            file_facet['@id'] = file_facet['@id'].replace('{ENTRY_UUID}', entry_uuid)
            custom_facet = entry['core:hasFacet'][1]
            custom_facet['@id'] = custom_facet['@id'].replace('{ENTRY_UUID}', entry_uuid)

            # Reuse same field-filling logic (copied from fill_template_from_csv)
            file_facet['observable:fileName'] = row.get('FileName', '')
            file_facet['observable:extension'] = row.get('Extension', '')
            file_facet['observable:filePath'] = f"{row.get('ParentPath', '')}{row.get('FileName', '')}"
            file_facet['observable:isDirectory']['@value'] = row.get('IsDirectory', 'FALSE').lower()
            file_facet['observable:sizeInBytes']['@value'] = sanitize_int(row.get('FileSize', '0'))
            file_facet['observable:ntfsHardLinkCount']['@value'] = sanitize_int(row.get('ReferenceCount', '0'))
            file_facet['observable:ntfsOwnerSID'] = row.get('SecurityId', '')
            custom_facet['ioi-ext:mftFlags']['@value'] = 'false'

            field_mapping = {
                'EntryNumber': 'ioi-ext:entryNumber', 'SequenceNumber': 'ioi-ext:sequenceNumber',
                'ParentEntryNumber': 'ioi-ext:parentEntryNumber', 'ParentSequenceNumber': 'ioi-ext:parentSequenceNumber',
                'UpdateSequenceNumber': 'ioi-ext:updateSequenceNumber', 'LogfileSequenceNumber': 'ioi-ext:logfileSequenceNumber',
                'FileSize': 'ioi-ext:fileSize', 'ReferenceCount': 'ioi-ext:referenceCount',
                'uSecZeros': 'ioi-ext:uSecZeros',
            }
            bool_fields = {'InUse': 'ioi-ext:inUse', 'IsDirectory': 'ioi-ext:isDirectory',
                           'HasAds': 'ioi-ext:hasAds', 'IsAds': 'ioi-ext:isAds',
                           'SI<FN': 'ioi-ext:siLessThanFn', 'Copied': 'ioi-ext:copied'}
            ts_fields = {'Created0x10': 'ioi-ext:created0x10', 'Created0x30': 'ioi-ext:created0x30',
                         'LastModified0x10': 'ioi-ext:lastModified0x10', 'LastModified0x30': 'ioi-ext:lastModified0x30',
                         'LastRecordChange0x10': 'ioi-ext:lastRecordChange0x10', 'LastRecordChange0x30': 'ioi-ext:lastRecordChange0x30',
                         'LastAccess0x10': 'ioi-ext:lastAccess0x10', 'LastAccess0x30': 'ioi-ext:lastAccess0x30'}
            str_fields = {'ParentPath': 'ioi-ext:parentPath', 'FileName': 'ioi-ext:fileName',
                          'Extension': 'ioi-ext:extension', 'ReparseTarget': 'ioi-ext:reparseTarget',
                          'SecurityId': 'ioi-ext:securityId', 'ObjectIdFileDroid': 'ioi-ext:objectIdFileDroid',
                          'LoggedUtilStream': 'ioi-ext:loggedUtilStream', 'ZoneIdContents': 'ioi-ext:zoneIdContents',
                          'SourceFile': 'ioi-ext:sourceFile', 'NameType': 'ioi-ext:nameType',
                          'SiFlags': 'ioi-ext:siFlags'}

            for csv_f, key in field_mapping.items():
                custom_facet[key]['@value'] = sanitize_int(row.get(csv_f, '0'))
            for csv_f, key in bool_fields.items():
                v = row.get(csv_f, '')
                custom_facet[key]['@value'] = v.lower() if v else 'false'
            for csv_f, key in ts_fields.items():
                custom_facet[key]['@value'] = sanitize_timestamp(row.get(csv_f, ''))
            for csv_f, key in str_fields.items():
                custom_facet[key] = row.get(csv_f, '') or ''

            entries.append(entry)
            action = copy.deepcopy(action_snippet[0])
            action['@id'] = action['@id'].replace('{ACTION_UUID}', action_uuid)
            action['core:source']['@id'] = action['core:source']['@id'].replace('{SOURCE_UUID}', source_uuid)
            action['core:target']['@id'] = action['core:target']['@id'].replace('{ENTRY_UUID}', entry_uuid)
            actions.append(action)

        final_template = copy.deepcopy(base_template)
        final_template['@graph'] = [source_file] + entries + actions

        with open(chunk_path, 'w', encoding='utf-8') as f:
            json.dump(final_template, f, indent=2, ensure_ascii=False)

        print(f"CHUNK_OUTPUT:{chunk_path}")
        chunk_paths.append(chunk_path)

    print(f"Generated {len(chunk_paths)} chunk file(s)")
    return chunk_paths


def main():
    """Main function."""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='MFT Template Filler')
    parser.add_argument('input', help='Input CSV file')
    parser.add_argument('output', help='Output JSON-LD file')
    parser.add_argument('--chunk-size', type=int, default=0,
                        help='Split output into chunks of N entries (0 = no chunking)')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: CSV file '{args.input}' not found")
        sys.exit(1)

    if args.chunk_size > 0:
        fill_template_chunked(args.input, args.output, args.chunk_size)
    else:
        fill_template_from_csv(args.input, args.output)


if __name__ == "__main__":
    main()
