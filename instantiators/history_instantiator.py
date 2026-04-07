#!/usr/bin/env python3
"""
Chrome History Template Filler
Fills CASE/UCO template from Chrome History SQLite export
Uses standard CASE/UCO classes: URLHistoryEntry, URLHistoryFacet, URLVisit, URLVisitFacet
"""

import json
import uuid
from datetime import datetime, timedelta

def webkit_to_datetime(webkit_time):
    """Convert Chrome WebKit timestamp to ISO 8601 datetime."""
    if webkit_time is None:
        return None
    # WebKit epoch: January 1, 1601
    # Microseconds since WebKit epoch
    webkit_epoch = datetime(1601, 1, 1)
    return (webkit_epoch + timedelta(microseconds=webkit_time)).isoformat() + 'Z'

def microseconds_to_seconds(microseconds):
    """Convert microseconds to seconds for duration."""
    if microseconds is None:
        return "0"
    return str(microseconds / 1000000.0)

def transition_to_string(transition_value):
    """Convert Chrome transition type integer to string."""
    # Chrome transition types
    # Since UCO URLTransitionTypeVocab is empty, using plain strings
    transitions = {
        0: "link",
        1: "typed",
        2: "auto_bookmark",
        3: "auto_subframe",
        4: "manual_subframe",
        5: "generated",
        6: "start_page",
        7: "form_submit",
        8: "reload",
        9: "keyword",
        10: "keyword_generated"
    }

    # Extract core transition type (lower 8 bits)
    core_type = transition_value & 0xFF if transition_value else 0
    return transitions.get(core_type, "link")

def fill_template_from_json(json_file_path, output_file_path):
    """Fill template from Chrome History JSON data."""

    print(f"Loading Chrome History data from {json_file_path}...")
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    urls_data = data.get('urls', [])
    visits_data = data.get('visits', [])

    print(f"Found {len(urls_data)} URLs and {len(visits_data)} visits")

    graph = []

    # Track ID mappings (database ID -> generated UUID)
    url_id_map = {}  # Maps database URL ID to observable:URL @id
    visit_id_map = {}

    # Process URLs - Create both observable:URL and URLHistoryEntry
    print("Processing URLs...")
    for url_entry in urls_data:
        url_id = url_entry.get('id')
        if url_id is None:
            continue

        # Create observable:URL object (the actual URL resource)
        url_resource_id = f"kb:url--{uuid.uuid4()}"
        url_id_map[url_id] = url_resource_id

        url_resource = {
            "@id": url_resource_id,
            "@type": "observable:URL",
            "uco-core:hasFacet": [
                {
                    "@id": f"kb:url-facet--{uuid.uuid4()}",
                    "@type": "observable:URLFacet",
                    "observable:fullValue": url_entry.get('url', '')
                }
            ]
        }
        graph.append(url_resource)

        # Create URLHistoryEntry (contains metadata about URL visits)
        history_entry_id = f"kb:url-history-entry--{uuid.uuid4()}"
        url_obj = {
            "@id": history_entry_id,
            "@type": "observable:URLHistoryEntry",
            "uco-core:hasFacet": [
                {
                    "@id": f"kb:url-history-facet--{uuid.uuid4()}",
                    "@type": "observable:URLHistoryFacet",
                    "observable:url": {
                        "@id": url_resource_id
                    },
                    "observable:pageTitle": url_entry.get('title', ''),
                    "observable:visitCount": {
                        "@type": "xsd:nonNegativeInteger",
                        "@value": str(url_entry.get('visit_count', 0))
                    },
                    "observable:manuallyEnteredCount": {
                        "@type": "xsd:nonNegativeInteger",
                        "@value": str(url_entry.get('typed_count', 0))
                    }
                }
            ]
        }

        # Add lastVisit if available
        last_visit = url_entry.get('last_visit_datetime')
        if last_visit:
            url_obj["uco-core:hasFacet"][0]["observable:lastVisit"] = {
                "@type": "xsd:dateTime",
                "@value": last_visit.replace(' ', 'T') + 'Z'
            }

        graph.append(url_obj)

    # Process Visits (URLVisit)
    print("Processing visits...")
    for visit_entry in visits_data:
        visit_id = visit_entry.get('id')
        url_id = visit_entry.get('url')

        if visit_id is None or url_id is None:
            continue

        generated_visit_id = f"kb:url-visit--{uuid.uuid4()}"
        visit_id_map[visit_id] = generated_visit_id

        visit_obj = {
            "@id": generated_visit_id,
            "@type": "observable:URLVisit",
            "uco-core:hasFacet": [
                {
                    "@id": f"kb:url-visit-facet--{uuid.uuid4()}",
                    "@type": "observable:URLVisitFacet"
                }
            ]
        }

        facet = visit_obj["uco-core:hasFacet"][0]

        # Visit time
        visit_datetime = visit_entry.get('visit_datetime')
        if visit_datetime:
            facet["observable:visitTime"] = {
                "@type": "xsd:dateTime",
                "@value": visit_datetime.replace(' ', 'T') + 'Z'
            }

        # Visit duration
        visit_duration = visit_entry.get('visit_duration')
        if visit_duration is not None:
            duration_seconds = microseconds_to_seconds(visit_duration)
            facet["observable:visitDuration"] = {
                "@type": "xsd:duration",
                "@value": f"PT{duration_seconds}S"
            }

        # Transition type (plain string - UCO vocab is empty)
        transition = visit_entry.get('transition')
        if transition is not None:
            facet["observable:urlTransitionType"] = transition_to_string(transition)

        # Reference to URL entry (using mapped UUID)
        if url_id in url_id_map:
            facet["observable:url"] = {
                "@id": url_id_map[url_id]
            }

        # From visit (referrer) - using mapped UUID
        from_visit = visit_entry.get('from_visit')
        if from_visit and from_visit != 0 and from_visit in visit_id_map:
            facet["observable:fromURLVisit"] = {
                "@id": visit_id_map[from_visit]
            }

        graph.append(visit_obj)

    # Create final JSON-LD structure
    output = {
        "@context": {
            "@vocab": "https://ontology.unifiedcyberontology.org/uco/observable/",
            "uco-core": "https://ontology.unifiedcyberontology.org/uco/core/",
            "observable": "https://ontology.unifiedcyberontology.org/uco/observable/",
            "vocabulary": "https://ontology.unifiedcyberontology.org/uco/vocabulary/",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "kb": "https://ioi-framework.github.io/kb/"
        },
        "@graph": graph
    }

    # Write output
    print(f"Writing output to {output_file_path}...")
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Successfully generated {len(graph)} objects")
    print(f"  - {len(urls_data)} URL history entries")
    print(f"  - {len(visits_data)} URL visits")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "history_filled.jsonld"
    else:
        input_file = "sqlite_exact.json"
        output_file = "history_filled.jsonld"

    fill_template_from_json(input_file, output_file)
