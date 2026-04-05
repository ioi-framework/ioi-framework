# AF-007 Step-by-Step
Security log clearing detection (Security EVTX + USN [+ optional System EVTX]).

> **Note:** Record the time taken at each step — Step 1 (Fill JSON-LD), Step 2 (Convert to N-Triples), Step 4 (Load graphs), and Step 5 (SPARQL run) — for evaluation purposes.

> Run all commands from inside the `AF-007/` folder:
> ```bash
> cd AF-007
> ```

## Requirements
- Docker installed and running
- Python 3.10+
- Python package:
```bash
pip install rdflib
```

## Inputs
- Security EVTX JSONL — exported from [EvtxECmd](https://github.com/EricZimmerman/evtx) or `evtx_dump`
- USN CSV/JSON — exported from [MFTECmd](https://github.com/EricZimmerman/MFTECmd)
- Optional: System EVTX JSONL — exported from the same tool as Security EVTX

## 1) Fill JSON-LD
```bash
mkdir -p outputs
python3 securityevtx/evtx_template_filler.py "<SECURITY_JSONL>" outputs/security_filled.jsonld
python3 USN/usn_template_filler.py "<USN_INPUT>" outputs/usn_filled.jsonld
```

If also using System EVTX (optional):
```bash
python3 Systemevtx/evtx_template_filler.py "<SYSTEM_JSONL>" outputs/system_filled.jsonld
```

## 2) Convert to N-Triples
```bash
python3 ../common/tools/convert_to_ntriples.py outputs/security_filled.jsonld outputs/security_case7.nt
python3 ../common/tools/convert_to_ntriples.py outputs/usn_filled.jsonld outputs/usn_case7.nt
```

If also using System EVTX (optional):
```bash
python3 ../common/tools/convert_to_ntriples.py outputs/system_filled.jsonld outputs/system_case7.nt
```

## 3) Fresh Virtuoso
First run only: `docker pull openlink/virtuoso-opensource-7:latest`

```bash
docker rm -f vos 2>/dev/null || true
docker run --name vos -d -e DBA_PASSWORD=dba -p 8890:8890 -p 1111:1111 openlink/virtuoso-opensource-7:latest
```

## 4) Load graphs
```bash
docker cp outputs/security_case7.nt vos:/database/security_case7.nt
docker cp outputs/usn_case7.nt vos:/database/usn_case7.nt
docker exec vos isql 1111 dba dba "exec=DELETE FROM DB.DBA.load_list;"
docker exec vos isql 1111 dba dba "exec=ld_dir('.', 'security_case7.nt', 'http://example.org/security_case7');"
docker exec vos isql 1111 dba dba "exec=ld_dir('.', 'usn_case7.nt', 'http://example.org/usn_case7');"
```

If also using System EVTX (optional):
```bash
docker cp outputs/system_case7.nt vos:/database/system_case7.nt
docker exec vos isql 1111 dba dba "exec=ld_dir('.', 'system_case7.nt', 'http://example.org/system_case7');"
```

```bash
docker exec vos isql 1111 dba dba "exec=rdf_loader_run();"
docker exec vos isql 1111 dba dba "exec=checkpoint;"
```

## 5) Run SPARQL
```bash
docker cp queries/RULEvirtuoso.rq vos:/database/AF007.rq
docker exec vos bash -lc "printf 'SPARQL\n'; cat /database/AF007.rq; printf '\n;'" | docker exec -i vos isql 1111 dba dba
```

**Interpreting results:** Rows returned indicate evidence of security log clearing correlated with USN journal anomalies. An empty result means no anomalies were detected.

---
> **Note:** Record the time taken at each step — Step 1 (Fill JSON-LD), Step 2 (Convert to N-Triples), Step 4 (Load graphs), and Step 5 (SPARQL run) — for evaluation purposes.
