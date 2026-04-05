# AF-011 Step-by-Step
LNK/MFT timestomping correlation (MFT + LNK).

> **Note:** Record the time taken at each step — Step 1 (Fill JSON-LD), Step 2 (Convert to N-Triples), Step 4 (Load graphs), and Step 5 (SPARQL run) — for evaluation purposes.

> Run all commands from inside the `AF-011/` folder:
> ```bash
> cd AF-011
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
- LNK CSV — exported from [LECmd](https://github.com/EricZimmerman/LECmd)

## 1) Fill JSON-LD
```bash
mkdir -p outputs
python3 baseline/mft_template_filler.py "<MFT_CSV>" outputs/mft_filled.jsonld
python3 lnk-shortcut/lnk_template_filler.py "<LNK_CSV>" outputs/lnk_filled.jsonld
```

## 2) Convert to N-Triples
```bash
python3 ../common/tools/convert_to_ntriples.py outputs/mft_filled.jsonld outputs/mft_case11.nt
python3 ../common/tools/convert_to_ntriples.py outputs/lnk_filled.jsonld outputs/lnk_case11.nt
```

## 3) Fresh Virtuoso
First run only: `docker pull openlink/virtuoso-opensource-7:latest`

```bash
docker rm -f vos 2>/dev/null || true
docker run --name vos -d -e DBA_PASSWORD=dba -p 8890:8890 -p 1111:1111 openlink/virtuoso-opensource-7:latest
```

## 4) Load graphs
```bash
docker cp outputs/mft_case11.nt vos:/database/mft_case11.nt
docker cp outputs/lnk_case11.nt vos:/database/lnk_case11.nt
docker exec vos isql 1111 dba dba "exec=DELETE FROM DB.DBA.load_list;"
docker exec vos isql 1111 dba dba "exec=ld_dir('.', 'mft_case11.nt', 'http://example.org/mft_case11');"
docker exec vos isql 1111 dba dba "exec=ld_dir('.', 'lnk_case11.nt', 'http://example.org/lnk_case11');"
docker exec vos isql 1111 dba dba "exec=rdf_loader_run();"
docker exec vos isql 1111 dba dba "exec=checkpoint;"
```

## 5) Run SPARQL
```bash
docker cp queries/virtuosorule1.rq vos:/database/AF011.rq
docker exec vos bash -lc "printf 'SPARQL\n'; cat /database/AF011.rq; printf '\n;'" | docker exec -i vos isql 1111 dba dba
```

**Interpreting results:** Rows returned indicate LNK file timestamps that contradict MFT records, suggesting timestomping. An empty result means no anomalies were detected.

---
> **Note:** Record the time taken at each step — Step 1 (Fill JSON-LD), Step 2 (Convert to N-Triples), Step 4 (Load graphs), and Step 5 (SPARQL run) — for evaluation purposes.
