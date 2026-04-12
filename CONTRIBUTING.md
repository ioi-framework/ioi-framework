# Contributing to the IoI Framework

There are three levels of contribution depending on your background:

- **Level 1 (no code)** — Open a GitHub issue describing an anti-forensic case in plain language using the ground truth template. No SPARQL or JSON-LD required.
- **Level 2 (SPARQL)** — Write an IoI SPARQL rule for a validated ground truth case. Core community contribution.
- **Level 3 (instantiators)** — Write a new artifact instantiator, templates, and registry entry for a new artifact type.

All contributions go through a Pull Request and are peer-reviewed before merging.

---

## Repository Structure

```
CASES/AF-NNN/               Case datasets, ground truth, test graphs
RULES/{temporal|structural|semantic}/
                            SPARQL .rq detection rules
instantiators/              Python instantiator scripts (one per artifact type)
instantiators/templates/    JSON-LD template files (4 per artifact type)
ontologies/                 ioi-ext.ttl — custom vocabulary
registry.json               Artifact registry — single source of truth
                            (facet names, field types, export strategy, graph segment)
playground/                 Browser SPARQL explorer
SCRIPTS/                    JSON-LD → N-Triples conversion utilities
scripts/                    Validation scripts (CI)
```

---

## What Can I Contribute?

| Contribution | Files to add or modify |
|---|---|
| New anti-forensic case | `CASES/AF-NNN/ground_truth.md` + `CASES/AF-NNN/test/*.jsonld` |
| New IoI rule (existing artifact) | `RULES/{category}/IOI-NNN_name.rq` |
| New artifact type | `instantiators/{artifact}_instantiator.py` + `instantiators/templates/{artifact}/` + `registry.json` entry + `RULES/` rule |
| ioi-ext vocabulary | `ontologies/ioi-ext.ttl` |

---

## Adding a New SPARQL Rule (Level 2)

### Required header on every `.rq` file

```sparql
# rule_id:    IOI-NNN
# version:    1.0
# status:     Community
# category:   temporal | structural | semantic
# title:      Short description
# invariant:  The expected property φ that this rule enforces
# artifacts:  mft, usn        ← lowercase artifact_type keys from registry.json
# contributor: @github-handle
# added:      YYYY-MM-DD
# changed:    (none)
```

### Rule versioning policy (immutable logic)

- Rule logic **never changes** once published — only the version number updates
- `1.0 → 1.1` — additive change (new `SELECT` variable, comment fix): OK
- `1.0 → 2.0` — logic change: archive old version to `RULES/archive/`, publish new

### Always use `GRAPH <IRI>` clauses

Named-graph form works in the playground (oxigraph) AND Virtuoso. Never write default-graph queries.

```sparql
PREFIX core:       <https://ontology.unifiedcyberontology.org/uco/core/>
PREFIX observable: <https://ontology.unifiedcyberontology.org/uco/observable/>
PREFIX ioi-ext:    <https://ioi-framework.github.io/ns/ioi-ext/>

SELECT ?entry ?fileName WHERE {
  GRAPH <https://ioi-framework.github.io/cases/AF-NNN/graphs/mft> {
    ?entry a observable:File ;
           core:hasFacet ?facet .
    ?facet a ioi-ext:MftFacet ;
           observable:fileName ?fileName .
  }
}
```

### Graph IRI convention

```
https://ioi-framework.github.io/cases/{case_id}/graphs/{graph_segment}
```

Graph segments per artifact (from `registry.json`):

| artifact_type | graph_segment |
|---|---|
| `mft` | `mft` |
| `usn` | `usn` |
| `lnk` | `lnk` |
| `evtx` | `evtx` |
| `history` | `history` |
| `office_xml` | `office` |

### Cross-artifact anti-joins — use `FILTER NOT EXISTS`

```sparql
# ✅ Works in playground (oxigraph) and Virtuoso
FILTER NOT EXISTS {
  GRAPH <https://ioi-framework.github.io/cases/AF-NNN/graphs/mft> {
    ?ff a observable:FileFacet ;
        observable:fileName ?mftFN .
    FILTER(UCASE(STR(?mftFN)) = UCASE(STR(?executableName)))
  }
}

# ❌ Avoid — MINUS subquery unreliable in both engines for cross-graph correlation
```

### Test before submitting

