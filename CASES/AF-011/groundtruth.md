# AF-011: Timestomping Detection via LNK File Analysis

## Summary

This test case demonstrates timestomping detection using LNK (shortcut) file analysis. When a file is timestomped using tools like timestomper.exe, the MFT $STANDARD_INFORMATION (0x10) timestamps are modified. However, LNK shortcut files preserve the original target file timestamps from when the shortcut was created. By comparing LNK timestamps with current MFT timestamps, timestomping can be detected.

## Impacted Artifacts and Attributes

- **$MFT** — Created0x10 ($STANDARD_INFORMATION) and Created0x30 ($FILE_NAME) timestamps
- **LNK files** — Target file creation time preserved in shortcut metadata

## Scenario Steps

### 1. Set Up
   - Created secret.docx on Windows system
   - Created shortcut (secret.lnk) pointing to secret.docx
   - Captured original timestamps of secret.docx

### 2. Tampering Process
   - Used timestomper.exe to forge timestamps of secret.docx
   - SetFileTime API modifies MFT $STANDARD_INFORMATION (0x10) timestamps
   - $FILE_NAME (0x30) timestamps remain unchanged

### 3. Post-Tampering Evidence Collection
   - Extracted $MFT using forensic tools
   - Extracted secret.lnk shortcut file
   - Compared LNK target timestamps with MFT timestamps

## Ground Truth Criteria

- LNK shortcut creation time matches MFT $FILE_NAME (0x30) timestamp (both preserve original time)
- MFT $STANDARD_INFORMATION (0x10) timestamp differs from LNK and $FILE_NAME timestamps
- MFT entry number links LNK target to MFT record

## Dataset Reference

| Artifact Type | Description |
|---------------|-------------|
| MFT | Extracted $MFT (contains 0x10 and 0x30 timestamps for target file) |
| LNK | Shortcut file (contains preserved target creation time) |

## Inconsistency Summary

When timestomper.exe modifies secret.docx timestamps, it only changes the MFT $STANDARD_INFORMATION (0x10) attribute. The LNK shortcut file retains the original target creation time from when the shortcut was created. Additionally, the $FILE_NAME (0x30) attribute in MFT preserves the original timestamp. The detection logic identifies timestomping when: LNK shortcut time ≈ MFT $FN (0x30), but MFT $SI (0x10) differs.

## Pseudo-queries to Surface the Inconsistency

```sql
-- Step 1: Get LNK file info with target timestamps
FIND lnk_files
  RETURN targetMftEntryNumber,
         targetCreatedTime,
         shortcutCreatedTime

-- Step 2: Get MFT timestamps for same entry number
FIND mft_entries WHERE mft_entries.entryNumber = lnk_files.targetMftEntryNumber
  RETURN created0x10 AS mftSiCreated,
         created0x30 AS mftFnCreated

-- Step 3: Compare timestamps
-- Detection Rule
IF lnkShortcutCreated != mftSiCreated
  AND truncate_to_seconds(lnkShortcutCreated) = truncate_to_seconds(mftFnCreated)
THEN FLAG 'AF-011: Timestomping Detected via LNK Analysis'
```

## Evidence Summary

- **LNK file**: secret.lnk preserves original target creation time (2/19/2025 17:24)
- **MFT $SI (0x10)**: Shows forged timestamp (2/16/2025 10:15)
- **MFT $FN (0x30)**: Preserves original timestamp matching LNK
