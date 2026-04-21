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

Virtuoso is the triplestore that holds the knowledge graphs. It runs in Docker.

### 1. Install Docker

Download Docker Desktop from https://www.docker.com/products/docker-desktop/ and make sure it is running.

### 2. Start Virtuoso

```bash
docker run --name vos -d   -e DBA_PASSWORD=dba   -p 8890:8890 -p 1111:1111   openlink/virtuoso-opensource-7:latest

docker exec vos isql 1111 dba dba "exec=select 1;"
```

Verify it started:
```bash
docker ps | grep vos
```

You should see the `vos` container listed as running. You can also open http://localhost:8890 in a browser to confirm.

### 3. Convert a test JSON-LD file to N-Triples

```bash
python3 SCRIPTS/convert_to_ntriples.py CASES/AF-004/test/mft_test.jsonld mft.nt
python3 SCRIPTS/convert_to_ntriples.py CASES/AF-004/test/usn_test.jsonld usn.nt
```

> **Note:** The script tries Node.js (`jsonld` package) first, then falls back to `rdflib`. If you don't have Node.js, install rdflib: `pip3 install rdflib`

### 4. Load N-Triples into Virtuoso

Virtuoso only reads files from directories listed in its config. The safe path is `/usr/share/proj/` inside the container. Copy your files there first, then load:

```bash
# Step 1 — copy files into the container
docker cp mft.nt vos:/usr/share/proj/mft.nt
docker cp usn.nt vos:/usr/share/proj/usn.nt

# Step 2 — load into named graphs (paste this whole block as one command)
docker exec -i vos isql 1111 dba dba <<'EOF'
DB.DBA.TTLP_MT(file_to_string_output('/usr/share/proj/mft.nt'), '', 'https://ioi-framework.github.io/cases/AF-004/graphs/mft', 512);
DB.DBA.TTLP_MT(file_to_string_output('/usr/share/proj/usn.nt'), '', 'https://ioi-framework.github.io/cases/AF-004/graphs/usn', 512);
EOF
```

You should see `Done.` for each file. If you see an access denied error, make sure you copied to `/usr/share/proj/` and not `/database/`.

### 5. Run a detection rule

```bash
docker cp RULES/structural/IOI-004_vss_traces_missing.rq vos:/database/rule.rq
docker exec vos bash -lc "printf 'SPARQL\n'; sed '/^#/d' /database/rule.rq; printf '\n;'"   | docker exec -i vos isql 1111 dba dba
```

Expected: 2 results for the AF-004 test data.

---

## Running against your own data

> **Want to reproduce the published cases directly?** Download a per-case reproducibility bundle from [Artifacts & Datasets](https://ioi-framework.github.io/artifacts/) and then follow the steps in [Executing Rules](https://ioi-framework.github.io/executerules/). These bundles include the raw artifacts and parser outputs needed to reproduce each case.

1. Parse your disk image artifacts with [Eric Zimmerman tools](https://ericzimmerman.github.io/)
   — `MFTECmd` for `$MFT`, `LECmd` for `.lnk`, `EvtxECmd` for `.evtx`

2. Run the instantiator for your artifact type:
   ```bash
   python3 instantiators/mft_instantiator.py mft.csv output.jsonld
   ```

3. Choose how to run the detection rule:
   - **Playground** (quick, no install): drag `output.jsonld` into `playground/index.html` → paste rule → Run
   - **Virtuoso** (full scale): follow steps 3–5 above with your own files

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
