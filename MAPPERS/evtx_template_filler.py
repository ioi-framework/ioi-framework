#!/usr/bin/env python3
"""
Windows Event Log Template Filler
Fills Event Log templates from JSONL data using observable:EventRecord + standard EventRecordFacet + custom EventLogFacet.
Follows CASE/UCO standard facet pattern with custom extension only for unmapped fields.
"""

import json
import uuid
import os
import copy
from pathlib import Path


def generate_uuid():
    """Generate a UUID for unique identifiers."""
    return str(uuid.uuid4())


def load_template_snippets():
    """Load template snippets."""
    base_path = Path(__file__).parent

    # Load base template
    with open(base_path / "evtx_template_base.json", 'r') as f:
        base_template = json.load(f)

    # Load source file snippet
    with open(base_path / "evtx_template-source_file.json", 'r') as f:
        source_snippet = json.load(f)

    # Load entry snippet
    with open(base_path / "evtx_template-entry_clean.json", 'r') as f:
        entry_snippet = json.load(f)

    # Load action snippet
    with open(base_path / "evtx_template-action.json", 'r') as f:
        action_snippet = json.load(f)

    return base_template, source_snippet, entry_snippet, action_snippet


def fill_template_from_jsonl(jsonl_file_path, output_file_path, max_entries=None):
    """Fill template from JSONL data (one JSON object per line) or JSON array."""

    # Load template snippets
    base_template, source_snippet, entry_snippet, action_snippet = load_template_snippets()

    # Try to load as JSON array/object first, then fall back to JSONL
    jsonl_data = []
    try:
        with open(jsonl_file_path, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
            if isinstance(data, list):
                # JSON array
                jsonl_data = data[:max_entries] if max_entries else data
            elif isinstance(data, dict):
                # Single JSON object - wrap in list
                jsonl_data = [data]
            print(f"Loaded as JSON array/object")
    except json.JSONDecodeError:
        # Fall back to JSONL (line-by-line parsing)
        with open(jsonl_file_path, 'r', encoding='utf-8-sig') as f:
            for line in f:
                if line.strip():
                    jsonl_data.append(json.loads(line))
                if max_entries and len(jsonl_data) >= max_entries:
                    break
        print(f"Loaded as JSONL (line-by-line)")

    print(f"Processing {len(jsonl_data)} Event Log entries from {jsonl_file_path}")

    # Generate UUID for source file
    source_uuid = generate_uuid()

    # Fill source file template
    source_file = copy.deepcopy(source_snippet[0])
    source_file['@id'] = source_file['@id'].replace('{SOURCE_UUID}', source_uuid)

    # Get source file info from first entry
    source_filepath = jsonl_data[0].get('SourceFile', 'C:\\Windows\\System32\\winevt\\Logs\\System.evtx')
    source_filename = os.path.basename(source_filepath).replace('.evtx', '')

    # Fill source file properties
    source_facet = source_file['uco-core:hasFacet'][0]
    source_facet['@id'] = source_facet['@id'].replace('{SOURCE_UUID}', source_uuid)
    source_facet['observable:fileName'] = source_filename
    source_facet['observable:filePath'] = source_filepath
    # Estimate source file size (rough calculation)
    source_facet['observable:sizeInBytes']['@value'] = str(len(jsonl_data) * 500)

    # Process each Event Log entry
    entries = []
    actions = []
    devices = {}  # Track unique devices to avoid duplicates

    for i, row in enumerate(jsonl_data):
        entry_uuid = generate_uuid()
        action_uuid = generate_uuid()
        computer = row.get('Computer', '')
        computer_uuid = devices.get(computer)
        if not computer_uuid:
            computer_uuid = generate_uuid()
            devices[computer] = computer_uuid

        # Fill entry template (deep copy to avoid shared references)
        entry = copy.deepcopy(entry_snippet[0])
        entry['@id'] = entry['@id'].replace('{ENTRY_UUID}', entry_uuid)

        # Fill standard EventRecordFacet
        standard_facet = entry['core:hasFacet'][0]
        standard_facet['@id'] = standard_facet['@id'].replace('{ENTRY_UUID}', entry_uuid)
        standard_facet['observable:eventID'] = str(row.get('EventId', 0))
        standard_facet['observable:eventRecordID'] = str(row.get('EventRecordId', ''))

        # Handle MapDescription (might be missing in some entries)
        event_description = row.get('MapDescription', row.get('Provider', 'Event'))
        standard_facet['observable:eventRecordText'] = event_description

        # Convert Payload dict to JSON string if needed
        payload = row.get('Payload', '')
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        standard_facet['observable:eventRecordRaw'] = payload

        standard_facet['observable:eventRecordServiceName'] = row.get('Provider', '')
        standard_facet['observable:eventType'] = row.get('Level', '')
        standard_facet['observable:startTime']['@value'] = row.get('TimeCreated', '1970-01-01T00:00:00Z')

        # Fill eventRecordDevice
        device_ref = standard_facet['observable:eventRecordDevice']
        device_ref['@id'] = device_ref['@id'].replace('{COMPUTER_UUID}', computer_uuid)
        device_ref['core:name'] = computer

        # Fill custom EventLogFacet (only unmapped fields)
        custom_facet = entry['core:hasFacet'][1]
        custom_facet['@id'] = custom_facet['@id'].replace('{ENTRY_UUID}', entry_uuid)
        custom_facet['dfc-ext:channel'] = row.get('Channel', '')
        custom_facet['dfc-ext:keywords'] = row.get('Keywords', '')
        custom_facet['dfc-ext:processId']['@value'] = str(row.get('ProcessId', 0))
        custom_facet['dfc-ext:threadId']['@value'] = str(row.get('ThreadId', 0))
        custom_facet['dfc-ext:chunkNumber']['@value'] = str(row.get('ChunkNumber', 0))
        custom_facet['dfc-ext:extraDataOffset']['@value'] = str(row.get('ExtraDataOffset', 0))
        custom_facet['dfc-ext:hiddenRecord']['@value'] = str(row.get('HiddenRecord', False)).lower()
        custom_facet['dfc-ext:sourceFile'] = source_filepath
        custom_facet['dfc-ext:payloadData1'] = row.get('PayloadData1', '')
        custom_facet['dfc-ext:payloadData2'] = row.get('PayloadData2', '')

        entries.append(entry)

        # Create action linking source to entry
        action = copy.deepcopy(action_snippet[0])
        action['@id'] = action['@id'].replace('{ACTION_UUID}', action_uuid)
        action['uco-core:source']['@id'] = action['uco-core:source']['@id'].replace('{SOURCE_UUID}', source_uuid)
        action['uco-core:target']['@id'] = action['uco-core:target']['@id'].replace('{ENTRY_UUID}', entry_uuid)
        actions.append(action)

    # Combine all components
    final_template = base_template.copy()
    final_template['@graph'] = [source_file] + entries + actions

    # Write output
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(final_template, f, indent=2, ensure_ascii=False)

    print(f"Generated Event Log template: {output_file_path}")
    print(f"   - Source file: 1")
    print(f"   - Event entries: {len(entries)}")
    print(f"   - Actions: {len(actions)}")
    print(f"   - Total nodes: {len(final_template['@graph'])}")
    print(f"   - Uses observable:EventRecord + standard EventRecordFacet + custom EventLogFacet (CASE/UCO compliant)")


def main():
    """Main function."""
    import sys

    if len(sys.argv) < 3:
        print("Usage: python3 evtx_template_filler.py <input.jsonl> <output.jsonld> [max_entries]")
        sys.exit(1)

    jsonl_file = sys.argv[1]
    output_file = sys.argv[2]
    max_entries = int(sys.argv[3]) if len(sys.argv) > 3 else None

    if not os.path.exists(jsonl_file):
        print(f"Error: JSONL file '{jsonl_file}' not found")
        sys.exit(1)

    fill_template_from_jsonl(jsonl_file, output_file, max_entries)


if __name__ == "__main__":
    main()
