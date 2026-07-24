# N01661670_HiveHBaseAssignment

Hive-HBase Assignment for Big Data Course

# Loblaw Retail Operations and Customer Shopping Analytics Platform

An integrated big-data analytics solution simulating retail transaction and product-sales
event processing for Real Canadian Superstore locations, using Apache HBase, Apache Hive,
Python, and Apache Zeppelin on a Hortonworks Data Platform (HDP) sandbox.

**All data is synthetic and generated for educational purposes only.** No actual Loblaw
operational data, proprietary information, or personally identifiable customer information
is used.

---

## 1. Architecture

```
Synthetic Retail CSV Data
        |
        v
Python (Data Validation & Ingestion)
        |
        v
HBase (Operational Data Store)
        |
        v  (HBase-Hive Integration)
Hive (SQL Analytical Layer)
        |
   +----+----+
   v         v
HiveQL    Python (Statistical Analysis)
   |         |
   +----+----+
        v
Zeppelin (Interactive Analytics)
        |
   +----+----+----+
   v    v    v
Charts Histograms Analysis
        |
        v
Business Findings -> Business Recommendations
```

A full-resolution diagram is in `docs/architecture.png`.

**Component roles:**
- **HBase** — operational data store; holds one row per product-sale event
- **Hive** — SQL analytical layer, reading directly from HBase via an external
  `HBaseStorageHandler` table (no separate copy of the data)
- **Python** — CSV ingestion/validation, transaction-level aggregation, statistical
  analysis, and outlier detection
- **Zeppelin** — the integrated notebook environment tying HiveQL, Python, and
  visualizations together into one workspace

---

## 2. Repository Structure

```
loblaw-hbase-hive-analytics/
├── README.md
├── data/                       # provided CSVs
├── hbase/
│   ├── create_table.txt
│   └── validation_commands.txt
├── hive/
│   ├── create_external_table.hql
│   └── analytics.hql
├── python/
│   ├── load_hbase.py
│   └── analytics.py
├── zeppelin/
│   └── loblaw_retail_analytics.json
├── screenshots/
│   ├── hbase/
│   ├── hive/
│   ├── python/
│   └── zeppelin/
└── docs/
    ├── architecture.png
    └── EVIDENCE_AND_FINDINGS.md
```

---

## 3. Environment

This project was built and executed on:

- **Infrastructure:** VMware Cloud Director, two VMs — a Windows VM (development) and an
  HDP Sandbox VM (Hadoop/HBase/Hive/Zeppelin server)
- **HDP Sandbox:** HBase 1.1.2 (HDP 2.6.5), Python 2.7.5 (server-side, used by Zeppelin's
  PySpark interpreter)
- **Windows VM:** VSCode, GitHub Desktop, Python 3.11 (client-side ingestion script)
- **Admin/monitoring:** Ambari (port 8080)
- **HBase access:** HBase REST API (Stargate) on port 60080 — used instead of Thrift, since
  Thrift was not available/configured in this sandbox
- **Terminal access to the HDP VM:** web terminal on port 4200

> **Note on architecture choice:** the Python ingestion script (`load_hbase.py`) runs on the
> Windows VM and connects to HBase over the network via its REST API, rather than running
> directly on the HDP VM. This was a deliberate choice based on available connectivity
> (Thrift was unavailable) and works because both VMs sit on the same internal vApp network
> in VMware Cloud Director.

---

## 4. Reproduction Instructions

### 4.1 Prerequisites
1. HDP Sandbox VM running, with HDFS, HBase, Hive, and Zeppelin services started (verify
   in Ambari — all should show green "Started").
2. HBase REST server running on the HDP VM:
   ```
   sudo /usr/hdp/current/hbase-master/bin/hbase-daemon.sh start rest -p 60080
   ```
3. Python 3.11 installed on the Windows VM (or wherever `load_hbase.py` will run), with:
   ```
   pip install requests pandas matplotlib numpy scipy
   ```
