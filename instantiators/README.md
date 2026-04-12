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

## office_xml_instantiator — Manual vs Autopsy mode

| Mode | Input | filePath in output |
|------|-------|--------------------|
| Autopsy | `merged.json` produced by ArtifactExporter | taken from merged JSON (matches MFT) |
| Manual | `.docx` / `.xlsx` / `.pptx` directly | prompted interactively, or pass `--filepath` |

**Important for manual use:** The `filePath` in the office graph must match the `filePath` in the MFT graph for the IOI-012 SPARQL join to work. Always supply `--filepath` with the original path as it appears in your MFT CSV (e.g. `/Users/ktams/Desktop/Confidential/password.docx`). If omitted, the script will prompt you.

## mft_instantiator — filePath normalisation

Both `ParentPath` and `FileName` from the MFT CSV are normalised to a forward-slash absolute path:

```
/Users/ktams/Desktop/Confidential/password.docx
```

Backslashes are converted, leading `./` is stripped, and a leading `/` is added if missing. This ensures the join key matches the office graph.

## Converting JSON-LD output to N-Triples

Use the provided script (Node.js `jsonld` package preferred, `rdflib` fallback):

```bash
python3 ../SCRIPTS/convert_to_ntriples.py output.jsonld output.nt
```

Do **not** use a custom NT serialiser — nested JSON-LD facet nodes will be silently dropped.
