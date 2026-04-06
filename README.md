# IoI Framework

Indicator of Inconsistency (IoI) framework for detecting cross-artifact contradictions in digital forensic investigations using CASE/UCO ontology graphs and SPARQL signatures.

Documentation: https://ioi-framework.github.io

## What's in this repository

| Directory | Contents |
|-----------|----------|
| `CASES/AF-NNN/` | Ground truth documents (`ground_truth.md`), JSON-LD snippets, test graphs |
| `RULES/temporal/` | SPARQL signatures for time-based contradictions |
| `RULES/structural/` | SPARQL signatures for structural contradictions (e.g. VSS purge) |
| `RULES/semantic/` | SPARQL signatures for semantic contradictions (e.g. browser history wipe) |
| `instantiators/` | Python scripts mapping artifact parser CSV output to CASE/UCO JSON-LD |
| `instantiators/templates/` | JSON-LD templates for each artifact type |
| `ontologies/` | `ioi-ext` custom vocabulary (Turtle) |
| `SCRIPTS/` | Utility scripts (JSON-LD → N-Triples conversion) |

## Quick start

Full setup instructions: https://ioi-framework.github.io/quickstart/

```bash
git clone https://github.com/ioi-framework/ioi-framework.git
cd ioi-framework
pip install -r requirements.txt
```

Pull and start Virtuoso:

```bash
docker pull openlink/virtuoso-opensource-7:latest
docker run --name vos -d -e DBA_PASSWORD=dba \
  -p 8890:8890 -p 1111:1111 \
  openlink/virtuoso-opensource-7:latest
```

Verify your setup using the AF-004 test graphs (no real data needed):

```bash
# Copy test graphs into container
docker cp CASES/AF-004/test/mft_test.nt vos:/database/mft_test.nt
docker cp CASES/AF-004/test/usn_test.nt vos:/database/usn_test.nt

# Load named graphs
docker exec vos isql 1111 dba dba "exec=ld_dir('/database', 'mft_test.nt', 'http://example.org/mft_case4');"
docker exec vos isql 1111 dba dba "exec=ld_dir('/database', 'usn_test.nt', 'http://example.org/usn_case4');"
docker exec vos isql 1111 dba dba "exec=rdf_loader_run();"
docker exec vos isql 1111 dba dba "exec=checkpoint;"

# Run IOI-004 — expect 2 rows
docker cp RULES/structural/IOI-004_vss_traces_missing.rq vos:/database/rule.rq
docker exec vos bash -lc "printf 'SPARQL\n'; cat /database/rule.rq; printf '\n;'" \
  | docker exec -i vos isql 1111 dba dba
```

A result with 2 rows confirms your environment is working correctly.

## Running against your own data

1. Parse artifacts with [Eric Zimmermann tools](https://ericzimmerman.github.io/) (MFTECmd, EvtxECmd, LECmd)
2. Run the appropriate instantiator: `python instantiators/mft_instantiator.py <mft.csv> output.jsonld`
3. Convert to N-Triples: `python SCRIPTS/convert_to_ntriples.py output.jsonld output.nt`
4. Load into Virtuoso and run any rule from `RULES/`

See https://ioi-framework.github.io/quickstart/ for the full walkthrough.

## Ground truth documents

Each case in `CASES/AF-NNN/ground_truth.md` documents the forensic scenario, expected contradictions, and artifact sources. Read the ground truth document before running its rule to understand what a positive result means.

## Namespace

Custom properties use the `ioi-ext` vocabulary:

```
PREFIX ioi-ext: <https://ioi-framework.github.io/ns/ioi-ext/>
```

Full vocabulary reference: https://ioi-framework.github.io/ns/ioi-ext/

## Requirements

```
pip install -r requirements.txt
```
