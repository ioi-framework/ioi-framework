# Instantiators

Template Instantiators map artifact parser output (CSV/JSON) to CASE/UCO-compliant JSON-LD knowledge graphs.

## Usage

```bash
python mft_to_case.py --input <mft.csv> --output <mft_case.jsonld>
python usn_to_case.py --input <usn.csv> --output <usn_case.jsonld>
python evtx_to_case.py --input <evtx.csv> --output <evtx_case.jsonld>
python lnk_to_case.py --input <lnk.csv> --output <lnk_case.jsonld>
python history_to_case.py --input <history.json> --output <history_case.jsonld>
python office_xml_to_case.py --input <office.json> --output <office_case.jsonld>
```

Templates are in `templates/` organized by artifact type.
