# Contributing to the IoI Framework

Thank you for contributing. There are three levels of contribution depending on your technical background:

- **Level 1 (no code)** — Open a GitHub issue describing an anti-forensic case in plain language using the ground truth template. No SPARQL or JSON-LD required.
- **Level 2 (SPARQL / JSON-LD)** — Write a CASE/UCO template and IoI SPARQL rule from a validated ground truth document. This is the core community contribution focus.
- **Level 3 (instantiators)** — Write a Template Instantiator for a new artifact type or parser, or contribute a tool integration such as an Autopsy plugin.

All Level 2 and 3 contributions go through a Pull Request and are peer-reviewed before merging.

---

## Repository structure at a glance

```
_cases/               Case pages (one .md per scenario)
_rules/               IoI rule pages (one .md per rule)
_instantiators/       Template Instantiator pages (one .md per parser)
CASES/AF-NNN/         Artifact datasets (CSV/JSON/JSONLD per case)
RULES/{category}/     SPARQL .rq files organised by category
instantiators/        Python instantiator scripts
TEMPLATES/{subdir}/   Case-agnostic CASE/UCO JSON-LD templates
ontologies/           ioi-ext.ttl namespace definitions
```

---

## What can I contribute?

| Contribution type      | Files to add                                                              |
|------------------------|---------------------------------------------------------------------------|
| New anti-forensic case | `_cases/af-NNN.md` + `CASES/AF-NNN/ground_truth.md`                       |
| New IoI rule           | `_rules/ioi-NNN.md` + `RULES/{category}/IOI-NNN_name.rq`                 |
| New instantiator       | `_instantiators/inst-NNN.md` + `instantiators/NNN_instantiator.py`       |
| New CASE/UCO template  | `TEMPLATES/{artifact_type}/` subfolder                                    |
| ioi-ext property       | Edit `ontologies/ioi-ext.ttl` + update documentation                     |
| Documentation fix      | Edit site pages directly                                                  |

You can contribute one type in a single PR, or bundle a case + its rule together — that is encouraged.

---

## Case front-matter schema (`_cases/af-NNN.md`)

Every case file **must** include all required fields. Optional fields should be included where applicable.

```yaml
---
# ── Required ──────────────────────────────────────────────
case_id:      AF-NNN           # Sequential ID. Check existing cases first.
title:        "Short descriptive title"
category:     Temporal         # Temporal | Structural | Semantic
status:       Community        # Community | Validated | Deprecated
description:  "One sentence describing the anti-forensic action and contradiction signal."
artifacts:                     # List of artifact types involved (use standard names below)
  - $MFT
  - $UsnJrnl
contributor:  "@github-handle"
date_added:   YYYY-MM-DD

# ── Optional ───────────────────────────────────────────────
rule_link:    /rules/ioi-NNN/  # Link to corresponding IoI rule page
tags:                          # Free-form tags for filtering
  - timestamp-manipulation
os:           Windows 10       # Target OS and version
tools_used:                    # Anti-forensic tools used in scenario
  - timestomper.exe
---
```

**Standard artifact names** (use these exactly for consistent filtering):
`$MFT`, `$UsnJrnl`, `$LogFile`, `Security.evtx`, `System.evtx`, `LNK`, `Prefetch`, `Chrome History`, `Firefox History`, `Registry`, `Office core.xml`, `IndexedDB`, `SQLite DB`

---

## IoI rule front-matter schema (`_rules/ioi-NNN.md`)

```yaml
---
# ── Required ──────────────────────────────────────────────
rule_id:      IOI-NNN
title:        "Short descriptive title"
category:     Temporal         # Temporal | Structural | Semantic
status:       Community        # Community | Validated | Deprecated
description:  "One sentence describing what the rule detects."
artifacts:
  - $MFT
  - LNK
invariant:    "Human-readable statement of the expected invariant φ"
sparql_file:  ioi-NNN.rq       # filename under rules/sparql/
contributor:  "@github-handle"
date_added:   YYYY-MM-DD

# ── Optional ───────────────────────────────────────────────
case_link:    /cases/af-NNN/
version:      "1.0"
tested_on:
  - "Virtuoso 7.2"
  - "Apache Jena Fuseki 4.x"
notes: ""
---
```

