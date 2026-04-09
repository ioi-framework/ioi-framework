# IoI Framework — Instantiator Contract

> **Version**: 1.0  
> **Status**: Canonical  
> **Rule**: This contract is **immutable once published**. Logic changes require a new version bump.

---

## TL;DR Answer

**Yes — all instantiators must follow the same structure.** The contract is what lets `MapperRunner` call any instantiator without code changes. If the interface deviates, the plugin breaks silently.

---

## 1. CLI Interface (MANDATORY)

`MapperRunner` always calls:

```bash
python3 instantiators/{artifact}_instantiator.py <input_file> <output_file>
python3 instantiators/{artifact}_instantiator.py <input_file> <output_file> --chunk-size N   # MFT / USN only
```

**Rules:**
- `sys.argv[1]` = single input file path (CSV, JSON, or JSONL)
- `sys.argv[2]` = output file path (`.jsonld`)
- `--chunk-size N` is optional; only MFT and USN need to handle it
- **Never** accept 3 positional arguments (office_xml currently violates this — it takes `mft_csv xml_folder output`, which MapperRunner cannot call)
- Always use `argparse` — never raw `sys.argv` index access

### `main()` Template

```python
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input',  help='Input file (CSV / JSON / JSONL)')
    parser.add_argument('output', help='Output JSON-LD file')
    parser.add_argument('--chunk-size', type=int, default=0,
                        help='Rows per chunk (0 = no chunking)')
    args = parser.parse_args()

    if args.chunk_size > 0:
        fill_template_chunked(args.input, args.output, args.chunk_size)
    else:
        fill_template_from_data(args.input, args.output)

if __name__ == '__main__':
    main()
```

---

## 2. Required Functions

| Function | Required | Purpose |
|---|---|---|
| `fill_template_from_data(input_path, output_path)` | ✅ Always | Main entry — reads input, fills templates, writes JSON-LD |
| `fill_template_chunked(input_path, output_base, chunk_size)` | Only MFT / USN | Writes `{output_base}_chunk{N}.jsonld` per chunk |
| `load_template_snippets()` | ✅ Always | Loads 4 template files from `Path(__file__).parent/templates/{artifact}/` |
| `generate_uuid()` | ✅ Always | Returns `str(uuid.uuid4())` |
| `sanitize_int(value, default='0')` | ✅ Always | Safe int conversion (handles bool/float/sci notation) |
| `sanitize_timestamp(value, default=DEFAULT_TIMESTAMP)` | ✅ Always | Returns ISO 8601 UTC or `DEFAULT_TIMESTAMP` |

### Canonical Sanitizers (copy exactly)

```python
DEFAULT_TIMESTAMP = '1970-01-01T00:00:00Z'

def sanitize_int(value, default='0'):
    if value is None or str(value).strip() == '':
        return default
    try:
        return str(int(float(str(value).strip().rstrip('%'))))
    except (ValueError, TypeError):
        return default

def sanitize_timestamp(value, default=DEFAULT_TIMESTAMP):
    if not value or str(value).strip() == '':
        return default
    v = str(value).strip()
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%d %H:%M:%S.%f',
        '%m/%d/%Y %H:%M:%S',
        '%m/%d/%Y %I:%M:%S %p',
    ]
    for fmt in formats:
        try:
            from datetime import datetime
            return datetime.strptime(v, fmt).strftime('%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            continue
    return default
```

---

## 3. Template Loading (MANDATORY pattern)

Templates live in `instantiators/templates/{artifact}/`, resolved relative to the script:

```python
def load_template_snippets():
    base = Path(__file__).parent / 'templates' / '{artifact}'

    with open(base / '{artifact}_template_base.json') as f:
        base_template = json.load(f)
    with open(base / '{artifact}_template-source_file.json') as f:
        source_snippet = json.load(f)
    with open(base / '{artifact}_template-entry_clean.json') as f:
        entry_snippet = json.load(f)
    with open(base / '{artifact}_template-action.json') as f:
        action_snippet = json.load(f)

    return base_template, source_snippet, entry_snippet, action_snippet
```

**Rules:**
- Always use `Path(__file__).parent` — never hardcoded or relative paths
- Template folder: `templates/{artifact}/` (lowercase artifact name)
- All 4 template files required (base, source_file, entry_clean, action)
- `copy.deepcopy()` when filling per-row — never mutate the snippet in-place

---

## 4. Output Structure (MANDATORY)

Every instantiator's final `@graph` must be:

```
[@graph] = [source_file_node] + [N entry_nodes] + [N action_nodes]
```

### Source File Node
```json
{
  "@id": "kb:{artifact}-source--{UUID}",
  "@type": "observable:File",
  "core:hasFacet": [
    {
      "@id": "kb:{artifact}-source-facet--{UUID}",
      "@type": "observable:FileFacet",
      "observable:fileName": "...",
      "observable:filePath": "..."
    }
  ]
}
```

### Entry Node
```json
{
  "@id": "kb:{artifact}--{UUID}",
  "@type": "observable:File",
  "core:hasFacet": [
    {
      "@id": "kb:{artifact}-file-facet--{UUID}",
      "@type": "observable:FileFacet",
      "observable:fileName": "..."
    },
    {
      "@id": "kb:{artifact}-ext-facet--{UUID}",
      "@type": "ioi-ext:{Artifact}Facet",
      "ioi-ext:someField": "..."
    }
  ]
}
```

> **Note**: Use the most specific UCO type available (e.g. `observable:EventRecord` for EVTX, `observable:URLHistoryEntry` for History). When no exact UCO class exists, fall back to `observable:File`.

