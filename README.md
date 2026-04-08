# IoI Framework

Indicator of Inconsistency (IoI) framework for detecting cross-artifact contradictions in digital forensic investigations using CASE/UCO ontology graphs and SPARQL signatures.

Documentation: https://ioi-framework.github.io

## What's in this repository

| Directory | Contents |
|-----------|----------|
| `CASES/AF-NNN/` | Ground truth documents, JSON-LD snippets, test graphs |
| `RULES/temporal/` | SPARQL signatures for time-based contradictions |
| `RULES/structural/` | SPARQL signatures for structural contradictions (e.g. VSS purge) |
| `RULES/semantic/` | SPARQL signatures for semantic contradictions (e.g. browser history wipe) |
| `instantiators/` | Python scripts mapping artifact parser CSV → CASE/UCO JSON-LD |
| `instantiators/templates/` | JSON-LD templates for each artifact type |
| `ontologies/` | `ioi-ext` custom vocabulary (Turtle) |
| `registry.json` | Artifact registry — facet names, field types, cases and rules per artifact |
| `playground/` | Browser-based graph explorer + SPARQL runner (no install needed) |
| `SCRIPTS/` | Utility scripts (JSON-LD → N-Triples conversion) |

---

## Playground — no install needed

The fastest way to test any rule. Open `playground/index.html` in a browser (or visit the hosted version at https://ioi-framework.github.io/playground/).

1. Drag the test graphs from any `CASES/AF-NNN/test/` directory onto the drop zone — or paste a raw URL.
2. The graph IRI is auto-detected from the filename (`af004_mft.jsonld` → `…/cases/AF-004/graphs/mft`). It is editable if you need a different IRI.
3. Switch to the **SPARQL** tab and click an example button, or paste any rule from `RULES/`.
4. Click **Run Query** — results appear immediately using [oxigraph](https://github.com/oxigraph/oxigraph) WASM in your browser.

**Playground now supports named-graph queries directly.** The same canonical rule form with explicit `GRAPH <IRI>` clauses works in both the browser playground (oxigraph) and Virtuoso, so you do not need a separate default-graph-only version of each rule.

> **Quick test:** Load `CASES/AF-004/test/mft_test.jsonld` + `CASES/AF-004/test/usn_test.jsonld`, click **IOI-004 VSS Purge** → expect 2 results.

### Playground performance

| File size | Load time | Heap | Named-graph queries | Works |
|-----------|-----------|------|---------------------|-------|
| 1k / 0.7MB | 392ms | 25MB | ✓ `count=1,000` | ✓ |
| 10k / 6.7MB | 1.66s | 228MB | ✓ `count=10,000` | ✓ |
| 50k / 33.8MB | 8s | 1.1GB | ✓ `count=50,000` | ⚠️ borderline |

Named-graph `FILTER NOT EXISTS` across two graphs now works correctly in oxigraph. In testing, `SDELETE64.EXE` was flagged, `CMD.EXE` stayed clean, and the query completed in about 15ms.

---

## Virtuoso quick start

Full setup: https://ioi-framework.github.io/quickstart/

```bash
git clone https://github.com/kismatkunwar89/IoI-Framework.git
cd IoI-Framework
pip install -r requirements.txt
```

Pull and start Virtuoso:

```bash
docker pull openlink/virtuoso-opensource-7:latest
docker run --name vos -d -e DBA_PASSWORD=dba \
  -p 8890:8890 -p 1111:1111 \
  openlink/virtuoso-opensource-7:latest
```

Verify with the AF-004 test graphs:

```bash
# Load named graphs (N-Triples format)
docker cp CASES/AF-004/test/mft_test.nt vos:/database/mft_test.nt
docker cp CASES/AF-004/test/usn_test.nt vos:/database/usn_test.nt

docker exec vos isql 1111 dba dba \
  "exec=ld_dir('/database', 'mft_test.nt', 'https://ioi-framework.github.io/cases/AF-004/graphs/mft');"
docker exec vos isql 1111 dba dba \
  "exec=ld_dir('/database', 'usn_test.nt', 'https://ioi-framework.github.io/cases/AF-004/graphs/usn');"
docker exec vos isql 1111 dba dba "exec=rdf_loader_run();"
docker exec vos isql 1111 dba dba "exec=checkpoint;"

# Run IOI-004 — expect 2 rows
docker cp RULES/structural/IOI-004_vss_traces_missing.rq vos:/database/rule.rq
docker exec vos bash -lc "printf 'SPARQL\n'; cat /database/rule.rq; printf '\n;'" \
  | docker exec -i vos isql 1111 dba dba
```

---

## Running against your own data

1. Parse artifacts with [Eric Zimmermann tools](https://ericzimmerman.github.io/) (MFTECmd, EvtxECmd, LECmd, PECmd)
2. Run the appropriate instantiator:
   ```bash
   python instantiators/mft_instantiator.py mft.csv output.jsonld
   ```
3. **Playground**: drag `output.jsonld` into the playground and run any rule directly.
4. **Virtuoso**: convert to N-Triples, load into named graph, run rule with `GRAPH <...>` clauses.

For a new artifact type not yet in the registry, use the [IOI MCP Server](https://github.com/kismatkunwar89/ioi-mcp-server) which auto-generates the instantiator, templates, and registry entry from your CSV.

---

## SPARQL rules — two forms

Every rule in `RULES/` has a version header and works in both environments:

| Environment | Query form | How to use |
|-------------|-----------|------------|
| Playground (browser) | Named-graph — explicit `GRAPH <IRI>` clauses | Drag JSON-LD files → run the same rule used in production |
| Virtuoso (production) | Named-graph — explicit `GRAPH <IRI>` clauses | Load N-Triples → run rule with graph IRIs |

One canonical rule form works everywhere: explicit `GRAPH <IRI>` clauses for oxigraph and Virtuoso. `MINUS` subquery patterns are still unreliable across engines; `FILTER NOT EXISTS` is the recommended portable pattern.

---

## Ground truth documents

Each `CASES/AF-NNN/ground_truth.md` describes the forensic scenario, expected contradiction, and what a positive result means. Read it before running the rule.

## Namespace

```
PREFIX ioi-ext: <https://ioi-framework.github.io/ns/ioi-ext/>
```

Full vocabulary: https://ioi-framework.github.io/ns/ioi-ext/

## Requirements

```
pip install -r requirements.txt
```
