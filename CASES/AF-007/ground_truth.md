# AF-007: Event Log Clearing and Partial Repopulation via Wevtutil

## Summary

This test case demonstrates an anti-forensic technique where the Windows Security Event Log is cleared using the built-in wevtutil command. After the clearing, normal system usage (logon and reboot) generates new records, giving the appearance of continuity in the log. Attackers may rely on this method to erase incriminating entries and depend on legitimate system events written after the clear to mask the manipulation.

## Impacted Artifacts and Attributes

- **Security.evtx** — Event 1102 (Audit Log Cleared) records the clearing action
- **$UsnJrnl:$J** — DataTruncation entries for Security.evtx file

## Scenario Steps

### 1. Set Up
   - Launched a Windows 10 Pro x64 VirtualBox VM (UEFI enabled)
   - Identified active logs: Security.evtx, System.evtx, Application.evtx

### 2. Tampering Process
   - Cleared Security log using: `wevtutil cl Security`
   - Verified Security log was empty in Event Viewer

### 3. Post-Tampering Activity
   - Performed normal actions to repopulate logs:
     - Logged off and back in, generating a 4624 (Successful Logon)
     - Rebooted VM, generating a 6005 (Event Log Service Started) in System log

### 4. Evidence Collection
   - Exported logs from Event Viewer:
     - Security.evtx (cleared + repopulated)
     - System.evtx and Application.evtx (unaltered for comparison)
   - Powered off VM and converted disk to raw image:
     `VBoxManage clonehd "Case7-disk1.vdi" "AF007_Case.img" --format RAW`
   - Loaded image into Autopsy and extracted artifacts:
     - $UsnJrnl:$J → usn_journal.raw
     - Security.evtx
   - Parsed with MFTECmd:
     `MFTECmd.exe -f usn_journal.raw --csv af007_usn.csv`

## Ground Truth Criteria

- Security.evtx contains Event ID 1102 (Audit Log Cleared) from Security channel
- $UsnJrnl shows DataTruncation for files containing "Security" in the filename

## Dataset Reference

| Artifact Type | Description |
|---------------|-------------|
| Event Log | Security.evtx (contains Event 1102 log clearing record) |
| USN Journal | $UsnJrnl:$J log (contains DataTruncation entries for Security.evtx) |

## Inconsistency Summary

The clearing of Security.evtx is recorded by Windows itself through Event ID 1102 in the Security channel. Additionally, the $UsnJrnl shows DataTruncation activity for the Security.evtx file, indicating file truncation occurred. Subsequent real events (logon, reboot) reappear in the log, creating an illusion of normal continuity. However, the presence of Event 1102 combined with USN DataTruncation evidence exposes the log clearing activity.

## Pseudo-queries to Surface the Inconsistency

```sql
-- Step 1: Find Event 1102 (Log Clearing) in Security channel
FIND event_records WHERE event_records.eventID = "1102"
  AND event_records.channel = "Security"
  RETURN startTime AS clear_time, eventRecordText AS details

-- Step 2: Find USN DataTruncation for Security files
FIND usn_entries WHERE usn_entries.fileName CONTAINS "Security"
  AND usn_entries.updateReasons CONTAINS "DataTruncation"
  RETURN fileName, updateReasons, updateTimestamp

-- Detection Rule
IF event_1102 EXISTS IN event_records (channel = "Security")
  OR usn_entries SHOWS DataTruncation for Security files
THEN FLAG 'AF-007: Security Event Log Clearing Detected'
```

## Evidence Summary

- **Security.evtx**: Event ID 1102 records that the audit log was cleared
- **$UsnJrnl:$J**: Shows DataTruncation for Security.evtx file, confirming file truncation
