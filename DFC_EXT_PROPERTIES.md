# dfc-ext Properties Used

This document lists the custom `dfc-ext` properties introduced for the IoI
framework. These properties extend CASE/UCO where the required artifact fields
are not represented by existing core predicates. The extension is published
as a lightweight vocabulary in `VOCAB/dfc-ext.ttl`.

Namespace: `https://www.w3.org/dfc-ext/` #need to make it

## MFT
- dfc-ext:entryNumber
- dfc-ext:sequenceNumber
- dfc-ext:parentEntryNumber
- dfc-ext:parentPath
- dfc-ext:created0x10
- dfc-ext:created0x30
- dfc-ext:lastModified0x10
- dfc-ext:lastModified0x30
- dfc-ext:lastRecordChange0x10
- dfc-ext:lastRecordChange0x30
- dfc-ext:lastAccess0x10
- dfc-ext:lastAccess0x30

## USN
- dfc-ext:updateReasons
- dfc-ext:updateTimestamp

## LNK
- dfc-ext:targetFilePath
- dfc-ext:targetCreatedTime
- dfc-ext:targetMftEntryNumber

## Event Log (EVTX)
- dfc-ext:channel

## Office XML
- dfc-ext:xmlCreatedTime

## Notes
- These properties are populated by the mapping scripts in `MAPPERS/`.
- They are referenced by the IoI rules in `RULES/` and appear in the JSON-LD
  templates under `TEMPLATES/`.
