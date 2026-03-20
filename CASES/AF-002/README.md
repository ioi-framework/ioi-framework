# AF-002 — Selective Browser History Deletion

## Scenario Summary
This case models selective deletion of Chrome History entries where filesystem traces (MFT + IndexedDB cache) remain but browser history records are missing, with corroborating USN evidence of History file modification.

## Artifacts Used
- **MFT** (MFTECmd) — IndexedDB paths for cached domains
- **Chrome History** (SQLite export)
- **USN Journal** (MFTECmd $J)

## IoI Signature
Primary rule:
- `RULES/AF-002.rq`

Minicase rule (stable on snippets):
- `RULES/AF-002-grouped.rq`

## Graphs
- `http://example.org/mft_case2`
- `http://example.org/history_case2`
- `http://example.org/usn_case2`

## Expected Detection
- Domain present in IndexedDB but missing from History, with USN evidence of History file modification.

## Files in This Case
- `mapping.md` — field → ontology mapping notes
- `groundtruth.md` — scenario ground truth and invariant/violation
- `snippets/` — JSON‑LD snippets used for documentation/tests

