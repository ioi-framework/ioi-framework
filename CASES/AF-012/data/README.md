# AF-012 Step-by-Step
Office XML metadata mismatch detection using separate Office XML and MFT graphs.

> **Note:** Record the time taken at each step — Step 1 (Fill JSON-LD), Step 2 (Convert to N-Triples), Step 4 (Load graphs), and Step 5 (SPARQL run) — for evaluation purposes.

> Run all commands from inside the `AF-012/` folder:
> ```bash
> cd AF-012
> ```

## Requirements
- Docker installed and running
- Python 3.10+
- Python package:
```bash
pip install rdflib
```

## Inputs
- MFT CSV — exported from [MFTECmd](https://github.com/EricZimmerman/MFTECmd)
- XML metadata folder — directory containing extracted `core.xml` / `app.xml` files from Office documents (e.g. unzipped `.docx`/`.xlsx`)

## 1) Fill JSON-LD
Generate an Office-only graph:
```bash
mkdir -p outputs
python3 office-xml-metadata/office_xml_only_filler.py "<XML_FOLDER>" outputs/office_xml_only.jsonld
```

Generate a separate MFT graph:
```bash
python3 ../AF-011/baseline/mft_template_filler.py "<MFT_CSV>" outputs/mft_case12.jsonld
```

## 2) Convert to N-Triples
```bash
python3 ../common/tools/convert_to_ntriples.py outputs/office_xml_only.jsonld outputs/office_case12.nt
python3 ../common/tools/convert_to_ntriples.py outputs/mft_case12.jsonld outputs/mft_case12.nt
```

## 3) Fresh Virtuoso
First run only: `docker pull openlink/virtuoso-opensource-7:latest`

```bash
docker rm -f vos 2>/dev/null || true
docker run --name vos -d -e DBA_PASSWORD=dba -p 8890:8890 -p 1111:1111 openlink/virtuoso-opensource-7:latest
```

## 4) Load graphs
```bash
docker cp outputs/office_case12.nt vos:/database/office_case12.nt
docker cp outputs/mft_case12.nt vos:/database/mft_case12.nt
docker exec vos isql 1111 dba dba "exec=DELETE FROM DB.DBA.load_list;"
docker exec vos isql 1111 dba dba "exec=ld_dir('.', 'office_case12.nt', 'http://example.org/office_case12');"
docker exec vos isql 1111 dba dba "exec=ld_dir('.', 'mft_case12.nt', 'http://example.org/mft_case12');"
docker exec vos isql 1111 dba dba "exec=rdf_loader_run();"
docker exec vos isql 1111 dba dba "exec=checkpoint;"
```

## 5) Run SPARQL
```bash
docker cp queries/rule_virtuoso.rq vos:/database/AF012.rq
docker exec vos bash -lc "printf 'SPARQL\n'; cat /database/AF012.rq; printf '\n;'" | docker exec -i vos isql 1111 dba dba
```

**Interpreting results:** Rows returned indicate Office documents where internal XML metadata timestamps contradict separately loaded MFT timestamps, suggesting metadata manipulation. An empty result means no anomalies were detected.

---
> **Note:** Record the time taken at each step — Step 1 (Fill JSON-LD), Step 2 (Convert to N-Triples), Step 4 (Load graphs), and Step 5 (SPARQL run) — for evaluation purposes.
