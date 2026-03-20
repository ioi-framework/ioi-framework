# AF-012: Timestomping Detection via Office XML Metadata

## Summary

This test case demonstrates timestomping detection using Office XML metadata analysis. Office documents (docx, xlsx, pptx) are ZIP archives containing internal XML metadata (docProps/core.xml) that preserves the original creation timestamp. When MFT timestamps are forged using timestomping tools, the internal XML metadata remains unchanged, creating a detectable inconsistency.

## Impacted Artifacts and Attributes

- **$MFT** — Created0x10 ($STANDARD_INFORMATION) timestamp for Office document
- **Office XML metadata** — dcterms:created in docProps/core.xml

## Scenario Steps

### 1. Set Up
   - Created secret.docx on Windows system
   - Captured original timestamps of secret.docx

### 2. Tampering Process
   - Used timestomper.exe to forge timestamps of secret.docx
   - SetFileTime API modifies MFT $STANDARD_INFORMATION (0x10) timestamps
   - Internal Office XML metadata remains unmodified

### 3. Post-Tampering Evidence Collection
   - Extracted $MFT using forensic tools
   - Opened secret.docx as ZIP archive
   - Extracted docProps/core.xml for internal metadata
   - Compared XML dcterms:created with MFT timestamps

## Ground Truth Criteria

- Office XML metadata (dcterms:created) shows original creation time
- MFT $STANDARD_INFORMATION (0x10) shows forged (later) timestamp
- XML created time < MFT $SI created time indicates timestomping

## Dataset Reference

| Artifact Type | Description |
|---------------|-------------|
| MFT | Extracted $MFT (contains 0x10 timestamp for Office document) |
| Office XML | core.xml from docProps (contains dcterms:created metadata) |

## Inconsistency Summary

When timestomper.exe modifies secret.docx timestamps, it only changes the MFT $STANDARD_INFORMATION (0x10) attribute. The internal Office XML metadata in docProps/core.xml retains the original dcterms:created timestamp from when the document was actually created. The detection logic identifies timestomping when the XML metadata shows an earlier creation time than the MFT $SI timestamp.

## Pseudo-queries to Surface the Inconsistency

```sql
-- Step 1: Get Office XML metadata
FIND office_files
  RETURN filePath,
         dctermsCreated AS xmlCreated

-- Step 2: Get MFT timestamps for same file
FIND mft_entries WHERE mft_entries.filePath = office_files.filePath
  RETURN created0x10 AS mftSiCreated,
         created0x30 AS mftFnCreated

-- Step 3: Compare timestamps
-- Detection Rule
IF xmlCreated < mftSiCreated
THEN FLAG 'AF-012: Timestomping Detected via Office XML Metadata'
```

## Evidence Summary

- **Office XML (core.xml)**: dcterms:created = 2025-02-19T17:24 (original)
- **MFT $SI (0x10)**: Shows forged timestamp (2/16/2025 10:15)
- **Inconsistency**: XML metadata predates MFT timestamp, indicating forgery
