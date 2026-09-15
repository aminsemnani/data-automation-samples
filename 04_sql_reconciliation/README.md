# SQL Invoice / Payment Reconciliation

A finance-operations example that reconciles invoice and payment exports using SQLite and produces a clear exception report.

## Business problem

Invoices and payments often come from different systems. Manual reconciliation becomes slow when payments are split, missing, overpaid, or reference unknown invoice numbers. A useful reconciliation process should identify clean matches and isolate exceptions for review.

## What it does

- loads invoice and payment CSV exports into SQLite
- enforces primary keys and non-negative monetary values
- aggregates split payments by invoice
- classifies invoices as `matched`, `partial`, `overpaid`, or `unpaid`
- detects payments that reference unknown invoices
- supports a configurable rounding tolerance
- writes a row-level reconciliation CSV and a JSON control summary
- can persist the SQLite audit database for inspection
- includes standalone SQL files so the database logic is visible rather than hidden inside Python

## Run the sample

```bash
python reconcile.py sample_data/invoices.csv sample_data/payments.csv --output output/reconciliation.csv --summary output/summary.json --database output/audit.sqlite
```

Runtime uses only the Python standard library and SQLite.

## Test

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The tests cover split payments, partial payment, overpayment, orphan payments, persisted audit databases, and configurable tolerance.

All sample data is synthetic.
