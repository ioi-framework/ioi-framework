# Instantiators

Template Instantiators map artifact parser output (CSV/JSON) to CASE/UCO-compliant JSON-LD knowledge graphs.

## Usage

```bash
python3 mft_instantiator.py        <mft.csv>              <output.jsonld>
python3 usn_instantiator.py        <usn.csv>              <output.jsonld>
python3 evtx_instantiator.py       <evtx.csv>             <output.jsonld>
python3 lnk_instantiator.py        <lnk.csv>              <output.jsonld>
python3 history_instantiator.py    <history.json>         <output.jsonld>

# Office XML — two input modes:
python3 office_xml_instantiator.py <merged.json>          <output.jsonld>          # Autopsy path
python3 office_xml_instantiator.py <file.docx>            <output.jsonld>          # Manual path
python3 office_xml_instantiator.py <file.docx>            <output.jsonld> \
        --filepath "/original/path/on/image/file.docx"                             # Manual path with explicit filePath
```
