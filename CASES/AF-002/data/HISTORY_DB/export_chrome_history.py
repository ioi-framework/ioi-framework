#!/usr/bin/env python3
"""
Chrome History SQLite Exporter
Exports Chrome's History SQLite database to the JSON format expected by
history_template_filler_sqlite.py.

Usage:
    python3 export_chrome_history.py <path/to/History> <output.json>

Note: Chrome must be closed (or the History file copied) before running,
as Chrome locks the file while it is open.
"""

import json
import sys
import sqlite3
from datetime import datetime, timedelta


WEBKIT_EPOCH = datetime(1601, 1, 1)


def webkit_to_iso(webkit_time):
    if not webkit_time:
        return None
    return (WEBKIT_EPOCH + timedelta(microseconds=webkit_time)).strftime('%Y-%m-%d %H:%M:%S')


def export(history_path, output_path):
    print(f"Opening {history_path}...")
    con = sqlite3.connect(f"file:{history_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    urls = []
    for row in con.execute(
        "SELECT id, url, title, visit_count, typed_count, last_visit_time FROM urls"
    ):
        urls.append({
            "id": row["id"],
            "url": row["url"],
            "title": row["title"] or "",
            "visit_count": row["visit_count"],
            "typed_count": row["typed_count"],
            "last_visit_datetime": webkit_to_iso(row["last_visit_time"])
        })

    visits = []
    for row in con.execute(
        "SELECT id, url, visit_time, visit_duration, transition, from_visit FROM visits"
    ):
        visits.append({
            "id": row["id"],
            "url": row["url"],
            "visit_datetime": webkit_to_iso(row["visit_time"]),
            "visit_duration": row["visit_duration"],
            "transition": row["transition"],
            "from_visit": row["from_visit"]
        })

    con.close()

    out = {"urls": urls, "visits": visits}
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"✓ Exported {len(urls)} URLs and {len(visits)} visits to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 export_chrome_history.py <path/to/History> <output.json>")
        sys.exit(1)
    export(sys.argv[1], sys.argv[2])
