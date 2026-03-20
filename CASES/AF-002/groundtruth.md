# AF-002: Browser History Tampering via SQLite Manipulation

## Summary

This test demonstrates anti-forensics behavior through manipulation of browser history stored in Chrome's History SQLite database. The browser was used to visit websites, then the History file was edited using DB Browser for SQLite to remove traces of specific URLs (e.g., youtube.com). Despite the successful removal of records from the SQLite tables, low-level artifacts such as the $MFT and $UsnJrnl still reflect changes to the file, exposing forensic inconsistencies. This test case is used to evaluate the ability of forensic tools to detect mismatches between file content and execution traces.

## Impacted Artifacts and Attributes

- **History (SQLite DB)** — altered urls and visits tables
- **$MFT** — IndexedDB folder structure showing visited domains
- **$UsnJrnl:$J** — low-level file modification logs

## Scenario Steps

### 1. Set Up
   - Deployed Windows 10 VM and installed Google Chrome
   - Browsed to multiple websites (nytimes.com, youtube.com, reddit.com) using Chrome

### 2. Baseline Collection
   - Closed Chrome to flush memory to disk
   - Backed up the unmodified History SQLite file from:
     `C:\Users\resea\AppData\Local\Google\Chrome\User Data\Default\History`

### 3. Tampering Process
   - Opened the History file in DB Browser for SQLite
   - Deleted URL and visit entries related to youtube.com

### 4. Post-Tampering Evidence Collection
   - Collected both original and tampered versions of History
   - Extracted:
     - $MFT using Autopsy
     - $UsnJrnl:$J log

## Ground Truth Criteria

- $MFT shows IndexedDB folders for domains (e.g., youtube.com) that were visited
- Chrome's History DB no longer reflects visited sites like youtube.com
- $UsnJrnl shows History file was modified with tampering indicators (DataOverwrite, DataTruncation, DataExtend)

## Dataset Reference

| Artifact Type | Description |
|---------------|-------------|
| SQLite DB | History file (pre- and post-tampering) from Chrome |
| MFT | Extracted with MFTECmd (contains IndexedDB folder structure) |
| USN Journal | $UsnJrnl:$J log (contains sequence/timestamp of file updates) |

## Inconsistency Summary

The Chrome History SQLite database was deliberately modified to remove evidence of specific websites, but this did not erase related filesystem activity. The $MFT and $UsnJrnl show modifications to History even though the visit records no longer exist. This demonstrates how SQLite tampering leaves residual traces detectable by cross-artifact comparison, validating the effectiveness of correlating forensic data across layers.

## Pseudo-queries to Surface the Inconsistency

```sql
-- Step 1: Find domains in MFT IndexedDB folders
FIND mft_indexeddb WHERE mft_indexeddb.ParentPath CONTAINS 'IndexedDB'
  EXTRACT domain FROM ParentPath (e.g., 'https_www.youtube.com_0.indexeddb.leveldb' → 'youtube.com')
  RETURN domain, ParentPath

-- Step 2: Check if domain exists in History database
FIND history_urls WHERE history_urls.fullValue CONTAINS domain
  RETURN url_entry

-- Step 3: Check USN for History file tampering
FIND usn_entries WHERE usn_entries.fileName = 'History'
  AND usn_entries.updateReasons CONTAINS ('DataTruncation' OR 'DataOverwrite' OR 'DataExtend')
  RETURN updateReasons

-- Detection Rule
IF domain EXISTS IN mft_indexeddb
  AND domain NOT EXISTS IN history_urls
  AND usn_entries SHOWS tampering evidence
THEN FLAG 'AF-002: Selective Browser History Deletion Detected'
```

## Evidence Summary

- **$MFT evidence**: IndexedDB folders show youtube.com was visited (`https_www.youtube.com_0.indexeddb.leveldb`)
- **SQLite (post-tamper)**: History DB shows no youtube.com in urls/visits
- **$UsnJrnl:$J**: Shows History file modifications with tampering indicators (DataOverwrite, DataTruncation, DataExtend)
