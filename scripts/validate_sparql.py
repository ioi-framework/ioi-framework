#!/usr/bin/env python3
"""Parse all SPARQL .rq files for syntax errors using rdflib."""
import sys
from pathlib import Path

def validate():
    try:
        from rdflib.plugins.sparql import prepareQuery
    except ImportError:
        print("SKIP: rdflib not installed")
        sys.exit(0)

    root = Path(__file__).parent.parent
    rules_dir = root / "RULES"
    rq_files = list(rules_dir.rglob("*.rq"))

    if not rq_files:
        print("WARN: No .rq files found in RULES/")
        sys.exit(0)

    errors = []
    passed = 0

    for rq_path in sorted(rq_files):
        # Skip archive
        if "archive" in rq_path.parts:
            continue
        text = rq_path.read_text(encoding="utf-8")
        # Strip comment lines for parse attempt (rdflib strict on PREFIX)
        try:
            prepareQuery(text)
            passed += 1
        except Exception as e:
            errors.append(f"{rq_path.relative_to(root)}: {str(e)[:120]}")

    if errors:
        print(f"FAIL: SPARQL syntax errors in {len(errors)} file(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print(f"PASS: {passed} SPARQL rule(s) parsed without errors")

if __name__ == "__main__":
    validate()
