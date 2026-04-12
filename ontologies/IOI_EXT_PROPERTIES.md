# ioi-ext Properties Used

This document lists the custom `ioi-ext` properties introduced for the IoI
framework. These properties extend CASE/UCO where the required artifact fields
are not represented by existing core predicates. The extension is published
as a lightweight vocabulary in `ontologies/ioi-ext.ttl`.

Namespace: `https://ioi-framework.github.io/ns/ioi-ext/`

## MFT
- ioi-ext:entryNumber
- ioi-ext:sequenceNumber
- ioi-ext:parentEntryNumber
- ioi-ext:parentPath
- ioi-ext:created0x10
- ioi-ext:created0x30
- ioi-ext:lastModified0x10
- ioi-ext:lastModified0x30
- ioi-ext:lastRecordChange0x10
- ioi-ext:lastRecordChange0x30
- ioi-ext:lastAccess0x10
- ioi-ext:lastAccess0x30

## USN
- ioi-ext:updateReasons
- ioi-ext:updateTimestamp

## LNK
- ioi-ext:targetFilePath
- ioi-ext:targetCreatedTime
- ioi-ext:targetMftEntryNumber

## Event Log (EVTX)
- ioi-ext:channel

## Office XML
- ioi-ext:xmlCreatedTime

## Notes
- These properties are populated by the mapping scripts in `MAPPERS/`.
- They are referenced by the IoI rules in `RULES/` and appear in the JSON-LD
  templates under `TEMPLATES/`.