---

## Instantiator front-matter schema (`_instantiators/inst-NNN.md`)

```yaml
---
# ── Required ──────────────────────────────────────────────
inst_id:      INST-NNN
title:        "Artifact type — e.g. NTFS $MFT Instantiator"
artifact:     $MFT              # Single artifact type this parser handles
parser_tool:  MFTECmd           # Upstream parser tool
input_format: CSV               # CSV | JSON | JSONL | SQLite | XML
output:       JSON-LD           # Always JSON-LD
template:     mft               # Subdirectory under TEMPLATES/
script:       mft_instantiator.py  # Script under instantiators/
contributor:  "@github-handle"
date_added:   YYYY-MM-DD

# ── Optional ───────────────────────────────────────────────
status:       Community        # Community | Validated | Deprecated
python_version: "3.9+"
dependencies:
  - rdflib>=6.0
notes: ""
---
```

---

## Step-by-step: submitting a PR

### 1. Fork and branch

```bash
git clone https://github.com/ioi-framework/ioi-framework.git
cd ioi-framework
git checkout -b add/your-scenario-name
```

Use branch naming convention: `add/short-name`, `fix/...`, `docs/...`

### 2. Pick an ID

Use a placeholder ID (e.g. `AF-NEW`) if unsure — maintainers assign the canonical sequential ID during review. Numbering is flexible and finalized at merge time.

### 3. Add your files

Follow the schemas above. The minimum required files are:

```
CASES/AF-NEW/
  ground_truth.md          # describes the case
  test/
    <artifact>_test.jsonld # synthetic graph that makes the rule fire
RULES/{category}/
  IOI-NEW_your_rule.rq     # SPARQL signature
```

**Building the test graph** — the `test/` JSON-LD is a small synthetic knowledge graph (5–10 records) with fabricated values that trigger the contradiction. No real case data. You only need to include the fields your SPARQL actually touches — if your rule only checks `observable:fileName` and `ioi-ext:parentPath`, those are the only two fields needed. Omit everything else.

To get the correct node/facet structure for the fields you do need:

- **If an existing case uses the same artifact** (e.g. `$MFT`, `$UsnJrnl`, `LNK`) — copy the relevant fields from that case's `CASES/AF-NNN/snippets/` files, replace values with synthetic ones.
- **If it is a new artifact type** — use `TEMPLATES/{artifact_type}/` as the structure reference.

The test graph must use the prefixes `core:`, `observable:`, `ioi-ext:` with their real URIs, and load into named graphs matching the IRIs in your `.rq` file.

Then run the local validation script before pushing:

```bash
python scripts/validate_frontmatter.py
```

### 4. Open the Pull Request

Use the PR template (auto-loaded when you open a PR). Fill out every checkbox. Assign at least one reviewer from the maintainer team.

### 5. Review process

- Automated CI checks run first (schema validation, broken link check)
- A maintainer or community peer reviewer will review within 14 days
- Address any requested changes on the same branch
- Once approved, a maintainer merges and the site deploys automatically

---

## Status lifecycle

| Status      | Meaning                                                             |
|-------------|---------------------------------------------------------------------|
| `Community` | Contributed by a community member, not independently validated      |
| `Validated` | Independently reproduced or reviewed by the core maintainer team    |
| `Deprecated`| Superseded, known-broken, or no longer applicable                   |

To request promotion from `Community` to `Validated`, open a PR adding a `validation_note` field to the front matter and tagging a maintainer.

---

## Code of conduct

Be respectful. Forensic community contributions are expected to be grounded in evidence and reproducible. Do not submit signatures based on theoretical manipulation only — provide a ground-truth specification and, where possible, a paired dataset.
