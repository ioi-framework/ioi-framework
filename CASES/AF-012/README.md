# AF-012 — Office XML Metadata Timestamp Inconsistent with MFT

## Extracted Artifacts
- `$MFT` — parsed with MFTECmd, exported as CSV
- `password.docx` — opened as ZIP, `docProps/core.xml` extracted

## Mapped Artifacts
- MFT → `mft_instantiator.py` → `graphs/mft`
- Office XML → `office_xml_instantiator.py` → `graphs/office`

## IoI Signature
`ioi-ext:created` (Office XML core.xml) predates `ioi-ext:created0x10` (MFT $SI) for the same file — indicating the MFT timestamp was forged after document creation.

## Detection Rule
`RULES/temporal/IOI-012_office_mft_mismatch.rq`

Join key: normalized `observable:filePath` (forward-slash absolute path, case-insensitive).

## Verified Result (manual test)
| Field | Value |
|-------|-------|
| file | `password.docx` |
| filePath | `/Users/ktams/Desktop/Confidential/password.docx` |
| xmlCreated | `2025-03-04T01:09:00Z` |
| mftSiCreated | `2025-03-04T10:15:43Z` |
| gap | ~9 hours — timestomping confirmed |

## Notes
- MFT filePath is normalised by `mft_instantiator.py` (backslash → forward-slash, leading `/` ensured).
- For manual office graph generation, pass `--filepath` matching the MFT path or you will be prompted.
- IOI-012 uses `GROUP BY + MIN()` to deduplicate residual multi-entry MFT matches.
