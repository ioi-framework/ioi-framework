# AF-002 Step-by-Step
Browser history tampering detection (MFT + History + USN).

> **Note:** Record the time taken at each step — Step 1 (Fill JSON-LD), Step 2 (Convert to N-Triples), Step 4 (Load graphs), and Step 5 (SPARQL run) — for evaluation purposes.

> Run all commands from inside the `AF-002/` folder:
> ```bash
> cd AF-002
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
- Browser history — either: * (Tested more with option B)
  - **Option A (Hindsight JSONL):** install and run Hindsight:
    ```bash
    pip install pyhindsight
    pip install git+https://github.com/cclgroupltd/ccl_chromium_reader.git
    python3 /usr/local/bin/hindsight.py -i "<path/to/Chrome/Default>" -o output -f jsonl
    ```
    Then use the resulting `output.jsonl` file.
  - **Option B (SQLite JSON dump):** a JSON file with `urls` and `visits` keys from Chrome's `History` SQLite DB.
    Chrome's `History` file is at:
    - Windows: `%LOCALAPPDATA%\Google\Chrome\User Data\Default\History`
    - macOS: `~/Library/Application Support/Google/Chrome/Default/History`
    - Linux: `~/.config/google-chrome/Default/History`

    Copy the `History` file somewhere (Chrome locks it while running), then export:
    ```bash
    python3 HISTORY_DB/export_chrome_history.py "<path/to/History>" history_export.json
    ```
- USN CSV/JSON — exported from [MFTECmd](https://github.com/EricZimmerman/MFTECmd)

## 1) Fill JSON-LD
```bash
mkdir -p outputs
python3 baseline/mft_template_filler.py "<MFT_CSV>" outputs/mft_filled.jsonld
python3 USN/usn_template_filler.py "<USN_INPUT>" outputs/usn_filled.jsonld
```

For history, pick one:
```bash
# Option A — Hindsight JSONL
python3 HISTORY_DB/history_template_filler_hindsight.py "<HINDSIGHT.jsonl>" outputs/history_filled.jsonld

# Option B — SQLite JSON dump
python3 HISTORY_DB/history_template_filler_sqlite.py "<HISTORY.json>" outputs/history_filled.jsonld
```

## 2) Convert to N-Triples
```bash
python3 ../common/tools/convert_to_ntriples.py outputs/mft_filled.jsonld outputs/mft_case2.nt
python3 ../common/tools/convert_to_ntriples.py outputs/history_filled.jsonld outputs/history_case2.nt
python3 ../common/tools/convert_to_ntriples.py outputs/usn_filled.jsonld outputs/usn_case2.nt
```

## 3) Fresh Virtuoso
First run only: `docker pull openlink/virtuoso-opensource-7:latest`

```bash
docker rm -f vos 2>/dev/null || true
docker run --name vos -d -e DBA_PASSWORD=dba -p 8890:8890 -p 1111:1111 openlink/virtuoso-opensource-7:latest
```

## 4) Load graphs
```bash
docker cp outputs/mft_case2.nt vos:/database/mft_case2.nt
docker cp outputs/history_case2.nt vos:/database/history_case2.nt
docker cp outputs/usn_case2.nt vos:/database/usn_case2.nt
docker exec vos isql 1111 dba dba "exec=DELETE FROM DB.DBA.load_list;"
docker exec vos isql 1111 dba dba "exec=ld_dir('.', 'mft_case2.nt', 'http://example.org/mft_case2');"
docker exec vos isql 1111 dba dba "exec=ld_dir('.', 'history_case2.nt', 'http://example.org/history_case2');"
docker exec vos isql 1111 dba dba "exec=ld_dir('.', 'usn_case2.nt', 'http://example.org/usn_case2');"
docker exec vos isql 1111 dba dba "exec=rdf_loader_run();"
docker exec vos isql 1111 dba dba "exec=checkpoint;"
```

## 5) Run SPARQL
```bash
docker cp queries/RULE_VIRTUOSO.rq vos:/database/AF002.rq
docker exec vos bash -lc "printf 'SPARQL\n'; cat /database/AF002.rq; printf '\n;'" | docker exec -i vos isql 1111 dba dba
```

**Interpreting results:** Rows returned indicate suspicious browser history entries where MFT/USN timestamps suggest tampering. An empty result means no anomalies were detected.

---
> **Note:** Record the time taken at each step — Step 1 (Fill JSON-LD), Step 2 (Convert to N-Triples), Step 4 (Load graphs), and Step 5 (SPARQL run) — for evaluation purposes.
