# IoI Framework

Indicator of Inconsistency (IoI) framework for detecting cross-artifact contradictions in digital forensic investigations using CASE/UCO ontology graphs and SPARQL signatures.

Documentation: https://ioi-framework.github.io

## Structure

- `cases/` — ground truth documents, ontology mappings, JSON-LD snippets, and per-case instantiator data
- `instantiators/` — Python scripts that map artifact parser output to CASE/UCO JSON-LD graphs
- `rules/` — SPARQL IoI signatures organized by category (temporal, structural, semantic)
- `ontologies/` — custom extension vocabulary (`ioi-ext`) and property definitions
- `scripts/` — utility scripts (JSON-LD to N-Triples conversion)
- `engine/` — rule execution engine (in progress)

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

## Quick Start

See https://ioi-framework.github.io/quickstart/ for setup and execution instructions.
