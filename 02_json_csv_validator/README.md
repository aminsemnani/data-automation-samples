# JSON / CSV Validation & Transformation Pipeline

A small ETL-style utility for turning nested JSON or JSONL records into a clean tabular dataset while preserving rejected records and validation evidence.

## Business problem

Operational data often arrives from APIs or exported systems in nested JSON. Before it can be imported into Excel, a database, or a reporting tool, it needs to be normalized and checked. Silently dropping bad rows is risky, so this sample separates valid records from rejected records and produces an audit report.

## What it does

- reads JSON arrays or JSONL files
- maps nested source fields into a canonical flat schema
- normalizes text, e-mail, currency and country values
- validates required fields, dates, e-mail format and non-negative monetary values
- rejects duplicate order IDs
- writes accepted records to CSV
- preserves rejected source records together with explicit validation errors
- writes a machine-readable JSON quality report
- supports a configurable field map instead of hard-coding one source layout

## Run the sample

```bash
python pipeline.py sample_data/orders.json \
  --field-map sample_data/field_map.json \
  --valid output/valid_orders.csv \
  --rejected output/rejected_orders.json \
  --report output/validation_report.json
```

No runtime third-party dependency is required.

## Test

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The tests cover normalization, validation, duplicate detection, and creation of all audit outputs.

## Why this is useful

This pattern is suitable for client imports, API extracts, CRM/ERP staging files, order feeds, and any workflow where malformed records must be visible rather than quietly ignored.

All sample data is synthetic.
