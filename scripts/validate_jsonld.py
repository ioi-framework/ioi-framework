#!/usr/bin/env python3
"""Parse all test/*.jsonld files with rdflib to verify they are valid JSON-LD."""
import sys
from pathlib import Path
import json

def validate():
    try:
        from rdflib import ConjunctiveGraph
    except ImportError:
        print("SKIP: rdflib not installed")
        sys.exit(0)

    root = Path(__file__).parent.parent
    cases_dir = root / "CASES"
    jsonld_files = list(cases_dir.rglob("test/*.jsonld"))

    if not jsonld_files:
        print("WARN: No test/*.jsonld files found in CASES/")
        sys.exit(0)

    errors = []
    passed = 0

    for jld_path in sorted(jsonld_files):
        try:
            g = ConjunctiveGraph()
            g.parse(str(jld_path), format="json-ld")
            if len(g) == 0:
                errors.append(f"{jld_path.relative_to(root)}: parsed but contains 0 triples")
            else:
                passed += 1
        except Exception as e:
            errors.append(f"{jld_path.relative_to(root)}: {str(e)[:120]}")

    if errors:
        print(f"FAIL: JSON-LD parse errors in {len(errors)} file(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print(f"PASS: {passed} test JSON-LD file(s) parsed without errors")

if __name__ == "__main__":
    validate()
