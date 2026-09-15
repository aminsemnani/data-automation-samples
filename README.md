# Data Automation Samples

Practical, testable examples of data and office-automation work built around common business problems: messy files, unreliable imports, recurring Excel reports, reconciliation, and API synchronization.

This repository is intentionally small in scope and explicit in behavior. The goal is to show maintainable workflows that can be understood, tested, and adapted to real client processes rather than one-off demo scripts.

## Portfolio samples

| # | Sample | Typical use case | Main tools |
|---|---|---|---|
| 01 | [CSV / Excel Data Cleaner & Merger](./01_csv_excel_cleaner/) | Consolidating inconsistent spreadsheets and exports | Python, pandas, openpyxl |
| 02 | [JSON / CSV Validation & Transformation](./02_json_csv_validator/) | API/ERP/CRM import staging with accepted and rejected records | Python, JSON, CSV |
| 03 | [Excel Management Report Builder](./03_excel_management_report/) | Repeatable management reporting from transactional exports | Python, pandas, openpyxl |
| 04 | [SQL Invoice / Payment Reconciliation](./04_sql_reconciliation/) | Finance/operations reconciliation and exception handling | Python, SQLite, SQL |
| 05 | [REST API to SQLite Sync Pipeline](./05_rest_api_sync/) | Paginated API ingestion with retries, upserts, and audit history | Python, requests, SQLite |

## What these samples demonstrate

- clear input/output contracts
- validation before processing
- explicit exception and rejected-record handling
- repeatable command-line workflows
- audit/control reports where the task needs them
- deterministic synthetic sample data
- automated tests around business rules, not only happy paths
- limited dependencies and straightforward project structure
- no credentials, client data, or hidden external services required for tests

See [QUALITY.md](./QUALITY.md) for the standards used across the repository and [VALIDATION.md](./VALIDATION.md) for the local test snapshot.

## Scope

These are portfolio-sized examples, not claims that every client problem fits a generic script. In real work, field mappings, business rules, error policies, database schemas, reporting formats, and deployment details should be defined from the actual process and data.

## Typical work represented here

- Excel / CSV cleanup, merge, transformation, and validation
- JSON and API data preparation
- scheduled or repeatable reporting
- SQL import and reconciliation workflows
- lightweight internal data tools
- REST API integration and synchronization

> All example data in this repository is synthetic. No client or confidential data is included.