1. Load test graphs in the playground — rule must fire (`fired: true`)
2. Run negative test — rule must NOT fire when contradiction is absent
3. Run local validation:

```bash
python scripts/validate_sparql.py
python scripts/validate_registry.py
```

---

## Adding a New Artifact Type (Level 3)

Add **4 things** — all in this repo:

### 1. Registry entry (`registry.json`)

Add an entry under `"artifacts"`. Key must be the lowercase `artifact_type` identifier.

```json
"prefetch": {
  "artifact_type":       "prefetch",
  "graph_segment":       "prefetch",
  "graph_segment_aliases": [],
  "artifact_id":         "ART-007",
  "full_name":           "Windows Prefetch (.pf)",
  "parser_tool":         "PECmd",
  "input_format":        "CSV",
  "facet":               "ioi-ext:PrefetchFacet",
  "instantiator":        "instantiators/prefetch_instantiator.py",
  "template_dir":        "instantiators/templates/prefetch/",
  "status":              "community",
  "cases":               [],
  "rules":               [],
  "export_strategy":     "binary_tool",
  "file_patterns":       ["%.pf"],
  "fallback_patterns":   [],
  "parent_path_filter":  "Prefetch",
  "tool_key":            "PECMD_PATH",
  "tool_arg_mode":       "single_file",
  "tool_output_flag":    "--csv",
  "tool_output_ext":     ".csv",
  "tool_output_format":  "csv",
  "max_files":           0,
  "cleanup_raw":         true
}
```

### 2. Instantiator script

Follow the **Instantiator Contract** exactly — see [`INSTANTIATOR_CONTRACT.md`](./INSTANTIATOR_CONTRACT.md).

Key rules:
- CLI: `python3 {artifact}_instantiator.py <input_file> <output_file>` — always 2 positional args
- Entry point: `fill_template_from_data(input_path, output_path)`
- Use `argparse` — never raw `sys.argv`
- Templates loaded via `Path(__file__).parent / 'templates' / '{artifact}'`
- Node IDs: `kb:{artifact}--{uuid}` pattern
- Namespaces: `core:hasFacet` (not `uco-core:`), no `example.org`

### 3. Templates (4 files)

```
instantiators/templates/{artifact}/
  {artifact}_template_base.json         ← @context + empty @graph
  {artifact}_template-source_file.json  ← source File node
  {artifact}_template-entry_clean.json  ← entry File + Facets
  {artifact}_template-action.json       ← InvestigativeAction
```

All `@context` blocks must include:
```json
{
  "kb":         "https://ioi-framework.github.io/kb/",
  "ioi-ext":    "https://ioi-framework.github.io/ns/ioi-ext/",
  "core":       "https://ontology.unifiedcyberontology.org/uco/core/",
  "observable": "https://ontology.unifiedcyberontology.org/uco/observable/",
  "uco-action": "https://ontology.unifiedcyberontology.org/uco/action/",
  "xsd":        "http://www.w3.org/2001/XMLSchema#"
}
```

No `example.org` anywhere.

### 4. SPARQL rule

Add `RULES/{category}/IOI-NNN_{artifact}_name.rq` following the rule contract above.

### Validate your PR

```bash
python scripts/validate_registry.py   # registry.json schema check
python scripts/validate_sparql.py     # rule header + syntax check
python scripts/validate_jsonld.py     # template @context check
```

---

## Namespace Reference

```
kb:         https://ioi-framework.github.io/kb/
ioi-ext:    https://ioi-framework.github.io/ns/ioi-ext/
core:       https://ontology.unifiedcyberontology.org/uco/core/
observable: https://ontology.unifiedcyberontology.org/uco/observable/
uco-action: https://ontology.unifiedcyberontology.org/uco/action/
xsd:        http://www.w3.org/2001/XMLSchema#
```

---

## PR Process

1. Fork → branch (`add/short-name`, `fix/...`, `docs/...`)
2. Add files following the contracts above
3. Run validation scripts locally — must pass
4. Open PR using the PR template, fill all checkboxes
5. CI runs automatically — must pass all checks
6. Maintainer reviews within 14 days

---

## Code of Conduct

Be respectful. Contributions must be grounded in reproducible forensic evidence. Do not submit signatures based on theory only — provide a ground truth specification and, where possible, a test dataset.
