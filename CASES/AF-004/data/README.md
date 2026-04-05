# AF-004 Step-by-Step
VSS purge detection (MFT + USN).

> **Note:** Record the time taken at each step — Step 1 (Fill JSON-LD), Step 2 (Convert to N-Triples), Step 4 (Load graphs), and Step 5 (SPARQL run) — for evaluation purposes.

> Run all commands from inside the `AF-004/` folder:
> ```bash
> cd AF-004
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
- USN CSV/JSON — exported from [MFTECmd](https://github.com/EricZimmerman/MFTECmd)

## 1) Fill JSON-LD
```bash
mkdir -p outputs
python3 baseline/mft_template_filler.py "<MFT_CSV>" outputs/mft_filled.jsonld
python3 USN/usn_template_filler.py "<USN_INPUT>" outputs/usn_filled.jsonld
```

## 2) Convert to N-Triples
```bash
python3 ../common/tools/convert_to_ntriples.py outputs/mft_filled.jsonld outputs/mft_case4.nt
python3 ../common/tools/convert_to_ntriples.py outputs/usn_filled.jsonld outputs/usn_case4.nt
```

## 3) Fresh Virtuoso
First run only: `docker pull openlink/virtuoso-opensource-7:latest`

```bash
docker rm -f vos 2>/dev/null || true
docker run --name vos -d -e DBA_PASSWORD=dba -p 8890:8890 -p 1111:1111 openlink/virtuoso-opensource-7:latest
```

## 4) Load graphs
```bash
docker cp outputs/mft_case4.nt vos:/database/mft_case4.nt
docker cp outputs/usn_case4.nt vos:/database/usn_case4.nt
docker exec vos isql 1111 dba dba "exec=DELETE FROM DB.DBA.load_list;"
docker exec vos isql 1111 dba dba "exec=ld_dir('.', 'mft_case4.nt', 'http://example.org/mft_case4');"
docker exec vos isql 1111 dba dba "exec=ld_dir('.', 'usn_case4.nt', 'http://example.org/usn_case4');"
docker exec vos isql 1111 dba dba "exec=rdf_loader_run();"
docker exec vos isql 1111 dba dba "exec=checkpoint;"
```

## 5) Run SPARQL
```bash
docker cp queries/RULE_SIMPLE_VIRTUOSO.rq vos:/database/AF004.rq
docker exec vos bash -lc "printf 'SPARQL\n'; cat /database/AF004.rq; printf '\n;'" | docker exec -i vos isql 1111 dba dba
```

**Interpreting results:** Rows returned indicate evidence of VSS purge activity correlated with MFT/USN anomalies. An empty result means no anomalies were detected.

---
> **Note:** Record the time taken at each step — Step 1 (Fill JSON-LD), Step 2 (Convert to N-Triples), Step 4 (Load graphs), and Step 5 (SPARQL run) — for evaluation purposes.