### Action Node
```json
{
  "@id": "kb:{artifact}-action--{UUID}",
  "@type": "uco-action:InvestigativeAction",
  "core:source": { "@id": "kb:{artifact}-source--{SOURCE_UUID}" },
  "core:target": { "@id": "kb:{artifact}--{ENTRY_UUID}" }
}
```

---

## 5. Namespace Contract (MANDATORY — no exceptions)

The `@context` block in `{artifact}_template_base.json` MUST include:

```json
{
  "@context": {
    "kb":          "https://ioi-framework.github.io/kb/",
    "ioi-ext":     "https://ioi-framework.github.io/ns/ioi-ext/",
    "core":        "https://ontology.unifiedcyberontology.org/uco/core/",
    "observable":  "https://ontology.unifiedcyberontology.org/uco/observable/",
    "uco-action":  "https://ontology.unifiedcyberontology.org/uco/action/",
    "xsd":         "http://www.w3.org/2001/XMLSchema#"
  }
}
```

**Rules:**
- `core:hasFacet` — always use `core:` prefix, never `uco-core:hasFacet`
- `core:source` / `core:target` — never `uco-core:source`
- `example.org` — forbidden everywhere
- No `@vocab` shorthand — all prefixes must be explicit

---

## 6. Chunking Protocol (MFT / USN only)

When `--chunk-size N` is passed, `fill_template_chunked()` must:

1. Split input into groups of N rows
2. Write each group to `{output_base}_chunk{zero_padded_N}.jsonld`
3. Print `CHUNK_OUTPUT:{path}` for each file written
4. Exit 0

MapperRunner detects chunks by glob: `{artifact}_{idx}_chunk*.jsonld`.

```python
def fill_template_chunked(input_path, output_base, chunk_size):
    rows = read_all_rows(input_path)
    for i, batch in enumerate(chunks(rows, chunk_size)):
        path = f"{output_base}_chunk{i:04d}.jsonld"
        write_jsonld(batch, path)
        print(f"CHUNK_OUTPUT:{path}")
```

---

## 7. Exit Behavior

| Condition | Exit code | Effect |
|---|---|---|
| Success | `0` | MapperRunner collects output file(s) |
| Any failure | non-zero | MapperRunner logs `SEVERE` and skips artifact |

Never swallow exceptions silently — if the instantiator exits 0 but produces no output file, MapperRunner logs WARNING and moves on.

---

## 8. Current Compliance Status

| Instantiator | CLI contract | Templates | Namespaces | Action nodes | sanitize helpers | Status |
|---|---|---|---|---|---|---|
| `mft_instantiator.py` | ✅ argparse | ✅ 4 files | ✅ correct | ✅ | ✅ | ✅ Compliant |
| `usn_instantiator.py` | ✅ argparse | ✅ 4 files | ✅ correct | ✅ | ✅ | ✅ Compliant |
| `lnk_instantiator.py` | ⚠️ raw sys.argv | ⚠️ 3 files (no action) | ✅ correct | ❌ missing | ⚠️ partial | 🔧 Needs fix |
| `evtx_instantiator.py` | ⚠️ raw sys.argv | ✅ 4 files | ❌ `uco-core:` prefix | ✅ | ⚠️ partial | 🔧 Needs fix |
| `history_instantiator.py` | ⚠️ raw sys.argv | ❌ no templates (inline) | ⚠️ missing ioi-ext | ❌ missing | ❌ missing | 🔴 Major refactor |
| `office_xml_instantiator.py` | ❌ 2 positional inputs | ⚠️ 2 files (non-standard) | ⚠️ missing ioi-ext | ❌ missing | ⚠️ partial | 🔴 Major refactor |

### Fix Priority

| Priority | Instantiator | What to fix |
|---|---|---|
| P0 | `office_xml` | CLI takes 2 inputs — MapperRunner **cannot call it**. Rearchitect: pre-merge MFT+XML to a single JSON input file in ArtifactExporter, then pass that single JSON to the instantiator |
| P1 | `evtx` | Replace all `uco-core:hasFacet` → `core:hasFacet`, `uco-core:source` → `core:source`; add argparse |
| P1 | `lnk` | Add argparse; add action template + InvestigativeAction nodes; add sanitize helpers |
| P2 | `history` | Migrate inline @context to template files; add argparse; add ioi-ext facet for custom fields; add action nodes |

---

## 9. Adding a New Instantiator (Checklist)

1. Create `instantiators/{artifact}_instantiator.py` following this contract
2. Create `instantiators/templates/{artifact}/` with 4 template files
3. Add entry to `registry.json` with `"instantiator": "{artifact}_instantiator.py"` + export_strategy fields
4. Add `"{artifact}": {...}` to `ARTIFACT_TYPES` in `config.py`
5. Write a `.rq` SPARQL rule in `RULES/` targeting the new `ioi-ext:{Artifact}Facet`
6. Run `python scripts/validate_registry.py` — must pass with zero errors
7. No changes to MapperRunner, ArtifactExporter, or any other plugin file needed

---

## 10. Template File Naming Convention

```
templates/
  {artifact}/
    {artifact}_template_base.json          ← @context + empty @graph
    {artifact}_template-source_file.json   ← source File node
    {artifact}_template-entry_clean.json   ← entry File + Facets (no timestamps filled)
    {artifact}_template-action.json        ← InvestigativeAction linking source → entry
```

All placeholders use `{UPPER_SNAKE_CASE}` and are replaced per-row via `copy.deepcopy()` + dict mutation (not string `.replace()`).

> Exception: office_xml currently uses string `.replace()` — migrate to dict mutation.
