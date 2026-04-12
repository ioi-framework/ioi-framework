# Mapping Notes (AF-012)

## Purpose
Documents how raw artifact fields were mapped into CASE/UCO JSON-LD for timestomping detection.

## Input Artifacts

| Artifact | Tool | Source File |
|----------|------|-------------|
| $MFT | MFTECmd (Eric Zimmermann) | CSV export |
| Office XML | `office_xml_instantiator.py` | `password.docx` (opened as ZIP) |

## Mapper Scripts

| Artifact | Script |
|----------|--------|
| MFT | `instantiators/mft_instantiator.py` |
| Office XML | `instantiators/office_xml_instantiator.py` |

## Field-to-Ontology Mapping

| Source Field | JSON-LD Path | Facet/Class | Notes |
|---|---|---|---|
| MFT `ParentPath` + `FileName` | `observable:filePath` | `ioi-ext:MftFacet` via `observable:FileFacet` | Normalised: backslash→`/`, leading `/` ensured |
| MFT `Created0x10` | `ioi-ext:created0x10` | `ioi-ext:MftFacet` | $STANDARD_INFORMATION created timestamp |
| MFT `Created0x30` | `ioi-ext:created0x30` | `ioi-ext:MftFacet` | $FILE_NAME created timestamp |
| `core.xml` `dcterms:created` | `ioi-ext:created` | `ioi-ext:OfficeXMLFacet` | Original document creation time |
| `core.xml` `dcterms:modified` | `ioi-ext:modified` | `ioi-ext:OfficeXMLFacet` | |
| `core.xml` `dc:creator` | `ioi-ext:creator` | `ioi-ext:OfficeXMLFacet` | |
| File path on image | `observable:filePath` | `observable:FileFacet` (office graph) | Join key for IOI-012 — must match MFT filePath |

## IOI-EXT Extensions Used
- `ioi-ext:MftFacet` — `created0x10`, `created0x30`
- `ioi-ext:OfficeXMLFacet` — `created`, `modified`, `creator`, `lastModifiedBy`

## Notes / Assumptions
- MFT filePath is normalised to forward-slash absolute path (e.g. `/Users/ktams/Desktop/Confidential/password.docx`).
- Office XML filePath must match the MFT filePath exactly (case-insensitive) for IOI-012 join to fire.
- In Autopsy mode, both paths come from `AbstractFile` — match is automatic.
- In manual mode, supply `--filepath` to `office_xml_instantiator.py` with the path as it appears in the MFT CSV.
- IOI-012 uses `GROUP BY + MIN(?mftSiCreated)` to deduplicate cases where multiple MFT entries share the same path.
