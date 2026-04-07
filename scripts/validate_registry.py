#!/usr/bin/env python3
"""Validate registry.json against required schema."""
import json, sys
from pathlib import Path

REQUIRED_ARTIFACT_KEYS = {
    "artifact_id", "full_name", "parser_tool", "input_format",
    "facet", "instantiator", "template_dir", "status",
    "cases", "rules", "file_facet_columns", "field_types"
}
REQUIRED_FIELD_TYPE_KEYS = {"integer", "datetime", "boolean", "string"}

def validate():
    root = Path(__file__).parent.parent
    reg_path = root / "registry.json"
    if not reg_path.exists():
        print("FAIL: registry.json not found")
        sys.exit(1)

    with open(reg_path) as f:
        reg = json.load(f)

    errors = []

    # Top-level keys
    for k in ("schema_version", "kb_namespace", "graph_iri_pattern", "artifacts"):
        if k not in reg:
            errors.append(f"Missing top-level key: {k}")

    # Each artifact entry
    for name, entry in reg.get("artifacts", {}).items():
        missing = REQUIRED_ARTIFACT_KEYS - set(entry.keys())
        if missing:
            errors.append(f"{name}: missing keys {missing}")
        ft = entry.get("field_types", {})
        missing_ft = REQUIRED_FIELD_TYPE_KEYS - set(ft.keys())
        if missing_ft:
            errors.append(f"{name}.field_types: missing keys {missing_ft}")
        # Instantiator file must exist
        inst_path = root / entry.get("instantiator", "")
        if not inst_path.exists():
            errors.append(f"{name}: instantiator not found: {entry.get('instantiator')}")
        # Template dir must exist
        tmpl_path = root / entry.get("template_dir", "")
        if not tmpl_path.is_dir():
            errors.append(f"{name}: template_dir not found: {entry.get('template_dir')}")

    if errors:
        print("FAIL: registry.json validation errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print(f"PASS: registry.json — {len(reg['artifacts'])} artifacts validated")

if __name__ == "__main__":
    validate()
