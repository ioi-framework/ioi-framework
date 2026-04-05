# AF-004: Volume Shadow Copy Deletion Detection

## Summary

This test case models an anti-forensic tactic where Volume Shadow Copies (VSCs) are deleted to eliminate system restore points that could reveal prior system states. The detection identifies when VSS infrastructure files exist in the System Volume Information folder, but the corresponding GUID directories (which contain actual shadow copy data) have been deleted. USN Journal entries confirm the deletion activity. This creates a forensic inconsistency: VSS infrastructure remains but recovery data is missing.

## Impacted Artifacts and Attributes

- **$MFT** — VSS infrastructure files and GUID directory presence/absence
- **$UsnJrnl:$J** — GUID directory deletion events

## Scenario Steps

### 1. Set Up
   - Launched Windows 10 Pro x64 VM with System Protection and VSS configured
   - Used `wmic shadowcopy call create Volume="C:\"` to generate a restore point

### 2. Tampering Process
   - Deleted all shadow copies with: `vssadmin delete shadows /all /quiet`

### 3. Post-Tampering Evidence Collection
   - Extracted $MFT and $UsnJrnl:$J from NTFS volume

## Ground Truth Criteria

- $MFT shows VSS infrastructure files exist (tracking.log, IndexerVolumeGuid, _OnDiskSnapshotProp) in System Volume Information
- $MFT shows GUID directories are missing (no {XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX} folders)
- $UsnJrnl shows GUID directory deletions with indicators (FileDelete, FileDeleteClose, DataTruncation)

## Dataset Reference

| Artifact Type | Description |
|---------------|-------------|
| MFT | Extracted with MFTECmd (contains VSS infrastructure and GUID directory status) |
| USN Journal | $UsnJrnl:$J log (contains GUID deletion events) |

## Inconsistency Summary

VSS infrastructure files (tracking.log, IndexerVolumeGuid, _OnDiskSnapshotProp) exist in System Volume Information, indicating VSS was configured. However, the GUID directories that contain actual shadow copy data are missing from MFT. USN Journal confirms these GUID directories were deleted. This demonstrates anti-forensic VSS purge: the attacker deleted recovery points while leaving infrastructure traces behind.

## Pseudo-queries to Surface the Inconsistency

```sql
-- Step 1: Find VSS infrastructure files in MFT
FIND mft_vss WHERE mft_vss.ParentPath CONTAINS 'System Volume Information'
  AND mft_vss.FileName CONTAINS ('tracking.log' OR 'IndexerVolumeGuid' OR '_OnDiskSnapshotProp')
  RETURN FileName AS vss_infrastructure

-- Step 2: Check if GUID directories exist in MFT
FIND mft_guid WHERE mft_guid.ParentPath CONTAINS 'System Volume Information'
  AND mft_guid.FileName MATCHES '{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}' pattern
  AND mft_guid.isDirectory = true
  RETURN FileName AS guid_directory

-- Step 3: Find USN evidence of GUID deletion
FIND usn_entries WHERE usn_entries.FileName MATCHES GUID pattern
  AND usn_entries.updateReasons CONTAINS ('FileDelete' OR 'FileDeleteClose' OR 'DataTruncation')
  RETURN FileName AS deleted_guid, updateReasons AS usn_evidence

-- Detection Rule
IF vss_infrastructure EXISTS IN mft_vss
  AND guid_directory NOT EXISTS IN mft_guid
  AND deleted_guid EXISTS IN usn_entries
THEN FLAG 'AF-004: Volume Shadow Copy Purge Detected'
```

## Evidence Summary

- **$MFT evidence**: VSS infrastructure files present (tracking.log, IndexerVolumeGuid, _OnDiskSnapshotProp)
- **$MFT evidence**: GUID directories missing (no {GUID} folders in System Volume Information)
- **$UsnJrnl:$J**: Shows GUID directory deletions with FileDelete/FileDeleteClose/DataTruncation indicators
