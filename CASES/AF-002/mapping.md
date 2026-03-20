# AF-002 Mapping Notes

## Purpose
Map MFT, Chrome History, and USN artifacts to CASE/UCO + dfc‑ext so the IoI signature can detect selective browser history deletion.

## 1) MFT → observable:File + dfc‑ext:MftFacet
**Source:** MFTECmd CSV

**Key fields used by the rule:**
- `dfc‑ext:parentPath` / `observable:filePath` (IndexedDB path)
- `dfc‑ext:entryNumber` (for record identity)

**Mapping target:**
- `observable:File`
- `dfc‑ext:MftFacet`

---

## 2) Chrome History → observable:URL + observable:URLFacet
**Source:** Chrome History SQLite export

**Key fields used by the rule:**
- `observable:fullValue` (URL string)

**Mapping target:**
- `observable:URL`
- `observable:URLFacet`

---

## 3) USN → observable:File + dfc‑ext:UsnFacet
**Source:** MFTECmd $J CSV

**Key fields used by the rule:**
- `observable:fileName` (History)
- `dfc‑ext:updateReasons` (DataOverwrite/DataTruncation/DataExtend)

**Mapping target:**
- `observable:File`
- `dfc‑ext:UsnFacet`

---

## Detection Logic (Summary)
1) Extract domains from IndexedDB paths in MFT.
2) Exclude domains that appear in Chrome History URLs.
3) Require USN evidence showing History file modification.

