# IoI Framework

Indicator of Inconsistency (IoI) — detects cross-artifact contradictions in digital
forensic investigations using CASE/UCO knowledge graphs and SPARQL signatures.

Documentation: https://ioi-framework.github.io

## What's in this repository

| Directory | Contents |
|-----------|----------|
| `CASES/AF-NNN/` | Ground truth, JSON-LD snippets, test graphs, mapping notes |
| `RULES/temporal/` | SPARQL rules for timestamp-based contradictions |
| `RULES/structural/` | SPARQL rules for structural contradictions (e.g. VSS purge) |
| `RULES/semantic/` | SPARQL rules for semantic contradictions (e.g. history wipe) |
| `instantiators/` | Python scripts: artifact parser CSV → CASE/UCO JSON-LD |
| `instantiators/templates/` | 4 JSON-LD templates per artifact type |
| `ontologies/` | `ioi-ext` custom vocabulary (Turtle) |
| `registry.json` | Artifact registry — facet names, field types, linked cases and rules |
| `playground/` | Browser-based graph explorer + SPARQL runner (no install needed) |
| `SCRIPTS/` | JSON-LD → N-Triples conversion utilities |

---

## Playground — no install needed

Open `playground/index.html` in a browser (or the hosted version at https://ioi-framework.github.io/playground/).

1. Drag any `CASES/AF-NNN/test/*.jsonld` file onto the drop zone, or paste a raw URL.
2. The graph IRI is **auto-detected from the filename** — the IRI input is editable
   if the detection is wrong. Prefix files with the case ID to get it right automatically:

   | Filename | Auto-detected graph IRI |
   |----------|------------------------|
   | `af011_lnk_repro_sample.jsonld` | `…/cases/AF-011/graphs/lnk` ✓ |
   | `lnk_repro_sample.jsonld` | `…/cases/AF-NEW/graphs/lnk` ✗ wrong case |
   | `mft_full_graph.jsonld` | `…/cases/AF-NEW/graphs/mft` ✓ new case default |

   **Rule of thumb:** prefix with `afNNN_` for a known case. `AF-NEW` is the correct
   fallback for new cases and works with MCP `scaffold_case` output.

3. Switch to **SPARQL**, paste any rule from `RULES/`, click **Run Query**.

**Playground loads named graphs only.** All rules in `RULES/` use `GRAPH <IRI>` clauses
and work as-is in the playground. Queries without `GRAPH` clauses return no results.

**Scale:** comfortable up to ~15k entries per file (~10 MB). Beyond that, use Virtuoso.

> **Quick test:** Load `CASES/AF-004/test/mft_test.jsonld` + `usn_test.jsonld`,
> click **IOI-004 VSS Purge** → expect 2 results.

---

## Virtuoso quick start

Full setup: https://ioi-framework.github.io/quickstart/

```bash
docker pull openlink/virtuoso-opensource-7:latest
docker run --name vos -d -e DBA_PASSWORD=dba \
  -p 8890:8890 -p 1111:1111 \
  openlink/virtuoso-opensource-7:latest
```

Convert JSON-LD to N-Triples and load:

```bash
# Convert (rdflib)
python SCRIPTS/convert_to_ntriples.py CASES/AF-004/test/mft_test.jsonld mft.nt
python SCRIPTS/convert_to_ntriples.py CASES/AF-004/test/usn_test.jsonld usn.nt

# Load into named graphs
docker cp mft.nt vos:/database/mft.nt
docker cp usn.nt vos:/database/usn.nt
docker exec vos isql 1111 dba dba \
  "exec=ld_dir('/database','mft.nt','https://ioi-framework.github.io/cases/AF-004/graphs/mft');"
docker exec vos isql 1111 dba dba \
  "exec=ld_dir('/database','usn.nt','https://ioi-framework.github.io/cases/AF-004/graphs/usn');"
docker exec vos isql 1111 dba dba "exec=rdf_loader_run();"
docker exec vos isql 1111 dba dba "exec=checkpoint;"

# Run IOI-004 via SPARQL HTTP endpoint — expect 2 rows
curl -s "http://localhost:8890/sparql" \
  --data-urlencode "query@RULES/structural/IOI-004_vss_traces_missing.rq" \
  -H "Accept: application/sparql-results+json"
```

---

## Running against your own data

1. Parse artifacts with [Eric Zimmermann tools](https://ericzimmerman.github.io/)
   (MFTECmd, EvtxECmd, LECmd, PECmd, Hindsight)
2. Run the instantiator:
   ```bash
   python instantiators/mft_instantiator.py mft.csv output.jsonld
   ```
3. **Playground**: drag `output.jsonld` in → rule runs immediately.
4. **Virtuoso**: convert to N-Triples → load into named graph → run the same rule.

For an artifact not yet in `registry.json`, use the
[IOI MCP Server](https://github.com/kismatkunwar89/ioi-mcp-server)
to auto-generate the instantiator, templates, and registry entry from your CSV.

---

## Writing and contributing SPARQL rules

### Rule form — one form, works everywhere

All rules use **named-graph `GRAPH <IRI>` clauses**. This is the single canonical form
that works in both the playground (oxigraph WASM) and Virtuoso production.

```sparql
PREFIX core:       <https://ontology.unifiedcyberontology.org/uco/core/>
PREFIX observable: <https://ontology.unifiedcyberontology.org/uco/observable/>
PREFIX ioi-ext:    <https://ioi-framework.github.io/ns/ioi-ext/>

SELECT ... WHERE {
  GRAPH <https://ioi-framework.github.io/cases/AF-NNN/graphs/mft> {
    ?entry a observable:File ; core:hasFacet ?facet .
    ?facet a ioi-ext:MftFacet ; ioi-ext:parentPath ?path .
  }
  ...
}
```

### Cross-artifact anti-joins — use FILTER NOT EXISTS

To detect that a record exists in one artifact but NOT in another:

```sparql
# ✓ Use this — works in playground (oxigraph) and Virtuoso
FILTER NOT EXISTS {
  GRAPH <https://ioi-framework.github.io/cases/AF-NNN/graphs/mft> {
    ?ff a observable:FileFacet ;
        observable:fileName ?mftFN .
    FILTER(UCASE(STR(?mftFN)) = UCASE(STR(?executableName)))
  }
}

# ✗ Avoid this — MINUS subquery is unreliable in both oxigraph and Virtuoso
# for cross-graph variable correlation
MINUS { SELECT ?executableName WHERE { GRAPH <...> { ... } GRAPH <...> { ... } } }
```

### What NOT to use

| Pattern | Why | Alternative |
|---------|-----|-------------|
| `bif:datediff(...)` | Virtuoso built-in — not portable to oxigraph | `FILTER(xsd:dateTime(?t1) < xsd:dateTime(?t2))` |
| `bif:contains(...)` | Virtuoso full-text only | `FILTER(CONTAINS(STR(?v), "term"))` |
| `MINUS` subquery cross-graph | Unreliable in both engines | `FILTER NOT EXISTS { GRAPH <IRI> { ... } }` |
| Queries without `GRAPH` | Returns 0 in playground (named-graph only) | Always use `GRAPH <IRI>` |

### Version header — required on every rule

```sparql
# rule_id:   IOI-NNN
# version:   1.0
# status:    Community
# category:  temporal | structural | semantic
# title:     Short description
# invariant: The expected property φ that is violated
# artifacts: Artifact1, Artifact2
# contributor: @handle
# added:     YYYY-MM-DD
# changed:   (none)
```

### Graph IRI convention

```
https://ioi-framework.github.io/cases/{CASE_ID}/graphs/{artifact_lower}

Examples:
  MFT for AF-004  →  https://ioi-framework.github.io/cases/AF-004/graphs/mft
  USN for AF-004  →  https://ioi-framework.github.io/cases/AF-004/graphs/usn
  Prefetch        →  https://ioi-framework.github.io/cases/AF-NEW/graphs/prefetch
```

### Testing before contributing

1. Load your test graphs in the playground — rule must fire with `fired: true`
2. Run the negative test — rule must NOT fire when the contradiction is absent
3. Check: `CASES/AF-NNN/ground_truth.md` describes the scenario correctly
4. Check: `mapping.md` field table is filled (not placeholder text)
5. CI runs automatically on PR — must pass all 3 checks

---

## Ground truth documents

Each `CASES/AF-NNN/ground_truth.md` describes the forensic scenario, expected
contradiction, and what a positive result means. Read it before running the rule.

---

## Namespace

```
PREFIX ioi-ext: <https://ioi-framework.github.io/ns/ioi-ext/>
PREFIX core:    <https://ontology.unifiedcyberontology.org/uco/core/>
PREFIX observable: <https://ontology.unifiedcyberontology.org/uco/observable/>
```

Full vocabulary: https://ioi-framework.github.io/ns/ioi-ext/

---

## Requirements

```
pip install rdflib case-utils
```
