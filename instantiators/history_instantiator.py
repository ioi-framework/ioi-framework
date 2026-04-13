#!/usr/bin/env python3
"""
Browser History Instantiator - CASE/UCO JSON-LD generator for Chrome History.

Input contract (used by the Autopsy plugin):
  {
    "urls": [
      {
        "id": 1,
        "url": "https://example.com",
        "title": "Example",
        "visit_count": 3,
        "typed_count": 1,
        "last_visit_datetime": 13300000000000000
      }
    ],
    "visits": [
      {
        "id": 10,
        "url": 1,
        "visit_datetime": 13300000000000000,
        "visit_duration": 2000000,
        "transition": 1,
        "from_visit": 0
      }
    ]
  }

CLI (standard 2-argument contract - callable by MapperRunner):
  python3 history_instantiator.py <history.json> <output.jsonld>
"""

import argparse
import copy
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path


def generate_uuid():
    return str(uuid.uuid4())


def sanitize_int(value, default="0"):
    if value is None or str(value).strip() == "":
        return default
    try:
        return str(int(float(str(value))))
    except (TypeError, ValueError):
        return default


def webkit_to_datetime(webkit_time):
    """Convert Chrome WebKit timestamp to ISO 8601 datetime."""
    if webkit_time is None:
        return None
    webkit_epoch = datetime(1601, 1, 1)
    return (webkit_epoch + timedelta(microseconds=int(webkit_time))).isoformat() + "Z"


def sanitize_timestamp(value, default=""):
    """Normalize History timestamps from WebKit or string input."""
    if value is None or str(value).strip() == "":
        return default

    if isinstance(value, (int, float)):
        try:
            return webkit_to_datetime(value)
        except Exception:
            return default

    value_str = str(value).strip()
    if not value_str or value_str == "0":
        return default

    if "T" in value_str:
        return value_str if value_str.endswith("Z") else value_str + "Z"
    if " " in value_str:
        return value_str.replace(" ", "T") + "Z"

    try:
        return webkit_to_datetime(int(float(value_str)))
    except Exception:
        return default


def microseconds_to_seconds(microseconds):
    """Convert microseconds to seconds for xsd:duration."""
    if microseconds is None or str(microseconds).strip() == "":
        return "0"
    try:
        return str(float(microseconds) / 1000000.0)
    except (TypeError, ValueError):
        return "0"


def transition_to_string(transition_value):
    """Convert Chrome transition type integer to string."""
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
        10: "keyword_generated",
    }
    try:
        core_type = int(transition_value) & 0xFF
    except (TypeError, ValueError):
        core_type = 0
    return transitions.get(core_type, "link")


def _replace_placeholders(obj, replacements):
    if isinstance(obj, dict):
        return {k: _replace_placeholders(v, replacements) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_replace_placeholders(item, replacements) for item in obj]
    if isinstance(obj, str):
        for placeholder, value in replacements.items():
            obj = obj.replace(placeholder, value)
        return obj
    return obj


def load_template_snippets():
    """Load history template snippets."""
    base_path = Path(__file__).parent / "templates" / "browser_history"

    with open(base_path / "history_template_base.json", "r", encoding="utf-8") as f:
        base_template = json.load(f)

    with open(base_path / "history_template-url_resource.json", "r", encoding="utf-8") as f:
        url_snippet = json.load(f)

    with open(base_path / "history_template-entry.json", "r", encoding="utf-8") as f:
        entry_snippet = json.load(f)

    with open(base_path / "history_template-visit.json", "r", encoding="utf-8") as f:
        visit_snippet = json.load(f)

    return base_template, url_snippet, entry_snippet, visit_snippet


def fill_template_from_json(json_file_path, output_file_path):
    """Fill templates from Chrome History JSON data."""
    print("Loading Chrome History data from %s..." % json_file_path)
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    urls_data = data.get("urls", [])
    visits_data = data.get("visits", [])

    print("Found %d URLs and %d visits" % (len(urls_data), len(visits_data)))

    base_template, url_snippet, entry_snippet, visit_snippet = load_template_snippets()
    graph = []

    url_uuid_map = {}
    visit_uuid_map = {}

    print("Processing URLs...")
    for url_entry in urls_data:
        url_id = url_entry.get("id")
        if url_id is None:
            continue

        url_uuid = generate_uuid()
        entry_uuid = generate_uuid()
        url_uuid_map[url_id] = url_uuid

        replacements = {
            "{URL_UUID}": url_uuid,
            "{ENTRY_UUID}": entry_uuid,
            "{FULL_URL}": str(url_entry.get("url", "") or ""),
            "{TITLE}": str(url_entry.get("title", "") or ""),
            "{VISIT_COUNT}": sanitize_int(url_entry.get("visit_count", 0)),
            "{TYPED_COUNT}": sanitize_int(url_entry.get("typed_count", 0)),
            "{LAST_VISIT_DATETIME}": sanitize_timestamp(url_entry.get("last_visit_datetime"), ""),
        }

        url_node = _replace_placeholders(copy.deepcopy(url_snippet[0]), replacements)
        entry_node = _replace_placeholders(copy.deepcopy(entry_snippet[0]), replacements)

        if not replacements["{LAST_VISIT_DATETIME}"]:
            entry_facet = entry_node["core:hasFacet"][0]
            entry_facet.pop("observable:lastVisit", None)

        graph.append(url_node)
        graph.append(entry_node)

    for visit_entry in visits_data:
        visit_id = visit_entry.get("id")
        if visit_id is not None:
            visit_uuid_map[visit_id] = generate_uuid()

    print("Processing visits...")
    for visit_entry in visits_data:
        visit_id = visit_entry.get("id")
        url_id = visit_entry.get("url")

        if visit_id is None:
            continue

        replacements = {
            "{VISIT_UUID}": visit_uuid_map.get(visit_id, generate_uuid()),
            "{URL_UUID}": url_uuid_map.get(url_id, ""),
            "{VISIT_DATETIME}": sanitize_timestamp(visit_entry.get("visit_datetime"), ""),
            "{VISIT_DURATION_SECONDS}": microseconds_to_seconds(visit_entry.get("visit_duration")),
            "{TRANSITION}": transition_to_string(visit_entry.get("transition")),
            "{FROM_VISIT_UUID}": visit_uuid_map.get(visit_entry.get("from_visit"), ""),
        }

        visit_node = _replace_placeholders(copy.deepcopy(visit_snippet[0]), replacements)
        visit_facet = visit_node["core:hasFacet"][0]

        if not replacements["{URL_UUID}"]:
            visit_facet.pop("observable:url", None)
        if not replacements["{VISIT_DATETIME}"]:
            visit_facet.pop("observable:visitTime", None)
        if not replacements["{FROM_VISIT_UUID}"] or not visit_entry.get("from_visit"):
            visit_facet.pop("observable:fromURLVisit", None)

        graph.append(visit_node)

    base_template["@graph"] = graph

    print("Writing output to %s..." % output_file_path)
    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(base_template, f, indent=2, ensure_ascii=False)

    print("Successfully generated %d objects" % len(graph))
    print("  - %d URL resources" % len(urls_data))
    print("  - %d URL history entries" % len(urls_data))
    print("  - %d URL visits" % len(visits_data))


def main():
    parser = argparse.ArgumentParser(
        description="Generate CASE/UCO JSON-LD from Chrome History export JSON."
    )
    parser.add_argument("input_file", help="History export JSON containing urls[] and visits[]")
    parser.add_argument("output_file", help="Output JSON-LD path")
    args = parser.parse_args()

    fill_template_from_json(args.input_file, args.output_file)


if __name__ == "__main__":
    main()
