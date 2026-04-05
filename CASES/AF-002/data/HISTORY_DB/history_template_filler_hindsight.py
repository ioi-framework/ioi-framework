#!/usr/bin/env python3
"""
Chrome History Template Filler - Hindsight JSONL input
Fills CASE/UCO template from Hindsight JSONL export (hindsight.py -f jsonl).
Uses standard CASE/UCO classes: URLHistoryEntry, URLHistoryFacet, URLVisit, URLVisitFacet

Hindsight JSONL: one record per line, each line is a flat JSON object with fields:
  url, title, visit_count, typed_count, datetime, visit_duration, transition, from_visit
  visit_duration is a string in H:MM:SS.ffffff format
  datetime is ISO 8601 with timezone (e.g. 2025-10-08T13:10:38.083368+00:00)
  (data_type == "chrome:history:page_visited" lines only)
"""

import json
import sys
import uuid


def duration_string_to_seconds(duration_str):
    """Convert Hindsight duration string 'H:MM:SS.ffffff' to total seconds."""
    if not duration_str:
        return "0"
    try:
        parts = duration_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        secs = float(parts[2])
        return str(hours * 3600 + minutes * 60 + secs)
    except Exception:
        return "0"


def transition_to_string(transition_value):
    """Convert Chrome transition type integer to string."""
    transitions = {
        0: "link", 1: "typed", 2: "auto_bookmark", 3: "auto_subframe",
        4: "manual_subframe", 5: "generated", 6: "start_page",
        7: "form_submit", 8: "reload", 9: "keyword", 10: "keyword_generated"
    }
    core_type = transition_value & 0xFF if transition_value else 0
    return transitions.get(core_type, "link")


def fill_template_from_hindsight_jsonl(jsonl_file_path, output_file_path):
    """Fill template from Hindsight JSONL export."""

    print(f"Loading Hindsight JSONL data from {jsonl_file_path}...")

    records = []
    with open(jsonl_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get('data_type') == 'chrome:history:page_visited':
                records.append(obj)

    print(f"Found {len(records)} page_visited records")

    graph = []
    url_count = 0
    visit_count = 0
    visit_id_map = {}  # Maps Hindsight visit_id -> generated UUID for from_visit linking

    for record in records:
        raw_url = record.get('url', '')
        if not raw_url:
            continue

        # Create observable:URL
        url_resource_id = f"kb:url--{uuid.uuid4()}"
        url_resource = {
            "@id": url_resource_id,
            "@type": "observable:URL",
            "uco-core:hasFacet": [
                {
                    "@id": f"kb:url-facet--{uuid.uuid4()}",
                    "@type": "observable:URLFacet",
                    "observable:fullValue": raw_url
                }
            ]
        }
        graph.append(url_resource)

        # Build URLHistoryFacet
        history_facet = {
            "@id": f"kb:url-history-facet--{uuid.uuid4()}",
            "@type": "observable:URLHistoryFacet",
            "observable:url": {"@id": url_resource_id},
            "observable:pageTitle": record.get('title', ''),
            "observable:visitCount": {
                "@type": "xsd:nonNegativeInteger",
                "@value": str(record.get('visit_count', 0))
            },
            "observable:manuallyEnteredCount": {
                "@type": "xsd:nonNegativeInteger",
                "@value": str(record.get('typed_count', 0))
            }
        }

        # lastVisit — Hindsight 'datetime' field (ISO 8601)
        last_visit = record.get('datetime')
        if last_visit:
            history_facet["observable:lastVisit"] = {
                "@type": "xsd:dateTime",
                "@value": last_visit.replace(' ', 'T') if 'Z' not in last_visit else last_visit
            }

        history_entry = {
            "@id": f"kb:url-history-entry--{uuid.uuid4()}",
            "@type": "observable:URLHistoryEntry",
            "uco-core:hasFacet": [history_facet]
        }
        graph.append(history_entry)
        url_count += 1

        # Build URLVisit
        visit_facet = {
            "@id": f"kb:url-visit-facet--{uuid.uuid4()}",
            "@type": "observable:URLVisitFacet",
            "observable:url": {"@id": url_resource_id}
        }

        # visitTime — same datetime field
        if last_visit:
            visit_facet["observable:visitTime"] = {
                "@type": "xsd:dateTime",
                "@value": last_visit.replace(' ', 'T') if 'Z' not in last_visit else last_visit
            }

        # visitDuration — Hindsight gives "H:MM:SS.ffffff" string
        duration = record.get('visit_duration')
        if duration:
            visit_facet["observable:visitDuration"] = {
                "@type": "xsd:duration",
                "@value": f"PT{duration_string_to_seconds(duration)}S"
            }

        # urlTransitionType — Hindsight has integer transition, convert to string
        transition = record.get('transition')
        if transition is not None:
            visit_facet["observable:urlTransitionType"] = transition_to_string(transition)

        # fromURLVisit — Hindsight provides from_visit as visit_id integer
        from_visit_id = record.get('from_visit')
        if from_visit_id and from_visit_id != 0 and from_visit_id in visit_id_map:
            visit_facet["observable:fromURLVisit"] = {"@id": visit_id_map[from_visit_id]}

        generated_visit_id = f"kb:url-visit--{uuid.uuid4()}"
        visit_id = record.get('visit_id')
        if visit_id is not None:
            visit_id_map[visit_id] = generated_visit_id

        visit_obj = {
            "@id": generated_visit_id,
            "@type": "observable:URLVisit",
            "uco-core:hasFacet": [visit_facet]
        }
        graph.append(visit_obj)
        visit_count += 1

    # Final JSON-LD structure — identical context/graph shape to sqlite variant
    output = {
        "@context": {
            "@vocab": "https://ontology.unifiedcyberontology.org/uco/observable/",
            "uco-core": "https://ontology.unifiedcyberontology.org/uco/core/",
            "observable": "https://ontology.unifiedcyberontology.org/uco/observable/",
            "vocabulary": "https://ontology.unifiedcyberontology.org/uco/vocabulary/",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "kb": "http://example.org/kb/"
        },
        "@graph": graph
    }

    print(f"Writing output to {output_file_path}...")
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"✓ Successfully generated {len(graph)} objects")
    print(f"  - {url_count} URL history entries")
    print(f"  - {visit_count} URL visits")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 history_template_filler_hindsight.py <hindsight.jsonl> [output.jsonld]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "history_filled.jsonld"

    fill_template_from_hindsight_jsonl(input_file, output_file)