4. Python 2.7 on the HDP VM (pre-installed) with pandas/numpy/matplotlib available to the
   Zeppelin PySpark interpreter:
   ```
   sudo curl https://bootstrap.pypa.io/pip/2.7/get-pip.py -o get-pip.py
   sudo python get-pip.py
   sudo pip install --ignore-installed "numpy==1.16.6" "pandas==0.24.2" "matplotlib==2.2.5"
   ```
   Restart the `spark2` interpreter in Zeppelin after installing.

### 4.2 Load the CSVs
Upload the six CSVs to HDFS via Ambari's Files View (e.g. to
`/user/maria_dev/retail_data/`), and copy them to local disk on the HDP VM for use in
Zeppelin paragraphs:
```
hdfs dfs -copyToLocal /user/maria_dev/retail_data/retail_events.csv /tmp/retail_events.csv
```
Also keep a copy of the CSVs in this repo's `data/` folder, since `load_hbase.py` reads
from local disk on whichever machine runs it.

### 4.3 Create the HBase table
In HBase shell (`hbase shell` from the HDP VM terminal):
```
create 'retail_events', 'transaction', 'product', 'store', 'sales'
```
Full commands in `hbase/create_table.txt`.

### 4.4 Run the ingestion script
From the Windows VM (or wherever Python 3 + `requests` is available):
```
cd python
python load_hbase.py ../data/retail_events.csv
```
Edit the `HDP_IP` constant at the top of `load_hbase.py` first to match your HDP VM's IP.

Test error handling against the malformed dataset:
```
python load_hbase.py ../data/malformed_retail_events.csv
```

### 4.5 Create the Hive external table
Run `hive/create_external_table.hql` via Hive View (Ambari) or Beeline. This creates
`retail_events_hive`, mapped directly onto the `retail_events` HBase table — no data is
copied.

### 4.6 Run analytics
HiveQL analytical queries are in `hive/analytics.hql`. Python statistical analysis is in
`python/analytics.py` (mirrors the logic used in the Zeppelin notebook's `%pyspark`
paragraphs).

### 4.7 Import the Zeppelin notebook
In Zeppelin: **Import Note** → select `zeppelin/loblaw_retail_analytics.json`. This contains
the full documented analysis (Sections 01–25). Re-run paragraphs top to bottom to regenerate
live charts, since query results are not persisted in the JSON export.

---

## 5. Known Environment Gotchas

These issues came up during development on this specific VMware/vCD + HDP sandbox setup —
documented here in case of a rebuild:

- **VSCode integrated terminal fails with "Cannot launch conpty"** — common on this VM
  image. Fix: add `"terminal.integrated.windowsUseConptyDll": true` to VSCode's
  `settings.json`, or just use an external Command Prompt/PowerShell window instead — the
  integrated terminal is not required to run any part of this project.
- **`pip` not found even though `python` works** — use `python -m pip ...` instead, or
  `python -m ensurepip --upgrade` if pip is missing entirely.
- **HDP VM's Python 2.7 has no `pip`** — bootstrap it with the Python-2.7-specific
  `get-pip.py` (see section 4.1); modern `pip`/PyPI no longer support Python 2 by default.
- **`sudo pip install matplotlib` fails with "Cannot uninstall 'pyparsing'"** — a system
  RPM-installed package conflicts with pip. Fix: `sudo pip install --ignore-installed ...`
- **Hive queries using window functions (`OVER()`) against the HBase-backed external table
  run extremely slowly or hang** — the HBase storage handler doesn't push filters down
  efficiently under window functions. Avoid `OVER()` on this table; do percentage/ratio
  calculations in Python instead after a plain `GROUP BY`.
- **Zeppelin shows "Interpreter python not found"** — this sandbox's Zeppelin only has
  `%pyspark` (Python via the `spark2` interpreter group) rather than a standalone `%python`
  interpreter. Use `%pyspark` throughout.
- **Installed Python packages don't appear after `pip install`** — the interpreter process
  must be restarted (Zeppelin → Interpreter page → restart icon on `spark2`) before newly
  installed packages become visible; restarting also clears all in-memory notebook
  variables, so upstream paragraphs need to be re-run in order.

---

## 6. Evidence and Findings

See `docs/EVIDENCE_AND_FINDINGS.md` for the full write-up of business findings and
recommendations, cross-referenced to supporting queries and screenshots.
