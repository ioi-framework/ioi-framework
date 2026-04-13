#!/usr/bin/env python3
"""
Chrome History SQLite Exporter

Exports Chrome's History SQLite database to the JSON shape consumed by
instantiators/history_instantiator.py.

Manual path:
  History SQLite -> export_chrome_history.py -> history_instantiator.py

Autopsy path:
  The Autopsy plugin performs this same SQLite -> JSON export internally, so
  this helper is not needed when running through Autopsy.
"""

import argparse
import json
import sqlite3
from datetime import datetime, timedelta


WEBKIT_EPOCH = datetime(1601, 1, 1)


def webkit_to_iso(webkit_time):
    """Convert a Chrome WebKit timestamp to an ISO-like string."""
    if not webkit_time:
        return None
    return (WEBKIT_EPOCH + timedelta(microseconds=webkit_time)).strftime("%Y-%m-%d %H:%M:%S")


def export(history_path, output_path):
    print("Opening %s..." % history_path)
    conn = sqlite3.connect("file:%s?mode=ro" % history_path, uri=True)
    conn.row_factory = sqlite3.Row

    urls = []
    for row in conn.execute(
        "SELECT id, url, title, visit_count, typed_count, last_visit_time FROM urls"
    ):
        urls.append({
            "id": row["id"],
            "url": row["url"],
            "title": row["title"] or "",
            "visit_count": row["visit_count"] or 0,
            "typed_count": row["typed_count"] or 0,
            "last_visit_datetime": webkit_to_iso(row["last_visit_time"]),
        })

    visits = []
    for row in conn.execute(
        "SELECT id, url, visit_time, visit_duration, transition, from_visit FROM visits"
    ):
        visits.append({
            "id": row["id"],
            "url": row["url"],
            "visit_datetime": webkit_to_iso(row["visit_time"]),
            "visit_duration": row["visit_duration"] or 0,
            "transition": row["transition"] or 0,
            "from_visit": row["from_visit"] or 0,
        })

    conn.close()

    payload = {"urls": urls, "visits": visits}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print("Exported %d URLs and %d visits to %s" % (len(urls), len(visits), output_path))


def main():
    parser = argparse.ArgumentParser(
        description="Export a Chrome History SQLite database to framework JSON."
    )
    parser.add_argument("history_db", help="Path to a copied Chrome History SQLite database")
    parser.add_argument("output_json", help="Output JSON path")
    args = parser.parse_args()
    export(args.history_db, args.output_json)


if __name__ == "__main__":
    main()
