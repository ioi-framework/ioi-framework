#!/usr/bin/env python3
"""Parse all SPARQL .rq files for syntax errors using rdflib.
Rules using bif: (Virtuoso built-ins) are warned but not failed —
they are valid Virtuoso SPARQL even though rdflib does not recognise bif:."""
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
    warnings = []
    passed = 0

    for rq_path in sorted(rq_files):
        if "archive" in rq_path.parts:
            continue
        text = rq_path.read_text(encoding="utf-8")
        rel = str(rq_path.relative_to(root))

        # bif: is Virtuoso-specific — warn but do not fail
        if "bif:" in text:
            warnings.append(f"{rel}: uses bif: (Virtuoso built-in) — not portable to rdflib")
            passed += 1
            continue

        try:
            prepareQuery(text)
            passed += 1
        except Exception as e:
            errors.append(f"{rel}: {str(e)[:120]}")

    for w in warnings:
        print(f"WARN: {w}")

    if errors:
        print(f"FAIL: SPARQL syntax errors in {len(errors)} file(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print(f"PASS: {passed} SPARQL rule(s) checked ({len(warnings)} Virtuoso-specific warned)")

if __name__ == "__main__":
    validate()
